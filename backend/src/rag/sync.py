"""Diff freshly chunked content against what's already in public.documents.

Pure functions (no I/O) so the hash-skip logic is unit-testable; ingest.py does the I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rag.models import Chunk

# Non-embedding columns that can change without the text changing (e.g. a frontmatter flag).
_PATCHABLE = ("source_type", "title", "url", "section", "metadata")
# Columns ingest reads back to plan a sync. Embeddings are never fetched (too large).
INDEX_COLUMNS = "id,source_id,chunk_index,content_hash," + ",".join(_PATCHABLE)


@dataclass
class SyncPlan:
    to_embed: list[dict[str, Any]] = field(default_factory=list)  # new or changed text
    to_patch: list[tuple[str, dict[str, Any]]] = field(default_factory=list)  # (id, fields)
    to_delete: list[str] = field(default_factory=list)  # ids of stale chunks
    unchanged: int = 0

    @property
    def is_noop(self) -> bool:
        return not (self.to_embed or self.to_patch or self.to_delete)

    def summary(self) -> dict[str, int]:
        return {
            "embed": len(self.to_embed),
            "patch": len(self.to_patch),
            "delete": len(self.to_delete),
            "unchanged": self.unchanged,
        }


def plan_sync(
    chunks: list[Chunk],
    existing: list[dict[str, Any]],
    *,
    embed_model: str,
    embed_dim: int,
    force: bool = False,
) -> SyncPlan:
    """Decide what to embed, patch and delete.

    - A chunk is keyed by (source_id, chunk_index), matching the table's unique constraint.
    - Same key + same content_hash -> no re-embedding; metadata/title/url differences are
      patched in place.
    - Existing keys that no longer exist (chunk dropped, or the whole source deleted) are removed.
    - `force` re-embeds everything.
    """
    by_key = {(row["source_id"], row["chunk_index"]): row for row in existing}
    plan = SyncPlan()
    seen: set[tuple[str, int]] = set()

    for chunk in chunks:
        key = (chunk.source_id, chunk.chunk_index)
        if key in seen:
            raise ValueError(f"duplicate chunk key {key}; source_ids must be unique")
        seen.add(key)

        row = chunk.to_row(embed_model, embed_dim)
        old = by_key.get(key)
        if force or old is None or old.get("content_hash") != row["content_hash"]:
            plan.to_embed.append(row)
            continue
        changed = {col: row[col] for col in _PATCHABLE if old.get(col) != row[col]}
        if changed:
            plan.to_patch.append((old["id"], changed))
        else:
            plan.unchanged += 1

    plan.to_delete = [row["id"] for key, row in by_key.items() if key not in seen]
    return plan
