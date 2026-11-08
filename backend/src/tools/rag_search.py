"""The retrieval tool the LangGraph `retrieve` node calls.

Returns the chunks plus two ready-made views of them:
  - `context`: numbered blocks for the answering prompt; the model cites them as [n].
  - `sources`: one entry per number for the UI's "Sources for this answer" panel (SSE event).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from rag.models import RetrievedChunk
from rag.retriever import retrieve

SNIPPET_CHARS = 220


class Source(BaseModel):
    n: int  # citation number used in the answer, 1-based
    type: str
    title: str
    section: str | None = None
    snippet: str
    url: str | None = None
    similarity: float


class RagSearchResult(BaseModel):
    query: str
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    context: str = ""
    sources: list[Source] = Field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.chunks


def _snippet(text: str, limit: int = SNIPPET_CHARS) -> str:
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    cut = flat[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for n, chunk in enumerate(chunks, start=1):
        where = f"{chunk.title} — {chunk.section}" if chunk.section else chunk.title
        url = f" ({chunk.url})" if chunk.url else ""
        blocks.append(f"[{n}] {where}{url}\n{chunk.body}")
    return "\n\n---\n\n".join(blocks)


def to_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    return [
        Source(
            n=n,
            type=chunk.source_type,
            title=chunk.title,
            section=chunk.section,
            snippet=_snippet(chunk.body),
            url=chunk.url,
            similarity=round(chunk.similarity, 4),
        )
        for n, chunk in enumerate(chunks, start=1)
    ]


def rag_search(
    query: str,
    *,
    k: int | None = None,
    min_similarity: float | None = None,
    filters: dict[str, Any] | None = None,
    **retrieve_kwargs: Any,
) -> RagSearchResult:
    chunks = retrieve(query, k=k, min_similarity=min_similarity, filter=filters, **retrieve_kwargs)
    return RagSearchResult(
        query=query, chunks=chunks, context=format_context(chunks), sources=to_sources(chunks)
    )
