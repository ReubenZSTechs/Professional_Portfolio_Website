"""Per-visitor rate limiting backed by Supabase (serverless instances share no memory).

IPs are never stored: they are hashed with IP_HASH_SALT first. If Supabase isn't configured
(e.g. a quick local run without .env), limits are skipped with a warning instead of failing.
"""

from __future__ import annotations

import asyncio
import hashlib

from fastapi import HTTPException, Request, status

from core.config import MissingSettingError, get_settings
from core.logging import get_logger
from core.supabase import get_supabase

log = get_logger(__name__)


def client_ip(request: Request) -> str:
    # Vercel puts the real client IP first in x-forwarded-for.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


def hash_ip(ip: str) -> str:
    salt = get_settings().ip_hash_salt.get_secret_value()
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]


def _check(key: str, window_seconds: int, max_requests: int) -> bool:
    response = (
        get_supabase()
        .rpc(
            "check_rate_limit",
            {"p_key": key, "p_window_seconds": window_seconds, "p_max": max_requests},
        )
        .execute()
    )
    return bool(response.data)


async def enforce_rate_limit(
    request: Request, bucket: str, *, max_requests: int, window_seconds: int
) -> str:
    """Raise 429 when this visitor exceeded the bucket's limit. Returns the IP hash."""
    ip_hash = hash_ip(client_ip(request))
    try:
        allowed = await asyncio.to_thread(
            _check, f"{bucket}:{ip_hash}", window_seconds, max_requests
        )
    except MissingSettingError:
        log.warning("rate_limit_skipped", extra={"reason": "supabase not configured"})
        return ip_hash
    except Exception as exc:  # don't take the site down because the limiter is unreachable
        log.error("rate_limit_error", extra={"error": str(exc)})
        return ip_hash
    if not allowed:
        minutes = max(1, window_seconds // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You've reached the limit for now. Try again in about {minutes} minutes.",
            headers={"Retry-After": str(window_seconds)},
        )
    return ip_hash
