"""End-to-end run of backend/scripts/ingest.py with Supabase and Gemini faked."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

import core.supabase
import rag.embedder
import rag.store

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "ingest.py"


def load_script():
    spec = importlib.util.spec_from_file_location("ingest_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class FakeIndex:
    """In-memory stand-in for public.documents behind the rag.store functions."""

    def __init__(self):
        self.rows: dict[tuple[str, int], dict[str, Any]] = {}
        self.embedded = 0

    def install(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(core.supabase, "get_supabase", lambda: object())
        monkeypatch.setattr(
            rag.store, "fetch_index", lambda _c: [dict(r) for r in self.rows.values()]
        )
        monkeypatch.setattr(rag.store, "upsert_rows", lambda _c, rows: self._upsert(rows))
        monkeypatch.setattr(rag.store, "patch_rows", lambda _c, patches: self._patch(patches))
        monkeypatch.setattr(rag.store, "delete_ids", lambda _c, ids: self._delete(ids))
        monkeypatch.setattr(rag.embedder, "embed_texts", self._embed)

    def _embed(self, texts, **_):
        self.embedded += len(texts)
        return [[0.0] * 768 for _ in texts]

    def _upsert(self, rows):
        for row in rows:
            key = (row["source_id"], row["chunk_index"])
            old_id = self.rows.get(key, {}).get("id")
            self.rows[key] = {**row, "id": old_id or f"id-{len(self.rows)}-{row['source_id']}"}

    def _patch(self, patches):
        for row_id, fields in patches:
            for row in self.rows.values():
                if row["id"] == row_id:
                    row.update(fields)

    def _delete(self, ids):
        self.rows = {k: v for k, v in self.rows.items() if v["id"] not in set(ids)}


@pytest.fixture
def content(tmp_path: Path) -> Path:
    projects = tmp_path / "content" / "projects"
    projects.mkdir(parents=True)
    (projects / "a.mdx").write_text("---\ntitle: A\n---\n## One\n\nfirst\n\n## Two\n\nsecond\n")
    (projects / "b.mdx").write_text("---\ntitle: B\n---\n## Only\n\nbee\n")
    return tmp_path


def run(script, content: Path, *extra: str) -> int:
    return script.main(
        [
            "--content-dir",
            str(content / "content"),
            "--knowledge-dir",
            str(content / "knowledge"),
            *extra,
        ]
    )


def test_dry_run_makes_no_calls(content: Path, capsys, monkeypatch):
    monkeypatch.setattr(core.supabase, "get_supabase", lambda: pytest.fail("network in dry run"))
    assert run(load_script(), content, "--dry-run") == 0
    out = capsys.readouterr().out
    assert "2 sources, 3 chunks" in out


def test_incremental_ingest(content: Path, monkeypatch):
    index = FakeIndex()
    index.install(monkeypatch)
    script = load_script()

    assert run(script, content) == 0
    assert index.embedded == 3 and len(index.rows) == 3

    # second run: nothing changed -> nothing embedded
    assert run(script, content) == 0
    assert index.embedded == 3

    # edit one chunk, delete project b
    (content / "content" / "projects" / "a.mdx").write_text(
        "---\ntitle: A\n---\n## One\n\nfirst, edited\n\n## Two\n\nsecond\n"
    )
    (content / "content" / "projects" / "b.mdx").unlink()
    assert run(script, content) == 0
    assert index.embedded == 4
    assert sorted(index.rows) == [("project:a", 0), ("project:a", 1)]


def test_refuses_to_wipe_index_when_no_content(tmp_path: Path, monkeypatch):
    index = FakeIndex()
    index.rows[("project:a", 0)] = {"id": "x", "source_id": "project:a", "chunk_index": 0}
    index.install(monkeypatch)
    assert run(load_script(), tmp_path) == 2
    assert index.rows  # untouched
