"""Pydantic models shared by ingestion and retrieval."""

from __future__ import annotations

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """One logical source before chunking: a project MDX file, a YAML entry, a knowledge note."""

    source_type: str  # project | experience | research | awards | skills | knowledge | ...
    source_id: str  # stable and unique across the corpus, e.g. "project:plantatio"
    title: str
    url: str | None = None
    text: str  # markdown / MDX body (frontmatter already removed)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A piece of a SourceDocument, ready to embed. `content` is exactly what gets embedded."""

    source_type: str
    source_id: str
    title: str
    url: str | None = None
    section: str | None = None
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    def hash(self, embed_model: str, embed_dim: int) -> str:
        return content_hash(self.content, embed_model, embed_dim)

    def to_row(self, embed_model: str, embed_dim: int) -> dict[str, Any]:
        """Column values for public.documents (without `embedding`)."""
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "content_hash": self.hash(embed_model, embed_dim),
            "metadata": self.metadata,
        }


class RetrievedChunk(BaseModel):
    """A row returned by the match_documents RPC."""

    id: str
    source_type: str
    source_id: str
    title: str
    url: str | None = None
    section: str | None = None
    chunk_index: int
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    similarity: float

    @property
    def body(self) -> str:
        """`content` without the "Title — Section" prefix the chunker adds for embedding."""
        head, sep, rest = self.content.partition("\n\n")
        return rest if sep and head.startswith(self.title) else self.content


def content_hash(content: str, embed_model: str, embed_dim: int) -> str:
    """Hash of everything that determines a chunk's embedding.

    The model id and dimension are part of the hash, so switching GEMINI_EMBED_MODEL or
    EMBED_DIM makes every chunk look changed and the next ingest re-embeds the whole corpus.
    """
    digest = hashlib.sha256()
    digest.update(f"{embed_model}\x00{embed_dim}\x00".encode())
    digest.update(content.encode())
    return digest.hexdigest()
