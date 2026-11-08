"""Application settings, loaded from environment variables (and the repo-root `.env` locally).

Every tunable lives here so swapping a Gemini model or changing a RAG threshold is an env-var
change in Vercel, not a code change. Names map 1:1 to env vars, case-insensitively:
`gemini_chat_model` <- `GEMINI_CHAT_MODEL`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/src/core/config.py -> repo root is three levels above `src`.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Gemini embeddings are natively 3072-d and already unit-length at that size; smaller
# output_dimensionality values are truncations that must be re-normalised client-side.
GEMINI_NATIVE_EMBED_DIM = 3072


class MissingSettingError(RuntimeError):
    """Raised when code needs a secret/URL that isn't configured."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Secrets / endpoints (optional at import time; use `require()` where needed) ---
    gemini_api_key: SecretStr | None = None
    supabase_url: str | None = None
    supabase_service_role_key: SecretStr | None = None
    resend_api_key: SecretStr | None = None
    contact_to_email: str | None = None
    contact_from_email: str = "Portfolio <onboarding@resend.dev>"

    # --- Gemini models (ids from https://ai.google.dev/gemini-api/docs/models, Nov 2026) ---
    gemini_chat_model: str = "gemini-3.6-flash"
    gemini_rewrite_model: str = "gemini-3.5-flash-lite"
    gemini_embed_model: str = "gemini-embedding-001"
    # Tried in order when the primary model is overloaded (503), rate-limited (429), retired
    # (404) or times out. Env vars take a comma-separated list, e.g.
    #   GEMINI_CHAT_FALLBACK_MODELS=gemini-3.5-flash,gemini-3.8-flash
    # Embeddings have no fallback on purpose: vectors from another model wouldn't match the index.
    gemini_chat_fallback_models: Annotated[list[str], NoDecode] = [
        "gemini-3.5-flash",
        "gemini-3.8-flash",
    ]
    gemini_rewrite_fallback_models: Annotated[list[str], NoDecode] = [
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
    ]
    # How hard the answering model "thinks" before writing (Gemini 3: "minimal", "low", "medium",
    # "high"; empty = model default). Thinking tokens count against max_output_tokens, and the
    # answer only summarises retrieved passages, so "low" keeps answers fast and never truncated.
    gemini_chat_thinking_level: str | None = "low"
    answer_max_output_tokens: int = Field(default=2048, ge=256)
    # Per-request network timeout. Kept short so a stuck model is skipped quickly.
    gemini_timeout_seconds: float = Field(default=25.0, gt=0)

    # --- Embeddings ---
    # Must equal the vector(N) size in supabase/migrations; changing it needs a new migration
    # plus a full re-ingest (the content hash includes the dim, so ingest re-embeds everything).
    embed_dim: int = Field(default=768, ge=128, le=GEMINI_NATIVE_EMBED_DIM)
    embed_batch_size: int = Field(default=100, ge=1, le=250)

    # --- Retrieval ---
    rag_top_k: int = Field(default=6, ge=1, le=50)
    rag_min_similarity: float = Field(default=0.5, ge=-1.0, le=1.0)

    # --- Chat guardrails ---
    max_question_chars: int = Field(default=500, ge=1)
    max_history_turns: int = Field(default=10, ge=0)

    # --- Rate limits (fixed windows, enforced by the check_rate_limit RPC) ---
    rate_limit_chat_max: int = Field(default=20, ge=1)
    rate_limit_chat_window_seconds: int = Field(default=600, ge=1)
    rate_limit_contact_max: int = Field(default=3, ge=1)
    rate_limit_contact_window_seconds: int = Field(default=3600, ge=1)
    # Salt for hashing client IPs before they touch the database.
    ip_hash_salt: SecretStr = SecretStr("change-me")

    # --- Misc ---
    log_level: str = "INFO"
    environment: str = "development"

    @field_validator("gemini_chat_fallback_models", "gemini_rewrite_fallback_models", mode="before")
    @classmethod
    def split_model_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [m.strip() for m in value.split(",") if m.strip()]
        return value

    def require(self, name: str) -> str:
        """Return a configured value as a plain string, or raise a clear error."""
        value = getattr(self, name)
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not value:
            raise MissingSettingError(
                f"{name.upper()} is not set. Add it to .env locally or to the Vercel project's "
                "environment variables."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings singleton. Tests call `get_settings.cache_clear()` to reset."""
    return Settings()
