# Local development

## Prerequisites
- **Node.js 20.9+** (22 recommended) and npm
- **Python 3.12**
- Optional: Docker, the Supabase CLI (`npx supabase`)

## First-time setup
```bash
git clone https://github.com/ReubenZSTechs/Professional_Portfolio_Website.git
cd Professional_Portfolio_Website

npm install                                   # frontend dependencies
python3.12 -m venv .venv                      # backend virtualenv (git-ignored)
.venv/bin/pip install -r requirements.txt pytest pytest-asyncio ruff

cp .env.example .env                          # then fill in the keys you have
```
The site runs without any keys: pages are built from `content/`. The chat needs `GEMINI_API_KEY` + Supabase; the contact form needs Supabase (+ Resend for email). Without them they show a friendly "not configured" message.

## Running
```bash
npm run dev:all     # Next.js on :3000 and FastAPI on :8000 together
# or separately:
npm run dev         # site only
npm run dev:api     # API only (uvicorn --reload)
```
Open http://localhost:3000. Next.js proxies `/api/py/*` to `:8000` (see `next.config.ts`). API docs: http://localhost:8000/api/py/docs.

## Common tasks
| Task | Command |
|---|---|
| Type-check + lint + production build | `npm run check` |
| Backend tests | `cd backend && ../.venv/bin/python -m pytest -q` |
| Backend lint / format | `.venv/bin/ruff check backend api` · `.venv/bin/ruff format backend api` |
| Preview what the chatbot will index | `.venv/bin/python backend/scripts/ingest.py --dry-run` |
| Re-index after editing content | `.venv/bin/python backend/scripts/ingest.py` |
| Live chatbot evals | `cd backend && RUN_EVALS=1 ../.venv/bin/python -m pytest tests/evals -v` |
| Find unfinished placeholders | `grep -rn TODO content` |

## Environment variables
All variables are listed with comments in `.env.example`, and documented in [deployment.md](deployment.md#5-vercel). Backend settings and their defaults live in `backend/src/core/config.py`. Any field there can be overridden by an env var of the same name in upper case (e.g. `RAG_TOP_K=8`).

## Working with a local database (optional)
```bash
npx supabase start          # local Postgres + pgvector in Docker
npx supabase db reset       # applies supabase/migrations
```
Use the local URL and service-role key printed by `supabase start` in `.env`.
