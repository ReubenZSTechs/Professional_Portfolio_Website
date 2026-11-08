# Documentation

Everything about how this portfolio works, how to run it, and how to change it.

## Start here
| I want to… | Read |
|---|---|
| Change text, pin a project, add a project, reorder sections | [content-guide.md](content-guide.md) |
| Run the site on my laptop | [local-development.md](local-development.md) |
| Deploy to Vercel with Supabase, Gemini and Resend | [deployment.md](deployment.md) |
| Fix something that broke | [troubleshooting.md](troubleshooting.md) |

## How it works
| Topic | Read |
|---|---|
| System overview, request lifecycle, folder map | [architecture.md](architecture.md) |
| The LangGraph agent (prompt rewriter → answering) | [agent-graph.md](agent-graph.md) |
| Retrieval: sources, chunking, embeddings, re-indexing | [rag.md](rag.md) |
| Supabase tables, RPCs, security model, migrations | [database.md](database.md) |
| HTTP API (`/api/py/chat`, `/contact`, `/health`) | [api.md](api.md) |
| Security model, guardrails, incident runbook | [security.md](security.md) |
| Colours, typography, components, dark mode | [design-system.md](design-system.md) |
| Unit tests, live evals, CI | [testing.md](testing.md) |
| Why things are built this way | [decisions/](decisions/) |

## Five-minute quickstart
```bash
npm install
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env        # fill in keys (the site runs without them; the chat needs them)
npm run dev:all             # http://localhost:3000 (Next.js) + :8000 (FastAPI)
```
Edit anything in `content/`, save, and the page reloads. Push to `main` to publish.
