# Troubleshooting

## Chat doesn't work locally: checklist
The chat needs three things. In `npm run dev`, the chat panel tells you which one is missing.

| # | Check | Fix |
|---|---|---|
| 1 | Supabase has the schema | Create a project, then run `supabase/migrations/0001_init.sql` in **SQL Editor** ([deployment.md](deployment.md)) |
| 2 | `.env` has the keys | `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `IP_HASH_SALT` (copy from `.env.example`) |
| 3 | The content is indexed | `.venv/bin/python backend/scripts/ingest.py` (then check the `documents` table has rows) |

Then run **`npm run dev:all`** (not just `npm run dev`; that starts only the website, not the Python API) and open http://localhost:3000/api/py/health. Every `configured` value except `resend` should be `true`.

## Build fails: `Invalid content in content/…`
The message names the file and field, e.g. `projects/plantatio.mdx: timeline: Invalid input`. Fix that field. See the field table in [content-guide.md](content-guide.md#project-frontmatter). Common causes: a missing required field, a `status`/`category` outside the allowed list, `slug` not matching the file name, or an `accent` that isn't a `#RRGGBB` hex colour.

## Build fails in an MDX file
Usually an unescaped `{` or `<` in prose, or a component prop missing its braces (`steps=["a"]` must be `steps={["a"]}`). The error shows the line number.

## The chat says "The assistant isn't configured yet."
`GEMINI_API_KEY`, `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` is missing. Check `/api/py/health`. Locally, make sure `.env` is in the repo root and restart `npm run dev:api`. On Vercel, add the variables and **redeploy** (env changes only apply to new deployments).

## The chat says "The AI model is very busy right now" or answers slowly
Google returned `503 high demand` (or timeouts) for every model in the chain. Check the API logs for `gemini_fallback` lines to see which models failed. Put models that work right now first. To test one:
```bash
.venv/bin/python -c "import sys; sys.path.insert(0,'backend/src'); from llm.gemini import get_gemini; print(get_gemini().generate('Reply ok', model='gemini-3.5-flash'))"
```
Then set `GEMINI_CHAT_MODEL` / `GEMINI_CHAT_FALLBACK_MODELS` in `.env` (and in Vercel). A `404` means the model id no longer exists on your key.

## The chat answers "I don't have that…" to everything
The index is empty or stale. Run `.venv/bin/python backend/scripts/ingest.py` and check Supabase → `documents` has rows. If it does, `RAG_MIN_SIMILARITY` may be too strict: try `0.4`. Also check that `EMBED_DIM` matches the `vector(768)` column (see [database.md](database.md)).

## Answers cite the wrong thing or miss obvious facts
Make the source clearer: put the fact in a project MDX or `knowledge/*.md` with an explicit heading, push, and let ingest run. Then add a golden question for it ([testing.md](testing.md)).

## `429 Too Many Requests`
The per-visitor limit was hit (default 20 questions / 10 min, 3 contact messages / hour). Change `RATE_LIMIT_*` env vars if needed. For local testing you can clear the `rate_limits` table.

## API returns 404 on Vercel
1. Confirm the deployment has a function for `api/index.py` (Vercel → Deployment → **Functions** tab).
2. Confirm the production rewrite in `next.config.ts` (`/api/py/:path*` → `/api/index`).
3. Check `vercel.json` → `functions["api/index.py"].includeFiles` covers `backend/src/**`. Without it the import of `agent.main` fails (`ModuleNotFoundError` in the function logs).
4. As an alternative, change the rewrite destination to `/api` and redeploy.

## `ModuleNotFoundError` in the function logs
A dependency is missing from the root `requirements.txt` (the file Vercel installs). Add it there **and** to `backend/pyproject.toml`.

## Streaming arrives all at once
Some proxies buffer SSE. The API sends `Cache-Control: no-transform` and `X-Accel-Buffering: no`. If you self-host behind nginx, also set `proxy_buffering off;` for `/api/py/`.

## Contact form works but no email arrives
Check the function logs for `contact_email_failed`. With `onboarding@resend.dev` as the sender, Resend only delivers to your own Resend account email until you verify a domain. The message is still saved in `contact_messages`.

## Local dev: `next dev` can't reach the API
Run `npm run dev:all` (or `npm run dev:api` in a second terminal). The proxy targets `127.0.0.1:8000`.
