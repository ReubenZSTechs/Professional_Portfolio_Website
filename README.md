# Reuben Zachary Susanto: AI Engineer portfolio

Personal portfolio for agentic-AI engineering work, with an **"Ask my portfolio" assistant**: a LangGraph agent that answers recruiters' questions from my CV and project case studies, citing its sources.

**Stack:** Next.js 16 (TypeScript, static) · FastAPI + LangGraph (Python 3.12) · Google Gemini · Supabase Postgres + pgvector · Resend · Vercel

## How the assistant works
```
question ─▶ compile_history ─▶ prompt rewriter ─┬─▶ retrieve (pgvector) ─▶ answering agent ─▶ streamed answer + [n] citations
            (trim + summarise)  (Gemini Flash-Lite,└────────────────────────▶ (greetings / off-topic / unsafe)
                                 structured output)
```
- The **prompt-rewriter agent** turns follow-ups like "what stack did it use?" into standalone English queries, and classifies intent.
- The **answering agent** answers only from retrieved passages, cites them as `[n]`, says so when it doesn't know, and replies in the visitor's language.
- Content is re-indexed automatically on every push (only changed chunks are re-embedded).

Details: [docs/agent-graph.md](docs/agent-graph.md) · [docs/rag.md](docs/rag.md)

## Quickstart
```bash
npm install
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env     # optional for the static site; required for chat and contact
npm run dev:all          # http://localhost:3000
```

## Editing content
Everything on the site comes from **`content/`**: `site.yaml` (headline, links, colour), `home.yaml` (section order), YAML files for experience, education and skills, and one MDX file per project in `content/projects/`. Edit, push to `main`, and Vercel redeploys while GitHub Actions re-indexes the assistant. Full guide: [docs/content-guide.md](docs/content-guide.md).

## Security
Layered protection for a public LLM app: Vercel Firewall rules, CSP/HSTS headers, Origin and size checks, Cloudflare Turnstile, per-visitor and site-wide (500/day) limits, and chatbot guardrails (signed history, English/Indonesian injection screening, spotlighted prompts, Gemini safety filters, canary-based leak detection), with a live red-team eval suite. See [docs/security.md](docs/security.md) and [SECURITY.md](SECURITY.md).

## Documentation
| | |
|---|---|
| [Architecture](docs/architecture.md) | system overview, request lifecycle, folder map |
| [Agent graph](docs/agent-graph.md) | LangGraph nodes, prompts, routing, streaming |
| [RAG](docs/rag.md) · [Database](docs/database.md) | chunking, embeddings, Supabase schema |
| [API](docs/api.md) | `/api/py/chat` (SSE), `/contact`, `/health` |
| [Content guide](docs/content-guide.md) | how to edit everything |
| [Design system](docs/design-system.md) | tokens, components, dark mode, accessibility |
| [Deployment](docs/deployment.md) | Supabase → Gemini → Resend → Vercel, step by step |
| [Local development](docs/local-development.md) · [Testing](docs/testing.md) · [Troubleshooting](docs/troubleshooting.md) | |
| [Decisions](docs/decisions/) | architecture decision records |

## Repository layout
```
content/        editable YAML + project MDX        src/            Next.js app (pages, components, lib)
knowledge/      chatbot-only background notes      backend/        FastAPI + LangGraph + RAG (Python)
public/         images, CV                         api/index.py    Vercel Python entrypoint
supabase/       SQL migrations                     docs/           documentation
```

## License
Code: MIT. Written content and images © Reuben Zachary Susanto.
