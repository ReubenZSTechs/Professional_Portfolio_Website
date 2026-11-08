-- 0001_init.sql: RAG store, contact form inbox and rate limiting for the portfolio backend.
--
-- Access model: RLS is enabled on every table and NO policies are created, and the anon /
-- authenticated roles lose their default grants. Only the backend, using the service-role key
-- (which bypasses RLS), can read or write. The browser never talks to Supabase directly.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
-- Supabase convention: keep extensions out of `public` (the security advisor flags it).
create schema if not exists extensions;
create extension if not exists vector with schema extensions;
-- gen_random_uuid() is built into Postgres 13+, no pgcrypto needed.

-- ---------------------------------------------------------------------------
-- documents: one row per embedded chunk
-- ---------------------------------------------------------------------------
create table if not exists public.documents (
  id            uuid primary key default gen_random_uuid(),
  source_type   text not null,                 -- project | experience | research | knowledge | ...
  source_id     text not null,                 -- stable id of the source, e.g. project:plantatio
  title         text not null,
  url           text,                          -- site path used for citations, e.g. /projects/plantatio
  section       text,                          -- heading path inside the source, e.g. "How it works > Retrieval"
  chunk_index   int  not null,
  content       text not null,                 -- the exact text that was embedded (title/section prefixed)
  content_hash  text not null,                 -- sha256 over embed model + dim + content; drives re-embedding
  metadata      jsonb not null default '{}'::jsonb,
  embedding     extensions.vector(768),        -- must match EMBED_DIM in backend/src/core/config.py
  updated_at    timestamptz not null default now(),
  constraint documents_source_chunk_key unique (source_id, chunk_index)
);

comment on table public.documents is 'RAG chunks written by backend/scripts/ingest.py. Service role only.';

-- Approximate nearest-neighbour index for cosine distance (<=>).
create index if not exists documents_embedding_hnsw_idx
  on public.documents
  using hnsw (embedding extensions.vector_cosine_ops);

create index if not exists documents_source_type_idx on public.documents (source_type);

-- Keep updated_at honest on every UPDATE / upsert.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists documents_set_updated_at on public.documents;
create trigger documents_set_updated_at
  before update on public.documents
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- match_documents: cosine similarity search used by backend/src/rag/retriever.py
-- ---------------------------------------------------------------------------
-- `filter` is matched with jsonb containment (@>) against the row's metadata merged with its
-- source_type and source_id columns, so {"source_type": "project"} and {"featured": true} both work.
create or replace function public.match_documents(
  query_embedding extensions.vector(768),
  match_count     int   default 6,
  min_similarity  float default 0,
  filter          jsonb default '{}'::jsonb
)
returns table (
  id           uuid,
  source_type  text,
  source_id    text,
  title        text,
  url          text,
  section      text,
  chunk_index  int,
  content      text,
  metadata     jsonb,
  similarity   float
)
language sql
stable
set search_path = public, extensions
as $$
  select
    d.id,
    d.source_type,
    d.source_id,
    d.title,
    d.url,
    d.section,
    d.chunk_index,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity
  from public.documents d
  where d.embedding is not null
    and 1 - (d.embedding <=> query_embedding) >= min_similarity
    and (
      filter is null
      or filter = '{}'::jsonb
      or (d.metadata || jsonb_build_object('source_type', d.source_type, 'source_id', d.source_id)) @> filter
    )
  order by d.embedding <=> query_embedding
  limit least(greatest(match_count, 1), 50);
$$;

-- ---------------------------------------------------------------------------
-- contact_messages: contact form inbox (also emailed via Resend)
-- ---------------------------------------------------------------------------
create table if not exists public.contact_messages (
  id          uuid primary key default gen_random_uuid(),
  name        text not null check (char_length(name) between 1 and 200),
  email       text not null check (char_length(email) between 3 and 320),
  message     text not null check (char_length(message) between 1 and 5000),
  ip_hash     text,                            -- salted hash, never the raw IP
  created_at  timestamptz not null default now()
);

create index if not exists contact_messages_created_at_idx on public.contact_messages (created_at desc);

-- ---------------------------------------------------------------------------
-- rate_limits + check_rate_limit: fixed-window counters (serverless has no shared memory)
-- ---------------------------------------------------------------------------
create table if not exists public.rate_limits (
  key           text not null,                 -- e.g. chat:<ip_hash>
  window_start  timestamptz not null,
  count         int not null default 0,
  primary key (key, window_start)
);

create index if not exists rate_limits_window_start_idx on public.rate_limits (window_start);

-- Increments the counter for the current window and returns true while the caller is within
-- p_max requests per p_window_seconds. The single INSERT .. ON CONFLICT .. RETURNING is atomic,
-- so concurrent requests can't both read a stale count.
create or replace function public.check_rate_limit(
  p_key            text,
  p_window_seconds int,
  p_max            int
)
returns boolean
language plpgsql
volatile
set search_path = ''
as $$
declare
  v_window_start timestamptz;
  v_count        int;
begin
  if p_window_seconds is null or p_window_seconds <= 0 then
    raise exception 'p_window_seconds must be positive';
  end if;

  v_window_start := to_timestamp(
    floor(extract(epoch from now()) / p_window_seconds) * p_window_seconds
  );

  insert into public.rate_limits as rl (key, window_start, count)
  values (p_key, v_window_start, 1)
  on conflict (key, window_start)
  do update set count = rl.count + 1
  returning rl.count into v_count;

  -- Cheap housekeeping: drop this key's old windows, and occasionally everyone's stale rows.
  delete from public.rate_limits
   where key = p_key and window_start < v_window_start;
  if random() < 0.01 then
    delete from public.rate_limits where window_start < now() - interval '1 day';
  end if;

  return v_count <= p_max;
end;
$$;

-- ---------------------------------------------------------------------------
-- Row Level Security and grants: service role only
-- ---------------------------------------------------------------------------
alter table public.documents        enable row level security;
alter table public.contact_messages enable row level security;
alter table public.rate_limits      enable row level security;

-- No policies on purpose. Also drop Supabase's default table grants for the public API roles.
revoke all on table public.documents        from anon, authenticated;
revoke all on table public.contact_messages from anon, authenticated;
revoke all on table public.rate_limits      from anon, authenticated;

revoke execute on function public.match_documents(extensions.vector, int, float, jsonb)
  from public, anon, authenticated;
revoke execute on function public.check_rate_limit(text, int, int)
  from public, anon, authenticated;
revoke execute on function public.set_updated_at() from public, anon, authenticated;

grant execute on function public.match_documents(extensions.vector, int, float, jsonb) to service_role;
grant execute on function public.check_rate_limit(text, int, int) to service_role;
