from __future__ import annotations

import pytest

from rag.models import Chunk
from rag.sync import plan_sync

MODEL, DIM = "gemini-embedding-001", 768


def chunk(source_id: str, idx: int, content: str, **kw) -> Chunk:
    return Chunk(
        source_type=kw.pop("source_type", "project"),
        source_id=source_id,
        title=kw.pop("title", "T"),
        url=kw.pop("url", None),
        section=kw.pop("section", None),
        chunk_index=idx,
        content=content,
        metadata=kw.pop("metadata", {}),
    )


def stored(c: Chunk, row_id: str, model: str = MODEL, dim: int = DIM) -> dict:
    """What fetch_index would return for a chunk ingested earlier."""
    return {"id": row_id, **c.to_row(model, dim)}


def test_unchanged_chunks_are_skipped():
    chunks = [chunk("project:a", 0, "alpha"), chunk("project:a", 1, "beta")]
    existing = [stored(c, f"id{i}") for i, c in enumerate(chunks)]
    plan = plan_sync(chunks, existing, embed_model=MODEL, embed_dim=DIM)
    assert plan.is_noop
    assert plan.unchanged == 2


def test_changed_text_is_re_embedded():
    old = chunk("project:a", 0, "alpha")
    new = chunk("project:a", 0, "alpha, edited")
    plan = plan_sync([new], [stored(old, "id0")], embed_model=MODEL, embed_dim=DIM)
    assert [r["content"] for r in plan.to_embed] == ["alpha, edited"]
    assert plan.to_delete == [] and plan.to_patch == []


def test_new_chunk_is_embedded():
    plan = plan_sync([chunk("project:a", 0, "alpha")], [], embed_model=MODEL, embed_dim=DIM)
    assert len(plan.to_embed) == 1
    assert plan.to_embed[0]["content_hash"] == chunk("project:a", 0, "alpha").hash(MODEL, DIM)


def test_metadata_only_change_is_patched_not_embedded():
    old = chunk("project:a", 0, "alpha", metadata={"featured": False})
    new = chunk("project:a", 0, "alpha", metadata={"featured": True}, url="/projects/a")
    plan = plan_sync([new], [stored(old, "id0")], embed_model=MODEL, embed_dim=DIM)
    assert plan.to_embed == []
    assert plan.to_patch == [("id0", {"url": "/projects/a", "metadata": {"featured": True}})]


def test_stale_chunks_and_removed_sources_are_deleted():
    kept = chunk("project:a", 0, "alpha")
    existing = [
        stored(kept, "keep"),
        stored(chunk("project:a", 1, "old second chunk"), "shrunk"),
        stored(chunk("project:gone", 0, "deleted project"), "gone"),
    ]
    plan = plan_sync([kept], existing, embed_model=MODEL, embed_dim=DIM)
    assert sorted(plan.to_delete) == ["gone", "shrunk"]
    assert plan.unchanged == 1


def test_switching_embedding_model_re_embeds_everything():
    chunks = [chunk("project:a", 0, "alpha"), chunk("project:b", 0, "beta")]
    existing = [stored(c, f"id{i}", model="old-model") for i, c in enumerate(chunks)]
    plan = plan_sync(chunks, existing, embed_model=MODEL, embed_dim=DIM)
    assert len(plan.to_embed) == 2


def test_force_re_embeds_unchanged():
    c = chunk("project:a", 0, "alpha")
    plan = plan_sync([c], [stored(c, "id0")], embed_model=MODEL, embed_dim=DIM, force=True)
    assert len(plan.to_embed) == 1


def test_duplicate_keys_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        plan_sync(
            [chunk("project:a", 0, "x"), chunk("project:a", 0, "y")],
            [],
            embed_model=MODEL,
            embed_dim=DIM,
        )
