"""Cloudflare Turnstile verification (invisible bot check for chat and contact).

The browser gets a one-time token from the Turnstile widget; the server confirms it with
Cloudflare's siteverify API, including that it was issued for the expected action and site.

Policy (docs/security.md):
  - Deployed (production/preview): TURNSTILE_SECRET_KEY is required; missing → fail closed.
  - Local development without a secret: verification is skipped so the site still runs.
    Cloudflare's always-pass test keys work locally too.
"""

from __future__ import annotations

import httpx

from core.config import MissingSettingError, Settings, get_settings
from core.logging import get_logger

log = get_logger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TEST_SECRET_PREFIX = "1x0000000000000000000000000000000"  # Cloudflare's published test secrets


def turnstile_enabled(settings: Settings | None = None) -> bool:
    s = settings or get_settings()
    configured = bool(s.turnstile_secret_key and s.turnstile_secret_key.get_secret_value())
    if not configured and s.is_deployed:
        raise MissingSettingError("TURNSTILE_SECRET_KEY is not set.")
    return configured


async def verify_turnstile(
    token: str | None,
    *,
    action: str,
    remote_ip: str | None = None,
    expected_hosts: set[str] | None = None,
    settings: Settings | None = None,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """True when Cloudflare confirms the token. Network errors count as failure (fail closed)."""
    s = settings or get_settings()
    if not token or len(token) > 2048:
        return False
    secret = s.require("turnstile_secret_key")
    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=5.0) as owned:
                response = await owned.post(SITEVERIFY_URL, data=data)
        else:
            response = await client.post(SITEVERIFY_URL, data=data)
        result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.error("turnstile_unreachable", extra={"error": str(exc)})
        return False

    if not result.get("success"):
        log.info("turnstile_failed", extra={"codes": result.get("error-codes")})
        return False
    is_test_secret = secret.startswith(TEST_SECRET_PREFIX)
    if not is_test_secret and result.get("action") and result.get("action") != action:
        log.info("turnstile_wrong_action", extra={"got": result.get("action"), "want": action})
        return False
    hostname = (result.get("hostname") or "").lower()
    if expected_hosts and not is_test_secret and hostname not in expected_hosts:
        log.info("turnstile_wrong_host", extra={"hostname": hostname})
        return False
    return True
