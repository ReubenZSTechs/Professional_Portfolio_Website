"""Rate limiting backed by Supabase (serverless instances share no memory).

Layers for the chat (cheapest check first):
  1. burst      5 questions / minute per visitor
  2. sustained  20 questions / 10 minutes per visitor
  3. global     500 questions / UTC day for the whole site (protects the Gemini bill)
The Vercel Firewall adds an edge layer in front of these (deploy/vercel-firewall/).

IPs are never stored: they are hashed with IP_HASH_SALT first.
If the limiter itself is unavailable: deployed → fail closed (503); local dev → allow.
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


def request_ip_hash(request: Request) -> str:
    return hash_ip(client_ip(request))


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


def _too_many(detail: str, retry_after: int, code: str = "rate_limited") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(retry_after), "X-Error-Code": code},
    )


async def _allowed(key: str, window_seconds: int, max_requests: int) -> bool:
    """One limiter check. Fails closed when deployed, open in local development."""
    try:
        return await asyncio.to_thread(_check, key, window_seconds, max_requests)
    except Exception as exc:  # MissingSettingError, network, database
        if get_settings().is_deployed:
            log.error("rate_limit_unavailable", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="This service is temporarily unavailable. Please try again shortly.",
                headers={"X-Error-Code": "unavailable"},
            ) from exc
        if not isinstance(exc, MissingSettingError):
            log.warning("rate_limit_error", extra={"error": str(exc)})
        return True


async def enforce_rate_limit(
    request: Request, bucket: str, *, max_requests: int, window_seconds: int
) -> str:
    """Raise 429 when this visitor exceeded the bucket's limit. Returns the IP hash."""
    ip_hash = request_ip_hash(request)
    if not await _allowed(f"{bucket}:{ip_hash}", window_seconds, max_requests):
        minutes = max(1, window_seconds // 60)
        raise _too_many(
            f"You've reached the limit for now. Try again in about {minutes} minutes.",
            window_seconds,
        )
    return ip_hash


async def enforce_chat_limits(request: Request) -> str:
    """Burst, per-visitor and site-wide daily limits for the chat. Returns the IP hash."""
    s = get_settings()
    ip_hash = request_ip_hash(request)
    if not await _allowed(
        f"chat-burst:{ip_hash}",
        s.rate_limit_chat_burst_window_seconds,
        s.rate_limit_chat_burst_max,
    ):
        raise _too_many(
            "You're asking very quickly. Please wait a minute.",
            s.rate_limit_chat_burst_window_seconds,
        )
    if not await _allowed(
        f"chat:{ip_hash}", s.rate_limit_chat_window_seconds, s.rate_limit_chat_max
    ):
        minutes = max(1, s.rate_limit_chat_window_seconds // 60)
        raise _too_many(
            f"You've reached the limit for now. Try again in about {minutes} minutes.",
            s.rate_limit_chat_window_seconds,
        )
    # An 86,400 s fixed window is aligned to the Unix epoch, so it resets at 00:00 UTC.
    if not await _allowed("chat:global", 86_400, s.rate_limit_chat_daily_global):
        log.warning("chat_daily_cap_reached", extra={"cap": s.rate_limit_chat_daily_global})
        raise _too_many(
            "The assistant has reached today's limit. Please email Reuben directly, "
            "or try again tomorrow.",
            3600,
            code="quota",
        )
    return ip_hash
