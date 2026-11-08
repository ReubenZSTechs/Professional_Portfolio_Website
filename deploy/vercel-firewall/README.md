# Vercel Firewall rules

Custom Vercel Firewall (WAF) rules for the portfolio, kept as code. Apply them
**once, after the first Vercel deploy** (the project has to exist first).

| File | Purpose |
| --- | --- |
| `rules.json` | The rules, in priority order, in the JSON shape `vercel firewall rules add --data` accepts. |
| `apply.sh` | Adds every rule that is missing, then publishes. Safe to re-run. |

## What each rule stops

Rules are evaluated top to bottom. The first two matter most, so they come first.

1. **Rate limit chat API.** `POST /api/py/chat` allows 30 requests per 60 s per
   client IP (fixed window). After that, requests are denied until the window
   resets. Every chat message costs an LLM call, so this caps what one abusive
   client or script can spend. A real visitor stays far below 30 messages a minute.
2. **Rate limit contact API.** `POST /api/py/contact` allows 5 requests per
   600 s per IP, then denies. This stops contact-form spam and inbox flooding.
3. **Block scanner paths.** Denies `/.env*`, `/.git*`, `/wp-*`, any path ending
   in `.php`, `/admin*` and `/phpmyadmin*`. Bots probe these paths for leaked
   secrets and WordPress or PHP holes. None of them exist on this Next.js site,
   so blocking them at the edge costs nothing and keeps the logs clean.
   Note that `/admin` is a prefix match. If you ever add an `/admin` page, edit
   this rule first.
4. **Block unexpected API methods.** Denies any method other than GET, HEAD,
   POST and OPTIONS on `/api/*`. The API only serves `GET /api/py/health` and
   `POST` for chat and contact. OPTIONS stays open so CORS preflight keeps working.

Both rate limits count per IP, so many visitors behind one NAT (an office or a
university) share a bucket. If real users start getting denied, raise `limit`.
These edge limits stop abusive traffic before it reaches the function, so it
is never billed. Keep any app-level limits in the backend as a second layer.

## Running it

Prerequisites: the `vercel` CLI (`npm i -g vercel`, then `vercel login`) and
`jq` (`brew install jq`).

```bash
vercel link --scope reubenzstechs
```

```bash
deploy/vercel-firewall/apply.sh --dry-run
```

```bash
deploy/vercel-firewall/apply.sh
```

The script works from any directory. It checks that the CLI is installed and
the repo is linked (`.vercel/project.json`), then:

1. prints the current rules (`vercel firewall rules list`, which includes drafts);
2. runs `vercel firewall rules add --data '<rule>' --yes` for each rule in
   `rules.json`, **skipping any rule whose `name` already exists**;
3. shows the staged changes (`vercel firewall diff`);
4. publishes with `vercel firewall publish --confirm-name <projectName>`. The
   project name comes from `.vercel/project.json`, or from `--project NAME`
   or `VERCEL_PROJECT_NAME`. Without one, publish asks you to type it.

`--dry-run` only prints the `vercel` commands. It runs none of them, does not
need the CLI or a link, and does not fetch the current rules, so every rule is
listed as "Add".

New rules are added at the end of the list. If the project already has other
custom rules, check the order afterwards with `vercel firewall rules list` and
fix it with `vercel firewall rules move "<name>" --position N --yes`.

## Changing or removing a rule

Firewall edits are staged as drafts and do nothing until you publish them.

```bash
vercel firewall rules inspect "Rate limit chat API"
```

```bash
vercel firewall rules update "Rate limit chat API" --rate-limit-requests 60 --yes
```

```bash
vercel firewall rules disable "Block scanner paths" --yes
```

```bash
vercel firewall rules remove "Block scanner paths" --yes
```

```bash
vercel firewall diff
```

```bash
vercel firewall publish --confirm-name <project-name>
```

To replace a rule completely, edit it in `rules.json`, remove the live rule
(`rules remove`), and re-run `apply.sh`, which adds it back from the file.
You can also run `vercel firewall rules update "<name>" --data '<json>' --yes`.
Keep `rules.json` in sync with whatever is live, so the file stays the source of truth.

## Plan limits

The number of custom rules and the rate-limiting features (window lengths,
keys other than IP, the token-bucket algorithm) depend on the Vercel plan. On
a plan with fewer rule slots, or where rate limiting is limited, apply the
rules in file order and stop where the plan stops. The two rate limits
protect cost and the inbox, so they matter most. The scanner and method rules
are nice to have. If `rules add` fails with a plan or limit error, `apply.sh`
stops there (it runs with `set -e`). Nothing is published until you publish
yourself, so you can publish the rules that were added.

## Emergency: Attack Challenge Mode

During an active attack (a sudden traffic flood, the chat API being hammered
from many IPs), turn on Attack Mode. It challenges all browser traffic at the
edge, while known good bots get through. It takes effect at once, with no
publish step.

```bash
vercel firewall attack-mode enable --duration 1h --yes
```

```bash
vercel firewall attack-mode disable --yes
```

`--duration` takes `1h` (the default), `6h` or `24h`. Attack Mode also
challenges the site's own `fetch()` calls to `/api/py/*`, so **the chat widget
and contact form stop working while it is on**. Use it to survive an attack,
then turn it off.

## Keep bot "challenge" actions off `/api/*`

A challenge is an interstitial page that runs JavaScript in the browser and
then sets a cookie. A page navigation can pass one, but a `fetch()` call
cannot. The chat widget's request to `/api/py/chat` (a streamed SSE response)
and the contact form's POST would get the challenge page back instead of JSON
or an event stream, and fail.

So:

- Use **deny** (or the rate-limit actions above) on `/api/*`, never
  **challenge**. None of the rules here challenge.
- If you set a managed bot rule (Bot Protection or AI Bots, see
  `vercel firewall bot-management`) to challenge, the API gets challenged too.
  The simplest safe setting is to keep Bot Protection on **log**
  (`vercel firewall rules update bot-protection --action log --yes`). A custom
  **bypass** rule for `/api/py/` can exempt the API, but a bypass also lets
  requests skip other protections. Check the current docs for what it skips,
  and make sure the rate limits above still apply. Test the chat widget in a
  real browser after any bot-rule change.

Reference: <https://vercel.com/docs/cli/firewall>
