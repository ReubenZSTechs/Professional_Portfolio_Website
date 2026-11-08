#!/usr/bin/env python
"""Index the site's content into Supabase for RAG.

    python backend/scripts/ingest.py --dry-run   # chunk counts only, no API calls
    python backend/scripts/ingest.py             # embed changed chunks, upsert, prune stale ones
    python backend/scripts/ingest.py --force     # re-embed everything

Idempotent: unchanged chunks (same content hash) are never re-embedded, so it is cheap to run
on every push (see .github/workflows/ingest.yml). Needs GEMINI_API_KEY, SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY unless --dry-run.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from core.config import get_settings  # noqa: E402
from core.logging import configure_logging, get_logger  # noqa: E402
from rag.chunker import DEFAULT_MAX_TOKENS, DEFAULT_OVERLAP_TOKENS, chunk_document, estimate_tokens  # noqa: E402
from rag.loaders import load_all  # noqa: E402
from rag.models import Chunk  # noqa: E402
from rag.sync import plan_sync  # noqa: E402

log = get_logger("ingest")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="chunk and report; no Gemini/Supabase calls"
    )
    parser.add_argument("--force", action="store_true", help="re-embed every chunk")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="allow pruning the whole index when no content is found (guards against a wrong path)",
    )
    parser.add_argument("--content-dir", type=Path, default=REPO_ROOT / "content")
    parser.add_argument("--knowledge-dir", type=Path, default=REPO_ROOT / "knowledge")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--overlap-tokens", type=int, default=DEFAULT_OVERLAP_TOKENS)
    return parser.parse_args(argv)


def build_chunks(args: argparse.Namespace) -> list[Chunk]:
    docs = load_all(args.content_dir, args.knowledge_dir)
    chunks: list[Chunk] = []
    for doc in docs:
        chunks.extend(
            chunk_document(doc, max_tokens=args.max_tokens, overlap_tokens=args.overlap_tokens)
        )
    return chunks


def print_report(chunks: list[Chunk]) -> None:
    per_source = Counter(c.source_id for c in chunks)
    tokens = Counter()
    for c in chunks:
        tokens[c.source_id] += estimate_tokens(c.content)
    by_type = Counter(c.source_type for c in chunks)
    width = max((len(s) for s in per_source), default=10)
    print(f"{'source_id':<{width}}  chunks  ~tokens")
    for source_id in sorted(per_source):
        print(f"{source_id:<{width}}  {per_source[source_id]:>6}  {tokens[source_id]:>7}")
    print(
        f"\n{len(per_source)} sources, {len(chunks)} chunks, ~{sum(tokens.values())} tokens"
        + (f"  ({', '.join(f'{t}: {n}' for t, n in sorted(by_type.items()))})" if by_type else "")
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging("WARNING" if args.dry_run else None)
    chunks = build_chunks(args)
    print_report(chunks)
    if args.dry_run:
        print("\n--dry-run: nothing embedded or written.")
        return 0

    # Imported here so --dry-run works without credentials or network.
    from core.supabase import get_supabase
    from rag.embedder import embed_texts
    from rag.store import delete_ids, fetch_index, patch_rows, upsert_rows

    settings = get_settings()
    client = get_supabase()
    existing = fetch_index(client)
    if not chunks and existing and not args.allow_empty:
        print(
            f"\nRefusing to delete all {len(existing)} indexed chunks: no content found under "
            f"{args.content_dir} or {args.knowledge_dir}. Pass --allow-empty if that's intended.",
            file=sys.stderr,
        )
        return 2

    plan = plan_sync(
        chunks,
        existing,
        embed_model=settings.gemini_embed_model,
        embed_dim=settings.embed_dim,
        force=args.force,
    )
    print(f"\nplan: {plan.summary()}")
    if plan.is_noop:
        print("Index is up to date.")
        return 0

    if plan.to_embed:
        vectors = embed_texts([row["content"] for row in plan.to_embed])
        rows = [{**row, "embedding": vec} for row, vec in zip(plan.to_embed, vectors, strict=True)]
        upsert_rows(client, rows)
    patch_rows(client, plan.to_patch)
    delete_ids(client, plan.to_delete)  # after upserts, so a failed embed never loses rows
    log.info("ingest complete", extra=plan.summary())
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
