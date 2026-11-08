# Testing

| Layer | What | Command | Needs keys? |
|---|---|---|---|
| Content | every YAML/MDX file validated against `src/lib/schemas.ts` | `npm run build` | no |
| Frontend | TypeScript + ESLint | `npm run typecheck && npm run lint` | no |
| Backend unit | chunker, loaders, sync planner, Gemini wrapper, graph (fake LLM), routing, HTTP routes | `cd backend && ../.venv/bin/python -m pytest -q` | no |
| Backend lint | ruff | `.venv/bin/ruff check backend api` | no |
| Live evals | golden questions against real Gemini + Supabase | `cd backend && RUN_EVALS=1 ../.venv/bin/python -m pytest tests/evals -v` | yes |

CI (`.github/workflows/ci.yml`) runs everything except the live evals on every pull request and push to `main`.

## Unit tests
`backend/tests/unit/`. Network calls are replaced with fakes, so the suite runs in about a second. Highlights:
- `test_graph.py`: whole-graph runs with a fake Gemini. Checks the event order, that retrieval uses the *rewritten* query, that only cited sources are sent, that greetings skip retrieval, that unsafe messages never reach the answering model, and that a failed rewriter falls back to the raw question.
- `test_routing.py`: the contract for `route_after_rewrite`.
- `test_routes.py`: the SSE framing, input validation, honeypot, "store before email", and that internal errors never leak to the browser.
- `conftest.py` stops tests from reading your real `.env`.

## Live evals
`backend/tests/evals/golden.yaml` lists questions with the sources a good answer must cite (or `expect_no_sources: true` for questions the bot should decline). Run the evals after changing prompts, models, chunking or `RAG_*` settings, and after a big content edit.

Adding a case:
```yaml
- question: What evaluation metrics does SIGAP use?
  expect_sources: [SIGAP]
- question: "and how long did it take?"     # follow-up: tests the rewriter
  history:
    - { role: user, content: Tell me about Arthur }
    - { role: assistant, content: Arthur summarises research papers… }
  expect_sources: [Arthur]
```
A run costs a few cents in Gemini usage. Prerequisite: the index is populated (`backend/scripts/ingest.py`).

## Manual checks before sharing the link
- Homepage and two case studies at phone width (375px) and desktop, in light and dark mode.
- Keyboard only: Tab through the nav, chat, and contact form; focus rings are visible.
- Lighthouse (Chrome DevTools → Lighthouse) ≥ 95 for Performance, Accessibility, Best Practices and SEO.
- `/api/py/health` shows every integration configured; one chat question and one contact message work end to end.
