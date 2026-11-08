# Retrieval-augmented generation (RAG)

The "Ask my portfolio" chat answers only from Reuben's own content. This page covers how that content gets into the vector store and how it comes back out. For how the LangGraph nodes use it, see [agent-graph.md](agent-graph.md). For the tables and RPCs, see [database.md](database.md).

```
content/ + knowledge/ ──▶ loaders ──▶ chunker ──▶ sync plan ──▶ Gemini embed ──▶ Supabase documents
                                                     ▲   (hash skip)                   │
                                                     └──────── fetch_index ◀───────────┘

question ──▶ rewrite_query ──▶ embed (RETRIEVAL_QUERY) ──▶ match_documents RPC ──▶ [1]…[n] context + sources
```

## Code map

| File | Role |
|---|---|
| [`backend/src/rag/loaders.py`](../backend/src/rag/loaders.py) | Reads MDX/YAML/Markdown and returns `SourceDocument`s |
| [`backend/src/rag/chunker.py`](../backend/src/rag/chunker.py) | MDX cleanup, heading split, size-bounded packing with overlap |
| [`backend/src/rag/models.py`](../backend/src/rag/models.py) | `SourceDocument`, `Chunk`, `RetrievedChunk`, `content_hash()` |
| [`backend/src/rag/sync.py`](../backend/src/rag/sync.py) | Pure diff of new chunks against indexed rows: embed / patch / delete |
| [`backend/src/rag/store.py`](../backend/src/rag/store.py) | Supabase reads/writes for ingest (paginated, batched) |
| [`backend/src/rag/embedder.py`](../backend/src/rag/embedder.py) | Batching and backoff around `GeminiClient.embed` |
| [`backend/src/rag/retriever.py`](../backend/src/rag/retriever.py) | `retrieve(query, k, min_similarity, filter)` → `list[RetrievedChunk]` |
| [`backend/src/tools/rag_search.py`](../backend/src/tools/rag_search.py) | What the graph calls: chunks + numbered `context` + `sources` for the UI |
| [`backend/src/llm/gemini.py`](../backend/src/llm/gemini.py) | Thin google-genai wrapper: `generate`, `generate_json`, `stream`/`astream`, `embed` |
| [`backend/scripts/ingest.py`](../backend/scripts/ingest.py) | The CLI that runs the whole ingestion pipeline |

## Sources

| Source | `source_type` | `source_id` | `url` |
|---|---|---|---|
| `content/projects/*.mdx` (files starting with `_`, like `_template.mdx`, and `draft: true` files are skipped) | `project` | `project:<slug>` | `/projects/<slug>` |
| `content/{experience,research,awards,skills,education,certifications,leadership,teaching,languages}.yaml`, **one document per entry**; missing files are skipped | the file name | `<file>:<slug of entry title>` | `/#<file>` |
| `knowledge/**/*.md`: RAG-only facts that aren't rendered on the site | `knowledge` | `knowledge:<relative path>` | frontmatter `url`, or none |

`site.yaml`, `home.yaml` and `suggested-questions.yaml` are layout, not facts, and are not indexed.

Details worth knowing:
- **Project frontmatter is indexed too.** `summary, highlight, role, timeline, status, category, series, stack, tags, repo, demo` are rendered into an "At a glance" section, so questions like "what stack did Plantatio use?" hit. All frontmatter is also stored in `metadata`, which is what the `filter` argument matches.
- **YAML is rendered generically** as `Key: value` lines. Short lists go on one line (`Stack: Python, Neo4j`) and sentence lists become `- ` bullets. A file can be a list of entries, a mapping with an `items:` list, or a mapping of groups (`{languages: [...], frameworks: [...]}`). Entry titles come from the first of `title, name, role, position, degree, field, group, award, label`, plus `— company/organization/institution/issuer` when present.
- **Placeholders are never indexed.** `<Todo>…</Todo>` blocks in MDX and any value starting with `TODO` in YAML or frontmatter are dropped, so the bot can't repeat "TODO: add the RAGAS scores".
- **IDs are stable.** YAML ids come from the entry title (or an explicit `id:`/`slug:`), not its position, so reordering a file doesn't re-embed it. If two entries share a title, the id gets their `year`/`date`/`start` appended (`awards:rector-s-list-calvin-institute-of-technology-2024`).

## Chunking

[`chunk_document()`](../backend/src/rag/chunker.py) runs on each source:

1. **Clean MDX** (`clean_mdx`). Removes `import`/`export` lines, `{/* */}` and `<!-- -->` comments, and `<Todo>`. React components become text **that keeps their props**, so the numbers survive:
   - `<Metric value="92%" label="Top-1 accuracy" />` → `Metric (value: 92%; label: Top-1 accuracy)`
   - `<Pipeline steps={["Question", "Decompose", "Answer"]} />` → `Pipeline (steps: Question, Decompose, Answer)`
   - `<Decision title="…">children</Decision>` → `Decision (title: …)` followed by the children text

   Presentational props (`className`, `src`, `href`, `highlight`, `width`, …) are dropped. Lowercase HTML tags are removed but their text is kept. Fenced code blocks are never touched, and `<` in prose (`p < 0.05`, autolinks) is left alone.
2. **Split by heading** (`split_sections`). Each section remembers its heading path (`How it works > Retrieval`). A `# H1` that repeats the title is ignored. Headings inside code fences don't count.
3. **Pack** (`pack`). Sections up to **800 tokens** (≈3,200 chars, estimated at 4 chars/token) become one chunk. Longer sections are packed paragraph by paragraph, with **~80 tokens of overlap**: the last paragraph, or the tail of a long one, is repeated at the start of the next chunk. Oversized paragraphs fall back to sentences, then words. Code blocks stay whole.
4. **Prefix.** Each chunk starts with `Title — Section\n\n`, so an isolated chunk still says what it's about. That helps the embedding and the answering model. `RetrievedChunk.body` strips the prefix again for snippets.

Today's corpus: `python backend/scripts/ingest.py --dry-run` prints a per-source table. At the time of writing it's 28 sources and 87 chunks (~10k tokens). Most project sections fit in one chunk.

## Embeddings

- Model: **`gemini-embedding-001`** (`GEMINI_EMBED_MODEL`) at **768 dimensions** (`EMBED_DIM`, `output_dimensionality`). 768 gives nearly the quality of 3072 at a quarter of the storage, and the HNSW index stays fast.
- **Asymmetric task types.** Chunks use `RETRIEVAL_DOCUMENT` and questions use `RETRIEVAL_QUERY`. Using the same type for both noticeably hurts recall.
- **Normalisation.** Only the native 3072-d output is unit-length. For any smaller dimension, Google says to L2-normalise yourself, and [`GeminiClient.embed`](../backend/src/llm/gemini.py) does that, so cosine scores are comparable.
- Batching: 100 texts per request (the API's batch limit, `EMBED_BATCH_SIZE`). The SDK makes up to 3 attempts on transient errors. `embed_texts` adds an outer exponential backoff (2s, 4s, 8s) for quota (429) bursts during a full re-index.
- Newer option: `gemini-embedding-2` is multimodal and auto-normalises, but it **doesn't accept `task_type`** (you put the task into the text instead). Switching to it needs a change in `GeminiClient.embed`, not just an env var.

## Re-indexing

```bash
python backend/scripts/ingest.py --dry-run
```

```bash
python backend/scripts/ingest.py
```

What a real run does:
1. Loads and chunks everything (same as `--dry-run`).
2. Reads the current index from Supabase: keys, hashes and patchable columns, never the embeddings.
3. Plans the sync ([`plan_sync`](../backend/src/rag/sync.py)), keyed by `(source_id, chunk_index)`:
   - **same hash**: skipped. If only `title/url/section/metadata/source_type` changed (for example you flipped `featured`), the row is patched without re-embedding.
   - **new key or different hash**: embedded and upserted.
   - **key no longer produced** (a chunk was dropped or the whole file was deleted): deleted.
4. Upserts first, then patches, then deletes, so a failed embedding call never leaves the index with fewer rows than before.

The hash covers **embed model + dimension + content**. Changing `GEMINI_EMBED_MODEL` or `EMBED_DIM` therefore re-embeds everything on the next run, with no `--force` needed (you'd still need a migration for a new dimension; see [database.md](database.md#changing-the-embedding-size)).

Flags:

| Flag | Effect |
|---|---|
| `--dry-run` | Chunk and print counts. No Gemini or Supabase calls, no credentials needed |
| `--force` | Re-embed every chunk |
| `--allow-empty` | By default ingest **refuses to delete the whole index** when it finds no content, which usually means a wrong `--content-dir`. This flag allows it |
| `--content-dir`, `--knowledge-dir` | Override the default `content/` and `knowledge/` paths |
| `--max-tokens`, `--overlap-tokens` | Chunk size experiments (defaults 800 / 80) |

Needs `GEMINI_API_KEY`, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, from the repo-root `.env` or the environment. In CI, `.github/workflows/ingest.yml` runs it on pushes to `main` that touch `content/**` or `knowledge/**`.

A known trade-off: inserting a section near the top of a project shifts the `chunk_index` of everything after it, so those chunks are re-embedded even though their text didn't change. At this corpus size that's a fraction of a cent. Matching on hash across indexes would avoid it, but it isn't worth the complexity yet.

## Retrieval

```python
from tools.rag_search import rag_search

result = rag_search("How has Reuben used LangGraph?", k=6, filters={"source_type": "project"})
result.context   # "[1] Plantatio — How it works (/projects/plantatio)\n…\n\n---\n\n[2] …"
result.sources   # [Source(n=1, type="project", title="Plantatio", section=…, snippet=…, url=…, similarity=0.78), …]
result.empty     # True when nothing cleared the threshold → answer "I don't have that information"
```

`retrieve()` embeds the (rewritten, standalone) query, then calls `match_documents` with `RAG_TOP_K` (default 6) and `RAG_MIN_SIMILARITY` (default 0.5). It returns rows best first and logs `hits`, `top_similarity` and latency as JSON. `rag_search` numbers the chunks: `context` goes into the answering prompt (the model cites `[n]`), and `sources` is sent as the SSE `sources` event that fills the UI panel.

## Tuning tips

- **Find the threshold empirically.** Log `top_similarity` for a set of good and off-topic questions. With `gemini-embedding-001` at 768-d, relevant matches typically score around 0.6–0.8 and unrelated ones around 0.4–0.55. Set `RAG_MIN_SIMILARITY` just above the off-topic cluster. If greetings or off-topic questions return sources, raise it. If real questions come back with "I don't know", lower it.
- **Fix the query before tuning k.** Most misses are vague follow-ups ("what stack did it use?"). The `rewrite_query` node turning those into standalone queries ("What tech stack did Plantatio use?") matters more than k.
- **Use filters** when the rewriter detects intent: `{"source_type": "project"}` for project questions, `{"source_type": "experience"}` for work history. Containment filters are applied while scanning, so a narrow filter with a small `k` can return fewer rows than asked. Keep `k` at 6 or more when filtering.
- **k.** 6 chunks is about 2–4k tokens of context, cheap for Flash. Going above ~10 mostly adds noise and slower first tokens.
- **Chunk size.** The sections are short and topical, so 800 tokens rarely splits anything. Smaller chunks (`--max-tokens 400`) give sharper citations, larger ones more context per hit. Re-run the eval set (`backend/tests/evals`) after any change, since `--max-tokens` changes every chunk and triggers a full re-embed.
- **HNSW recall.** Under ~10k rows, pgvector is already near-exact. If results ever look unstable at scale, raise `hnsw.ef_search` (default 40) in a session or in the function.
- **Missing facts.** If a fact isn't on the site but should be answerable, add it to `knowledge/*.md` instead of stuffing frontmatter.
