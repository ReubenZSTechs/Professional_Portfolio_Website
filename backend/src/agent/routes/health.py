"""GET /api/py/health: liveness check.

Deployed (production/preview): only {"status": "ok"}, so the endpoint reveals nothing about the
setup. Local development adds which integrations are configured (never their values) and the
model chains, to make setup problems obvious.
"""

from __future__ import annotations

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    s = get_settings()
    if s.is_deployed:
        return {"status": "ok"}
    return {
        "status": "ok",
        "environment": s.environment,
        "configured": {
            "gemini": s.gemini_api_key is not None,
            "supabase": bool(s.supabase_url and s.supabase_service_role_key),
            "resend": bool(s.resend_api_key and s.contact_to_email),
            "turnstile": bool(s.turnstile_secret_key),
            "chat_signing_secret": bool(s.chat_signing_secret),
        },
        "models": {
            "chat": s.gemini_chat_model,
            "rewrite": s.gemini_rewrite_model,
            "embed": s.gemini_embed_model,
            "chat_fallbacks": s.gemini_chat_fallback_models,
            "rewrite_fallbacks": s.gemini_rewrite_fallback_models,
        },
    }
