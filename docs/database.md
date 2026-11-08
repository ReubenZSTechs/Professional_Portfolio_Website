# Database (Supabase Postgres)

The backend uses one Supabase project for three things: the RAG vector store, the contact-form inbox, and rate-limit counters. The schema lives in [`supabase/migrations/`](../supabase/migrations/). It currently has one migration, [`0001_init.sql`](../supabase/migrations/0001_init.sql).

## Access model

- **Only the backend touches the database.** It connects with the **service-role key** (`SUPABASE_SERVICE_ROLE_KEY`), which bypasses Row Level Security. The browser never gets a Supabase key.
- **RLS is enabled on every table, and there are no policies.** With RLS on and no policies, the `anon` and `authenticated` roles can't see or change any rows.
- The migration also **revokes** Supabase's default table grants and `EXECUTE` on the RPCs from `anon`, `authenticated` and `public`. So even if the anon key leaked, PostgREST would answer "permission denied" instead of returning empty results.
- Every function sets `search_path` (`''`, or `public, extensions` for the vector search), as the Supabase security advisor recommends.

> If you ever add a table, enable RLS on it in the same migration. A table without RLS can be read with the anon key.

## Tables

### `documents`: RAG chunks

| column | type | notes |
|---|---|---|
| `id` | `uuid` PK | `gen_random_uuid()` |
| `source_type` | `text` | `project`, `experience`, `research`, `awards`, `skills`, `education`, `certifications`, `leadership`, `teaching`, `languages`, `knowledge` |
| `source_id` | `text` | Stable id of the source, e.g. `project:plantatio`, `experience:backend-ai-engineer-flyrank-ai`, `knowledge:resume` |
| `title` | `text` | Shown in the sources panel |
| `url` | `text` | Site path used for citations (`/projects/<slug>`, `/#experience`) |
| `section` | `text` | Heading path inside the source, e.g. `How it works` |
| `chunk_index` | `int` | 0-based position within the source |
| `content` | `text` | Exactly the text that was embedded (prefixed with `Title — Section`) |
| `content_hash` | `text` | sha256 of embed model + dimension + content. Ingest uses it to skip unchanged chunks |
| `metadata` | `jsonb` | Project frontmatter / YAML scalar fields, plus `file` (the source path) |
| `embedding` | `vector(768)` | `gemini-embedding-001` at `output_dimensionality=768`, L2-normalised |
| `updated_at` | `timestamptz` | Set by a trigger on every update |

Constraints and indexes:
- `unique (source_id, chunk_index)`: the upsert key used by ingest.
- An HNSW index on `embedding` with `vector_cosine_ops`, for cosine distance (`<=>`).
- A b-tree index on `source_type`.

### `contact_messages`

| column | type | notes |
|---|---|---|
| `id` | `uuid` PK | |
| `name` | `text` | 1–200 chars (check constraint) |
| `email` | `text` | 3–320 chars |
| `message` | `text` | 1–5000 chars |
| `ip_hash` | `text` | Salted hash of the client IP, never the raw IP |
| `created_at` | `timestamptz` | default `now()`, indexed descending |

### `rate_limits`

| column | type | notes |
|---|---|---|
| `key` | `text` | e.g. `chat:<ip_hash>`, `contact:<ip_hash>` |
| `window_start` | `timestamptz` | Start of the fixed window |
| `count` | `int` | Requests seen in that window |

Primary key `(key, window_start)`, plus an index on `window_start` for cleanup.

## RPCs

Call these with `supabase.rpc(name, params)` (PostgREST `POST /rest/v1/rpc/<name>`).

### `match_documents(query_embedding vector(768), match_count int = 6, min_similarity float = 0, filter jsonb = '{}') → table`

Returns `id, source_type, source_id, title, url, section, chunk_index, content, metadata, similarity`, best match first.

- `similarity = 1 - cosine_distance`, in `[-1, 1]` (in practice about 0.3–0.9 for this model).
- Rows below `min_similarity` are dropped. `match_count` is clamped to 1–50.
- `filter` uses jsonb containment (`@>`) against `metadata`, merged with `source_type` and `source_id`. So all of these work:
  - `{"source_type": "project"}`: projects only
  - `{"source_id": "project:plantatio"}`: one project
  - `{"featured": true}`, `{"category": "agentic"}`: frontmatter fields

```sql
-- psql / SQL editor check (pass a real 768-d vector in practice)
select source_id, section, round(similarity::numeric, 3)
from match_documents((select embedding from documents limit 1), 5, 0.3, '{"source_type":"project"}');
```

### `check_rate_limit(p_key text, p_window_seconds int, p_max int) → boolean`

Increments the counter for the current fixed window and returns `true` while the caller is still within `p_max` requests. The `INSERT … ON CONFLICT DO UPDATE … RETURNING` runs as one statement, so concurrent serverless invocations can't race past the limit. Each call also deletes the key's older windows, and about 1% of calls delete every row older than a day, so the table stays small.

The limits come from `RATE_LIMIT_CHAT_MAX` / `RATE_LIMIT_CHAT_WINDOW_SECONDS` and `RATE_LIMIT_CONTACT_*` in [`backend/src/core/config.py`](../backend/src/core/config.py). Fixed windows allow a burst of up to `2 × max` across a window boundary. That's fine for abuse protection on a portfolio site.

## Applying migrations

**Supabase dashboard (simplest):** SQL Editor → paste the migration file → Run. Every statement is idempotent (`if not exists` / `create or replace`), so re-running it is safe.

**Supabase CLI:**

```bash
supabase link --project-ref <your-project-ref>
```

```bash
supabase db push
```

## Adding a migration

1. Create `supabase/migrations/NNNN_short_name.sql`, numbered after the last one (`0002_add_feedback.sql`). The CLI applies files in name order and records them in `supabase_migrations.schema_migrations`. If you use `supabase migration new <name>` instead, it creates a timestamp-prefixed file, which also sorts correctly.
2. Never edit a migration that has already been applied to production; add a new one.
3. For new tables: `enable row level security`, `revoke all … from anon, authenticated`, and no policies unless the browser genuinely needs access.
4. For new functions: set `search_path`, and revoke `execute` from `public, anon, authenticated`.
5. Apply it locally or to a branch first, run `pytest backend/tests/unit`, then push.

### Changing the embedding size

`vector(768)` must match `EMBED_DIM`. To switch to, say, 1536:

1. Add a migration that drops the HNSW index, runs `alter table documents alter column embedding type extensions.vector(1536) using null` (old vectors can't be converted), recreates the index, and recreates `match_documents` with the new type.
2. Set `EMBED_DIM=1536` everywhere (Vercel, the GitHub Action, `.env`).
3. Run `python backend/scripts/ingest.py`. The content hash includes the dimension, so every chunk is re-embedded automatically.

## Useful queries

```sql
-- chunks per source
select source_type, source_id, count(*) from documents group by 1, 2 order by 1, 2;

-- latest contact messages
select created_at, name, email, left(message, 80) from contact_messages order by created_at desc limit 20;

-- who is being rate limited right now
select key, window_start, count from rate_limits order by count desc limit 20;
```
