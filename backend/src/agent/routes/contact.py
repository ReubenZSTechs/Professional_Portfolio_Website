"""POST /api/py/contact: save a contact-form message and email it to Reuben.

The message is stored first, then emailed, so a Resend outage never loses a message.
"""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from core.config import MissingSettingError, get_settings
from core.logging import get_logger
from core.rate_limit import client_ip, enforce_rate_limit
from core.security import log_security_event
from core.supabase import get_supabase
from core.turnstile import turnstile_enabled, verify_turnstile
from services.email import send_contact_email

log = get_logger(__name__)
router = APIRouter()


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=10, max_length=5000)
    # Honeypot: hidden in the form, so only bots fill it in.
    company: str = Field(default="", max_length=200)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    @field_validator("name")
    @classmethod
    def single_line_name(cls, value: str) -> str:
        # The name goes into the email subject: no line breaks or control characters
        # (prevents header-injection style tricks and keeps subjects readable).
        value = re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()
        if not value:
            raise ValueError("Please enter your name.")
        return value


@router.post("/contact")
async def contact(body: ContactRequest, request: Request) -> dict[str, bool]:
    if body.company.strip():
        log.info("contact_honeypot")
        return {"ok": True}  # pretend success so bots don't retry

    settings = get_settings()
    try:
        bot_check = turnstile_enabled()
    except MissingSettingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sorry, the form isn't working right now. Please email me directly.",
        ) from exc
    ip_hash = await enforce_rate_limit(
        request,
        "contact",
        max_requests=settings.rate_limit_contact_max,
        window_seconds=settings.rate_limit_contact_window_seconds,
    )
    if bot_check and not await verify_turnstile(
        body.turnstile_token, action="contact", remote_ip=client_ip(request)
    ):
        log_security_event("bot_check_failed", ip_hash=ip_hash, path="/contact")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete the quick verification and try again.",
            headers={"X-Error-Code": "verification"},
        )

    row = {
        "name": body.name.strip(),
        "email": str(body.email),
        "message": body.message.strip(),
        "ip_hash": ip_hash,
    }

    try:
        await asyncio.to_thread(
            lambda: get_supabase().table("contact_messages").insert(row).execute()
        )
    except Exception as exc:
        log.error("contact_store_failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sorry, the form isn't working right now. Please email me directly.",
        ) from exc

    try:
        await asyncio.to_thread(send_contact_email, row["name"], row["email"], row["message"])
    except Exception as exc:  # stored already; the email is a convenience
        log.error("contact_email_failed", extra={"error": str(exc)})

    return {"ok": True}
