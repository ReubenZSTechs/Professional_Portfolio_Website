"""HMAC signatures for chat session tokens and assistant answers.

- Session token: proves the browser passed a Turnstile check recently, so it isn't challenged
  on every message. Format `v1.<expiry>.<sig>`, bound to the visitor's IP hash.
- Answer signature: the server signs every answer it streams. The browser sends answers back
  as history; unsigned or tampered "assistant" turns are dropped, so an attacker can't forge
  earlier replies like "Sure, I'll ignore my rules" (history-forgery prompt injection).

Uses CHAT_SIGNING_SECRET. When it's missing locally a fixed development key is used; when
deployed a missing key is a configuration error (fail closed).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

from core.config import MissingSettingError, Settings, get_settings

DEV_KEY = b"dev-only-chat-signing-key-not-for-production"


def _key(settings: Settings) -> bytes:
    if settings.chat_signing_secret and settings.chat_signing_secret.get_secret_value():
        return settings.chat_signing_secret.get_secret_value().encode()
    if settings.is_deployed:
        raise MissingSettingError("CHAT_SIGNING_SECRET is not set.")
    return DEV_KEY


def _sign(message: str, settings: Settings) -> str:
    digest = hmac.new(_key(settings), message.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_session(
    ip_hash: str, *, now: float | None = None, settings: Settings | None = None
) -> str:
    s = settings or get_settings()
    expiry = int((now if now is not None else time.time()) + s.chat_session_ttl_seconds)
    return f"v1.{expiry}.{_sign(f'session|{ip_hash}|{expiry}', s)}"


def verify_session(
    token: str | None, ip_hash: str, *, now: float | None = None, settings: Settings | None = None
) -> bool:
    if not token:
        return False
    s = settings or get_settings()
    try:
        version, expiry_text, signature = token.split(".", 2)
        expiry = int(expiry_text)
    except ValueError:
        return False
    if version != "v1" or expiry < (now if now is not None else time.time()):
        return False
    expected = _sign(f"session|{ip_hash}|{expiry}", s)
    return hmac.compare_digest(signature, expected)


def sign_answer(text: str, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    return _sign(f"answer|{hashlib.sha256(text.encode()).hexdigest()}", s)


def verify_answer(text: str, signature: str | None, settings: Settings | None = None) -> bool:
    if not signature:
        return False
    return hmac.compare_digest(signature, sign_answer(text, settings))
