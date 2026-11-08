"""Vector search over public.documents via the match_documents RPC."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any

from supabase import Client

from core.config import get_settings
from core.logging import get_logger
from core.supabase import get_supabase
from llm.gemini import GeminiClient
from rag.embedder import embed_query
from rag.models import RetrievedChunk

log = get_logger(__name__)


def search_by_embedding(
    embedding: Sequence[float],
    *,
    k: int,
    min_similarity: float,
    filter: dict[str, Any] | None = None,
    supabase: Client | None = None,
) -> list[RetrievedChunk]:
    client = supabase or get_supabase()
    response = client.rpc(
        "match_documents",
        {
            "query_embedding": list(embedding),
            "match_count": k,
            "min_similarity": min_similarity,
            "filter": filter or {},
        },
    ).execute()
    return [RetrievedChunk.model_validate(row) for row in response.data or []]


def retrieve(
    query: str,
    k: int | None = None,
    min_similarity: float | None = None,
    filter: dict[str, Any] | None = None,
    *,
    gemini: GeminiClient | None = None,
    supabase: Client | None = None,
) -> list[RetrievedChunk]:
    """Embed `query` (RETRIEVAL_QUERY) and return up to k chunks above min_similarity,
    best first. `filter` is jsonb containment over metadata + source_type/source_id, e.g.
    {"source_type": "project"}."""
    query = query.strip()
    if not query:
        return []
    settings = get_settings()
    k = k or settings.rag_top_k
    min_similarity = settings.rag_min_similarity if min_similarity is None else min_similarity

    started = time.perf_counter()
    embedding = embed_query(query, gemini=gemini)
    chunks = search_by_embedding(
        embedding, k=k, min_similarity=min_similarity, filter=filter, supabase=supabase
    )
    log.info(
        "retrieved",
        extra={
            "k": k,
            "min_similarity": min_similarity,
            "filter": filter or {},
            "hits": len(chunks),
            "top_similarity": round(chunks[0].similarity, 4) if chunks else None,
            "ms": round((time.perf_counter() - started) * 1000),
        },
    )
    return chunks
