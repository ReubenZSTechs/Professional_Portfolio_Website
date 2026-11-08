"""Contact-form notification email via Resend."""

from __future__ import annotations

import html

import resend

from core.config import get_settings


def send_contact_email(name: str, email: str, message: str) -> None:
    settings = get_settings()
    resend.api_key = settings.require("resend_api_key")
    body = html.escape(message).replace("\n", "<br>")
    resend.Emails.send(
        {
            "from": settings.contact_from_email,
            "to": [settings.require("contact_to_email")],
            "reply_to": email,  # hitting "Reply" answers the visitor directly
            "subject": f"Portfolio message from {name}",
            "html": (
                f"<p><strong>{html.escape(name)}</strong> ({html.escape(email)}) wrote:</p>"
                f"<blockquote>{body}</blockquote>"
                "<p style='color:#64748b'>Sent from the contact form on your portfolio.</p>"
            ),
            "text": f"{name} <{email}> wrote:\n\n{message}",
        }
    )
