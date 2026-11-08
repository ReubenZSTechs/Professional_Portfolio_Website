from __future__ import annotations

import sys
from pathlib import Path

import pytest

# pyproject's `pythonpath = ["src"]` covers pytest runs from backend/; this covers the rest.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch):
    """Never read the developer's real .env during unit tests."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
