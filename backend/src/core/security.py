"""HTTP-level hardening for the API (see docs/security.md).

`SecurityMiddleware` is a pure ASGI middleware (it doesn't buffer streamed responses) that:
  - adds security headers to every API response (incl. Cache-Control: no-store),
  - rejects POSTs that aren't JSON (415), are too large (413) or come from another site (403).

`log_security_event` writes one structured line per blocked attack, never raw IPs or full
prompts, so Vercel logs can be filtered by `security_event`.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.config import Settings, get_settings
from core.logging import get_logger

log = get_logger("security")

API_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
}


def excerpt_hash(text: str) -> str:
    """Stable short fingerprint of attacker input, so repeated attacks can be correlated in
    logs without storing the (possibly sensitive) text itself."""
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]


def log_security_event(
    event: str,
    *,
    ip_hash: str | None = None,
    rules: Iterable[str] = (),
    text: str | None = None,
    **extra: object,
) -> None:
    log.warning(
        "security_event",
        extra={
            "security_event": event,
            "ip_hash": ip_hash,
            "rules": sorted(set(rules)),
            "excerpt_hash": excerpt_hash(text) if text else None,
            **extra,
        },
    )


def _host(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(",")[0].strip().lower()


def origin_allowed(headers: Headers, settings: Settings) -> bool:
    """Browsers always send Origin on cross-origin and same-origin fetch POSTs.

    Allowed: same host as the request, configured/Vercel origins, or the preview-URL regex.
    Missing Origin (curl, scripts): allowed only in local development."""
    origin = headers.get("origin")
    if origin is None or origin == "null":
        if headers.get("sec-fetch-site") == "same-origin":
            return True
        return not settings.is_deployed
    origin = origin.rstrip("/").lower()
    request_host = _host(headers.get("x-forwarded-host")) or _host(headers.get("host"))
    if request_host and urlsplit(origin).netloc == request_host:
        return True
    if origin in {o.lower() for o in settings.trusted_origins}:
        return True
    return bool(
        settings.allowed_origin_regex and re.fullmatch(settings.allowed_origin_regex, origin)
    )


async def _reject(send: Send, status: int, detail: str, code: str) -> None:
    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"x-error-code", code.encode())]
    headers += [(k.lower().encode(), v.encode()) for k, v in API_SECURITY_HEADERS.items()]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for key, value in API_SECURITY_HEADERS.items():
                    headers.setdefault(key, value)
            await send(message)

        if scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}:
            settings = get_settings()
            headers = Headers(scope=scope)

            content_type = headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type != "application/json":
                await _reject(send, 415, "Content-Type must be application/json.", "content_type")
                return

            if not origin_allowed(headers, settings):
                log_security_event(
                    "origin_rejected", origin=headers.get("origin"), path=scope.get("path")
                )
                await _reject(send, 403, "Requests from this origin are not allowed.", "origin")
                return

            limit = settings.max_body_bytes
            declared = headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > limit:
                await _reject(send, 413, "Request is too large.", "too_large")
                return

            # Read the (small) body up front, enforcing the limit even without Content-Length,
            # then replay it to the app.
            chunks: list[bytes] = []
            size = 0
            more = True
            while more:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > limit:
                    await _reject(send, 413, "Request is too large.", "too_large")
                    return
                chunks.append(chunk)
                more = message.get("more_body", False)
            body = b"".join(chunks)
            replayed = False

            async def replay() -> Message:
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, replay, send_with_headers)
            return

        await self.app(scope, receive, send_with_headers)
