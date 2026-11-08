from __future__ import annotations

import pytest

from core.config import MissingSettingError, Settings, get_settings

ENV_VARS = [
    "GEMINI_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GEMINI_CHAT_MODEL",
    "GEMINI_REWRITE_MODEL",
    "GEMINI_EMBED_MODEL",
    "EMBED_DIM",
    "RAG_TOP_K",
    "RAG_MIN_SIMILARITY",
    "MAX_QUESTION_CHARS",
    "MAX_HISTORY_TURNS",
]


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults(clean_env):
    s = Settings()
    assert s.gemini_chat_model == "gemini-3.6-flash"
    assert s.gemini_rewrite_model == "gemini-3.5-flash-lite"
    assert s.gemini_embed_model == "gemini-embedding-001"
    assert s.embed_dim == 768
    assert s.rag_top_k == 6
    assert 0 < s.rag_min_similarity < 1
    assert s.max_question_chars == 500
    assert s.max_history_turns == 10
    assert s.gemini_api_key is None


def test_env_overrides(clean_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GEMINI_CHAT_MODEL", "gemini-flash-latest")
    monkeypatch.setenv("RAG_TOP_K", "8")
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    s = Settings()
    assert s.gemini_chat_model == "gemini-flash-latest"
    assert s.rag_top_k == 8
    assert s.require("gemini_api_key") == "secret"
    assert "secret" not in repr(s)  # SecretStr keeps keys out of logs


def test_require_missing_raises_clear_error(clean_env):
    with pytest.raises(MissingSettingError, match="SUPABASE_URL"):
        Settings().require("supabase_url")


def test_embed_dim_bounds(clean_env, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("EMBED_DIM", "4096")
    with pytest.raises(ValueError):
        Settings()


def test_get_settings_is_cached(clean_env):
    assert get_settings() is get_settings()
