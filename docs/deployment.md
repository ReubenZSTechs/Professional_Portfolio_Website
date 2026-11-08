# Deployment

Production runs on four services, all on free tiers:

| Service | Does what |
|---|---|
| **Vercel** | Hosts the Next.js site and the Python API (`api/index.py`) |
| **Supabase** | Postgres + pgvector: chatbot index, contact inbox, rate limits |
| **Google Gemini** | Chat answers and embeddings |
| **Resend** | Emails you each contact-form message |

This is a first-time checklist. It starts from where the repo is now: one "Initial commit" on `main`, all recent work uncommitted, nothing deployed. Do the steps in order and tick each box. Every step ends with a **Check** that tells you it worked.

Keep a scratch note open (a password manager entry is best) to paste keys into as you go. You will need them twice: once in `.env`, once in Vercel.

---

## 0. Pre-flight: test, commit, push

- [ ] **Put your CV in place.** The **Download CV** button links to `/cv.pdf` (set in `content/site.yaml`), so the file must exist at `public/cv.pdf`.
  ```bash
  ls -l public/cv.pdf
  ```
- [ ] **Run the frontend checks** (typecheck, lint, production build):
  ```bash
  npm run check
  ```
  **Check:** it ends with the Next.js route table and no `Error` lines.
- [ ] **Run the backend checks:**
  ```bash
  .venv/bin/ruff check backend api
  cd backend && ../.venv/bin/python -m pytest -q && cd ..
  ```
  **Check:** ruff prints `All checks passed!` and pytest ends with `passed` and no `failed`.
  No `.venv` yet? See [local-development.md](local-development.md).
- [ ] **Stage everything:**
  ```bash
  git add -A
  git status
  ```
- [ ] **Make sure no secrets are staged.** `.env` is git-ignored (see `.gitignore`), but look anyway:
  ```bash
  git ls-files | grep -E '(^|/)\.env'
  ```
  **Check:** the only line printed is `.env.example`. Also scan the `git status` list for anything that looks private (for example `.claude/settings.local.json`). Unstage it with `git restore --staged <path>` and add it to `.gitignore`.
  The many `deleted:` lines under `frontend/` and elsewhere are expected: they are the old placeholder files.
- [ ] **Commit and push:**
  ```bash
  git commit -m "Build portfolio site, chatbot API and deployment config"
  git push origin main
  ```
  **Check:** open <https://github.com/ReubenZSTechs/Professional_Portfolio_Website>. Your commit is at the top. Click the **Actions** tab: the **CI** workflow runs for that push and should finish with a green tick (both the *Frontend* and *Backend* jobs).

---

## 1. Supabase (database)

Free plan allows **2 active projects**. Your only other project, A.T.H.E.N.A, is paused, so you have room.

- [ ] Go to <https://supabase.com/dashboard> → **New project**.
- [ ] Fill in:
  - **Organization:** your personal org.
  - **Project name:** `portfolio`.
  - **Database password:** click **Generate a password**, then save it in your password manager. The app doesn't use it, but you'll need it for direct database access later.
  - **Region:** **Southeast Asia (Singapore)** (`ap-southeast-1`, closest to Jakarta).
  - Click **Create new project** and wait for it to finish provisioning (1–2 minutes).
- [ ] **Apply the schema.** Left sidebar → **SQL Editor** → **New query**. Open `supabase/migrations/0001_init.sql` in your editor, copy all of it, paste it into the query box, click **Run**.
  **Check:** the result panel says `Success. No rows returned`.
- [ ] **Verify the tables.** In a new SQL Editor query, run:
  ```sql
  select table_name from information_schema.tables
  where table_schema = 'public' order by table_name;
  ```
  **Check:** you see exactly `contact_messages`, `documents`, `rate_limits`. (They also appear under **Table Editor** in the sidebar.)
- [ ] **Copy the Project URL.** **Project Settings** (gear icon) → **Data API** (older dashboards: **API**) → **Project URL**, e.g. `https://abcdefghijkl.supabase.co`. This is `SUPABASE_URL`.
- [ ] **Copy the secret key.** **Project Settings** → **API Keys** → tab **Publishable and secret API keys** → under **Secret keys**, click **Reveal** (or **Create new secret key** if none exists) and copy the value starting with `sb_secret_`. This is `SUPABASE_SERVICE_ROLE_KEY`. (The older `service_role` key on the **Legacy API Keys** tab also works, but Supabase retires legacy keys at the end of 2026, so prefer the secret key.)

> [!CAUTION]
> The `service_role` key bypasses all row-level security: anyone holding it can read and delete everything. It is **server-only**. Put it only in `.env`, Vercel environment variables and GitHub Actions secrets. Never in browser code, never with a `NEXT_PUBLIC_` prefix, never in a commit or screenshot. Do **not** use the `anon` / publishable key: the backend needs the service role.

---

## 2. Gemini API key

- [ ] Go to <https://aistudio.google.com/apikey> and sign in with your Google account.
- [ ] Click **Create API key**. Pick an existing Google Cloud project or let it create one.
- [ ] Copy the key (starts with `AIza`). This is `GEMINI_API_KEY`.

**Check:** the key shows in the AI Studio key list. It is tested for real in step 5.

The default model ids are in `backend/src/core/config.py`: chat `gemini-3.6-flash` (falling back to `gemini-3.5-flash`, then `gemini-3.8-flash`), rewrite `gemini-3.5-flash-lite` (falling back to `gemini-3.1-flash-lite`, then `gemini-3.6-flash`), embeddings `gemini-embedding-001`. When one model is overloaded or retired, the backend moves on to the next automatically. You only need the `GEMINI_*_MODEL` / `GEMINI_*_FALLBACK_MODELS` variables to change that order; compare against [Google's model list](https://ai.google.dev/gemini-api/docs/models).

---

## 3. Resend key (contact-form email)

- [ ] Sign up at <https://resend.com>. **Remember which email address you sign up with.**
- [ ] **API Keys** → **Create API Key**. Name: `portfolio`. Permission: **Sending access**. Click **Add**.
- [ ] Copy the key (starts with `re_`). It is shown **only once**. This is `RESEND_API_KEY`.

> [!IMPORTANT]
> **Sender caveat.** Until you verify your own domain in Resend, you must send from `Portfolio <onboarding@resend.dev>`, and Resend will **only deliver to the address you signed up to Resend with**. So for now, set `CONTACT_TO_EMAIL` to that exact address. If it's a different address, emails silently fail (the message is still saved in Supabase; see [troubleshooting](troubleshooting.md#contact-form-works-but-no-email-arrives)).
> Later, once you own a domain: Resend → **Domains** → **Add Domain**, add the DNS records it shows, then change `CONTACT_FROM_EMAIL` to e.g. `Portfolio <hello@yourdomain.com>` and redeploy.

---

## 4. Generate `IP_HASH_SALT`

Visitor IPs are hashed with this salt before they are stored for rate limiting. The code falls back to `change-me` if it isn't set, so set a real one.

- [ ] Run:
  ```bash
  openssl rand -hex 32
  ```
- [ ] Save the 64-character output. This is `IP_HASH_SALT`. Use the same value everywhere; changing it later just resets everyone's rate-limit counters.

---

## 5. Fill `.env` locally and index the content

- [ ] Create your local env file (it is git-ignored):
  ```bash
  cp .env.example .env
  ```
- [ ] Open `.env` and fill in `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `RESEND_API_KEY`, `CONTACT_TO_EMAIL` (your Resend sign-up address, see step 3) and `IP_HASH_SALT`. Leave `ENVIRONMENT=development` and `NEXT_PUBLIC_SITE_URL=http://localhost:3000` as they are for local use.
- [ ] **Preview the indexing** (no API calls, nothing written):
  ```bash
  .venv/bin/python backend/scripts/ingest.py --dry-run
  ```
  **Check:** it lists the sources and a total chunk count (about 28 sources / 87 chunks at the time of writing). Note the chunk total.
- [ ] **Index for real** (embeds with Gemini, uploads to Supabase):
  ```bash
  .venv/bin/python backend/scripts/ingest.py
  ```
  **Check:** it finishes without a traceback. Then in Supabase → **SQL Editor**:
  ```sql
  select count(*) from documents;
  ```
  The count matches the dry-run chunk total.
- [ ] *(Optional but useful)* Try the whole thing locally: `npm run dev:all`, open <http://localhost:3000/api/py/health> (all three `configured` values should be `true`), then ask the chatbot a question at <http://localhost:3000>. Stop it with `Ctrl+C`.

---

## 6. Vercel (deploy)

- [ ] Go to <https://vercel.com/dashboard>. In the team switcher (top left), select the **Portfolio** team.
- [ ] Click **Add New…** → **Project**.
- [ ] Under **Import Git Repository**, find `Professional_Portfolio_Website` and click **Import**.
  Not listed? Click **Adjust GitHub App Permissions** (or **Install**), give the Vercel app access to `ReubenZSTechs/Professional_Portfolio_Website`, and come back.
- [ ] On **Configure Project**:
  - **Vercel Team:** Portfolio.
  - **Project Name:** keep the default or type `reuben-portfolio`. It becomes your free URL: `https://<project-name>.vercel.app`.
  - **Framework Preset:** **Next.js** (it's also pinned in `vercel.json`).
  - **Root Directory:** `./` (leave it).
  - **Build and Output Settings:** leave as they are.
- [ ] Open **Environment Variables** and add every variable below. Shortcut: copy your whole `.env` and paste it into the first **Key** box; Vercel splits it into rows. Then **change `ENVIRONMENT` and `NEXT_PUBLIC_SITE_URL`** to the production values in the table.

  | Name | Where to get it | Production | Preview |
  |---|---|---|---|
  | `GEMINI_API_KEY` | Step 2 | ✅ | ✅ |
  | `SUPABASE_URL` | Step 1 | ✅ | ✅ |
  | `SUPABASE_SERVICE_ROLE_KEY` | Step 1 (server-only secret) | ✅ | ✅ |
  | `RESEND_API_KEY` | Step 3 | ✅ | ✅ |
  | `CONTACT_TO_EMAIL` | Your Resend sign-up address (step 3) | ✅ | ✅ |
  | `CONTACT_FROM_EMAIL` | `Portfolio <onboarding@resend.dev>` until you verify a domain | ✅ | ✅ |
  | `IP_HASH_SALT` | Step 4 | ✅ | ✅ |
  | `ENVIRONMENT` | Type `production` (hides the API docs at `/api/py/docs`) | ✅ | ✅ |
  | `NEXT_PUBLIC_SITE_URL` | `https://<project-name>.vercel.app`, no trailing slash. Custom domain later (step 9) | ✅ | — |
  | `GEMINI_CHAT_MODEL` | Optional. Leave unset to use the default | optional | optional |
  | `GEMINI_REWRITE_MODEL` | Optional. Leave unset to use the default | optional | optional |
  | `GEMINI_EMBED_MODEL` | Optional. **Changing it means re-indexing everything** (`ingest.py --force`) | optional | optional |

  Variables added on this import screen apply to every environment. That's fine for a first deploy; you can narrow them later in **Settings → Environment Variables**.
- [ ] Click **Deploy** and wait for the build (a few minutes).
  **Check:** you see the "Congratulations" screen with a preview of the site. Click **Continue to Dashboard**. The URL under **Domains** is your live site. If it differs from what you put in `NEXT_PUBLIC_SITE_URL` (Vercel adds a suffix when a name is taken), fix the variable in **Settings → Environment Variables** and redeploy (**Deployments** → newest → **⋯** → **Redeploy**).

> Env-var changes only reach **new** deployments. After editing any variable, always redeploy.

**How the API is wired.** `vercel.json` deploys `api/index.py` as a Python function (with `backend/src/**` bundled through `includeFiles`, max duration 60 s). In production, `next.config.ts` rewrites `/api/py/*` to `/api/index`, and FastAPI routes the original `/api/py/...` path. Vercel installs Python packages from the root `requirements.txt`.

---

## 7. Post-deploy checks

Replace `<site>` with your live URL.

- [ ] **Health:** open `https://<site>/api/py/health` in a browser, or:
  ```bash
  curl -s https://<site>/api/py/health
  ```
  **Check:** `"status": "ok"`, `"environment": "production"`, and
  `"configured": {"gemini": true, "supabase": true, "resend": true}`. Any `false` means that variable is missing or misspelled in Vercel (then redeploy).

> [!WARNING]
> **If `/api/py/health` returns 404.** The Python-function routing (the rewrite to `/api/index`) has been tested locally but **not yet on a real Vercel deployment**, so this is the most likely first-deploy problem. Follow [troubleshooting.md → API returns 404 on Vercel](troubleshooting.md#api-returns-404-on-vercel): check the deployment's **Functions** tab lists `api/index.py`, check the rewrite in `next.config.ts`, check the function logs for `ModuleNotFoundError`, and as a fallback change the rewrite destination to `/api` and push again.

- [ ] **Chatbot:** open the homepage, click a suggested question (or type one, e.g. "What projects has Reuben built?").
  **Check:** the answer streams in word by word and shows source links. "The assistant isn't configured yet" or "I don't have that…" for everything → see [troubleshooting.md](troubleshooting.md).
- [ ] **Contact form:** send yourself a short test message from the Contact section of the homepage.
  **Check:** you get a success message on the page, an email arrives at `CONTACT_TO_EMAIL`, and the message appears in Supabase → **Table Editor** → `contact_messages`.
- [ ] **CV:** click **Download CV**.
  **Check:** your PDF opens (`/cv.pdf`), not a 404 page.

---

## 8. GitHub Actions secrets (auto re-indexing)

`.github/workflows/ingest.yml` re-indexes the chatbot whenever a push to `main` changes `content/`, `knowledge/`, `backend/src/rag/` or `backend/scripts/ingest.py`. It needs three secrets.

- [ ] GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add each one (name exactly as written, value from your `.env`), clicking **Add secret** after each:
  - `GEMINI_API_KEY`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`

  **Check:** all three are listed under **Repository secrets**.
- [ ] Run it once by hand: **Actions** tab → **Re-index RAG content** (left list) → **Run workflow** → branch `main`, leave **force** unticked → **Run workflow**.
  **Check:** the run finishes with a green tick. Because you already indexed in step 5, it should have little or nothing new to embed, and `select count(*) from documents;` is unchanged.
  Tick **force** only after changing the embedding model or size: it re-embeds every chunk.

---

## 9. Custom domain (optional)

- [ ] Vercel → your project → **Settings** → **Domains** → enter your domain → **Add**.
- [ ] At your domain registrar, add the DNS records Vercel shows (an `A` record for the bare domain and/or a `CNAME` for `www`). Wait until Vercel shows **Valid Configuration** (minutes to a few hours).
- [ ] **Settings** → **Environment Variables** → edit `NEXT_PUBLIC_SITE_URL` to `https://yourdomain.com` (no trailing slash) → **Save**.
- [ ] **Deployments** → newest → **⋯** → **Redeploy**. `NEXT_PUBLIC_*` values are baked in at build time, so the redeploy is required for the sitemap and social cards to use the new address.

**Check:** `https://yourdomain.com` loads with a padlock, and `https://yourdomain.com/api/py/health` still shows all `true`.

---

## 10. Day-to-day

- **Make a change:** edit → `git add -A` → `git commit -m "…"` → `git push origin main`. Vercel builds and deploys production automatically; there's no manual redeploy. Pushes to other branches get their own preview URLs. Content edits are covered in [content-guide.md](content-guide.md), and the chatbot re-indexes itself (step 8).
- **Roll back:** Vercel → project → **Deployments** → pick the last good one → **⋯** → **Promote to Production** (or **Instant Rollback**). Takes seconds; then fix forward with a new push.
- **Logs:** Vercel → project → **Logs**, filter by `/api/py`. Backend logs are JSON lines with an `event` field such as `rewrite`, `retrieved` or `answered`. Contact-email problems log `contact_email_failed`.
- **Read contact messages:** they're emailed to you, and every one is also stored in Supabase → **Table Editor** → `contact_messages` (newest first by `created_at`).
- **Supabase pausing:** free projects pause after a period of inactivity. If the chatbot suddenly says it isn't configured or errors, check the project isn't paused in the Supabase dashboard and click **Restore**.
- **Rotating a key:** create the new key in the provider, update it in `.env`, Vercel (then redeploy) and, for the three ingest keys, GitHub Actions secrets. Then delete the old key.

---

## Optional: self-host the API

`deploy/home_server/` contains a Dockerfile and compose file that run the same FastAPI app on your own machine:
```bash
docker compose -f deploy/home_server/docker-compose.yaml up -d --build
```
Route `/api/py/*` to it from your reverse proxy (with nginx, also set `proxy_buffering off;` so streaming works). The Next.js site can still live on Vercel.
