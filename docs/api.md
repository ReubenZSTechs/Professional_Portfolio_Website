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
    { "role": "assistant", "content": "Plantatio is a GraphRAG system… [1]" }
  ]
}
```
| Field | Rules |
|---|---|
| `message` | 1–500 characters after trimming (`MAX_QUESTION_CHARS`) |
| `history` | up to 60 turns; the server uses the last `MAX_HISTORY_TURNS` × 2 |

**Response**: `200 text/event-stream`. Each frame is `event: <name>\ndata: <json>\n\n`:

| Event | Data | When |
|---|---|---|
| `status` | `{"stage": "rewriting" \| "retrieving" \| "answering"}` | as each graph step starts |
| `token` | `{"text": "He cut token costs "}` | repeatedly while the answer streams |
| `sources` | `{"sources": [{"id": 1, "type": "experience", "title": "FlyRank AI", "section": "…", "snippet": "…", "url": "/#experience"}]}` | after the answer, only cited sources |
| `error` | `{"message": "…", "code": "config" \| "internal"}` | something failed; the message is safe to show |
| `done` | `{}` | always last |

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

**Errors before streaming**: `422` invalid body (e.g. question too long), `429` rate limit (`Retry-After` header; default 20 questions per 10 minutes per visitor).

## `POST /api/py/contact`
Saves a contact-form message to `contact_messages`, then emails it via Resend with `Reply-To` set to the visitor.

**Request**
```json
{ "name": "Ana", "email": "ana@company.com", "message": "We'd love to talk about an AI Engineer role.", "company": "" }
```
`company` is a honeypot: it's hidden in the form. If it's filled in, the server returns success without storing anything.

**Responses**: `200 {"ok": true}` · `422` invalid input (e.g. `"Please enter a valid email address."`) · `429` too many messages (default 3 per hour) · `503` the database is unavailable (the email is never attempted without a stored copy).

## `GET /api/py/health`
```json
{
  "status": "ok",
  "environment": "production",
  "configured": { "gemini": true, "supabase": true, "resend": true },
  "models": { "chat": "…", "rewrite": "…", "embed": "gemini-embedding-001" }
}
```
Shows which integrations have credentials, never the credentials themselves. Use it right after deploying.
