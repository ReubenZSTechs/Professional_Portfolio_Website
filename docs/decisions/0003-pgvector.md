# ADR 0003: Supabase pgvector instead of a dedicated vector database

**Status:** accepted · **Date:** 2026-11-08

## Context
The corpus is small (tens of documents, ~100 chunks). The backend also needs somewhere to store contact messages and rate-limit counters.

## Decision
Use Supabase Postgres with the `vector` extension, an HNSW cosine index, and a `match_documents` RPC that supports metadata filters. Embeddings are 768-dimensional `gemini-embedding-001` vectors (truncated and L2-normalised).

## Consequences
- One managed database with a free tier for everything; SQL for debugging.
- Row-level security is on, with no public policies: only the server (service-role key) can read or write.
- Changing the embedding size needs a migration plus a full re-ingest (documented in `docs/database.md`).
