"""Live evaluation against the real models and index. Costs a few cents per run.

    cd backend && RUN_EVALS=1 ../.venv/bin/python -m pytest tests/evals -v

Skipped unless RUN_EVALS=1 and the Gemini/Supabase settings are present (.env is used).
Requires `python backend/scripts/ingest.py` to have been run first.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from agent.graph.builder import build_graph
from agent.graph.state import Turn
from core.config import Settings, get_settings

CASES = yaml.safe_load((Path(__file__).parent / "golden.yaml").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(os.getenv("RUN_EVALS") != "1", reason="set RUN_EVALS=1 to run")


@pytest.fixture(autouse=True)
def real_settings(monkeypatch):
    # Undo the unit-test isolation in conftest.py: evals need the real .env.
    from core.config import REPO_ROOT

    monkeypatch.setitem(Settings.model_config, "env_file", REPO_ROOT / ".env")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize("case", CASES, ids=[c["question"][:40] for c in CASES])
async def test_golden(case):
    state = {
        "question": case["question"],
        "history": [Turn(**t) for t in case.get("history", [])],
    }
    events = [e async for e in build_graph().astream(state, stream_mode="custom")]
    answer = "".join(e["data"]["text"] for e in events if e["event"] == "token").strip()
    sources = next((e["data"]["sources"] for e in events if e["event"] == "sources"), [])
    titles = [s["title"] for s in sources]

    assert answer, "empty answer"
    if case.get("expect_no_sources"):
        assert not sources, f"should not cite sources, cited {titles}"
    for needle in case.get("expect_sources", []):
        assert any(needle.lower() in t.lower() for t in titles), (
            f"expected a source matching {needle!r}; cited {titles}\nanswer: {answer}"
        )
