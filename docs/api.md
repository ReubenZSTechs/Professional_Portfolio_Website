# HTTP API

All endpoints live under `/api/py` on the same domain as the site. Interactive docs (development only): `http://localhost:8000/api/py/docs`. The TypeScript client is `src/lib/api.ts`; keep the two in sync.

Errors use FastAPI's shape with a human-readable message: `{"detail": "Please keep questions under 500 characters."}`.

## `POST /api/py/chat`
Ask the portfolio assistant a question. Responds with a **Server-Sent Events** stream.

**Request**
```json
{
  "message": "What stack did it use?",
  "history": [
    { "role": "user", "content": "Tell me about Plantatio" },
    { "role": "assistant", "content": "Plantatio is a GraphRAG system… [1]", "sig": "Qm9y…" }
  ],
  "turnstile_token": "0.AbC…"
}
```
Headers: `Content-Type: application/json` (required), and `X-Chat-Session: v1.…` once the browser has a session.

| Field | Rules |
|---|---|
| `message` | 1–500 characters after normalisation (`MAX_QUESTION_CHARS`) |
| `history` | up to 20 turns, each ≤ 12,000 characters. **Assistant turns must carry the `sig` from their `done` event**, otherwise they are dropped (forgery protection) |
| `turnstile_token` | Cloudflare Turnstile token. Required when there's no valid `X-Chat-Session` and Turnstile is enabled |

Whole request ≤ 64 KB; the browser `Origin` must be this site (see [security.md](security.md)).

**Response**: `200 text/event-stream`. Each frame is `event: <name>\ndata: <json>\n\n`:

| Event | Data | When |
|---|---|---|
| `session` | `{"token": "v1.…"}` | first, only after a Turnstile check was just passed; send it back as `X-Chat-Session` (valid 30 min) |
| `status` | `{"stage": "rewriting" \| "retrieving" \| "answering"}` | as each graph step starts |
| `token` | `{"text": "He cut token costs "}` | repeatedly while the answer streams |
| `sources` | `{"sources": [{"id": 1, "type": "experience", "title": "FlyRank AI", "section": "…", "snippet": "…", "url": "/#experience"}]}` | after the answer, only cited sources |
| `retract` | `{"text": "I can only answer…"}` | the output guard stopped the answer: **replace** everything shown so far with `text` |
| `error` | `{"message": "…", "code": "config" \| "busy" \| "internal"}` | something failed; the message is safe to show |
| `done` | `{"sig": "…"}` | always last. `sig` signs the final visible answer (absent after an error) |

Example:
```
event: status
data: {"stage": "rewriting"}

event: token
data: {"text": "Plantatio uses LangGraph, Neo4j "}

event: sources
data: {"sources": [{"id": 1, "type": "project", "title": "Plantatio", ...}]}

event: done
data: {}
```

**Errors before streaming** (JSON `{"detail": "…"}` plus an `X-Error-Code` header):

| Status | `X-Error-Code` | Meaning |
|---|---|---|
| 403 | `origin` | request didn't come from this site |
| 403 | `verification` | Turnstile token missing or invalid: get a fresh one and retry |
| 413 | `too_large` | body over 64 KB |
| 415 | `content_type` | not `application/json` |
| 422 | — | invalid body (e.g. question too long) |
| 429 | `rate_limited` | per-visitor limit (5/min, 20/10 min); see `Retry-After` |
| 429 | `quota` | site-wide daily cap reached (500/day, resets 00:00 UTC) |
| 503 | `config` / `unavailable` | a required secret is missing, or the rate limiter is unreachable (fails closed) |

Questions blocked by the injection guard still return `200`: a `token` event with the standard refusal, then `done`.

## `POST /api/py/contact`
Saves a contact-form message to `contact_messages`, then emails it via Resend with `Reply-To` set to the visitor.

**Request**
```json
{ "name": "Ana", "email": "ana@company.com", "message": "We'd love to talk about an AI Engineer role.", "company": "", "turnstile_token": "0.AbC…" }
```
`company` is a honeypot: it's hidden in the form. If it's filled in, the server returns success without storing anything. `turnstile_token` is required when Turnstile is enabled. Line breaks and control characters are stripped from `name` (it becomes the email subject).

**Responses**: `200 {"ok": true}` · `403` (`verification`) bot check failed · `422` invalid input (e.g. `"Please enter a valid email address."`) · `429` too many messages (default 3 per hour) · `503` the database or rate limiter is unavailable (the email is never attempted without a stored copy). The same Origin, JSON-only and size rules as the chat apply.

## `GET /api/py/health`
Deployed (production and previews): just `{"status": "ok"}`, so the endpoint reveals nothing about the setup.

Local development adds the diagnostics the chat panel uses to explain setup problems:
```json
{
  "status": "ok",
  "environment": "development",
  "configured": { "gemini": true, "supabase": true, "resend": false, "turnstile": false, "chat_signing_secret": false },
  "models": { "chat": "…", "rewrite": "…", "embed": "gemini-embedding-001", "chat_fallbacks": ["…"], "rewrite_fallbacks": ["…"] }
}
```
These flags only say whether a credential is present, never its value.
