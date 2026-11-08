"""POST /api/py/chat: streams the agent's answer as Server-Sent Events.

Event order: session? → status* → token* (or retract) → sources? → done   (or error → done)
Wire format documented in docs/api.md; the browser client is src/lib/api.ts.

Security layers, in order (docs/security.md):
  1. SecurityMiddleware   JSON only, size limit, same-site Origin (core/security.py)
  2. rate limits          burst / per visitor / site-wide daily cap (core/rate_limit.py)
  3. human check          Turnstile token, then a signed 30-minute chat session
  4. history integrity    unsigned or tampered assistant turns are dropped
  5. input guard          deterministic injection screening; blocked → refusal, no LLM call
  6. the graph            spotlighted prompts, LLM `unsafe` intent, streaming output guard
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from agent.graph.builder import get_graph
from agent.graph.state import ChatState, Turn
from agent.guardrails import REFUSAL
from agent.guardrails.history import verify_history
from agent.guardrails.input_guard import scan_conversation
from agent.guardrails.normalize import normalize_text
from agent.guardrails.spotlight import new_nonce
from core.config import MissingSettingError, get_settings
from core.logging import get_logger
from core.rate_limit import client_ip, enforce_chat_limits
from core.security import log_security_event
from core.signing import issue_session, sign_answer, verify_session
from core.turnstile import turnstile_enabled, verify_turnstile
from llm.gemini import ModelUnavailableError

log = get_logger(__name__)
router = APIRouter()

MAX_HISTORY_ITEMS = 20


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[Turn] = Field(default_factory=list, max_length=MAX_HISTORY_ITEMS)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    @field_validator("message")
    @classmethod
    def check_length(cls, value: str) -> str:
        value = normalize_text(value)
        limit = get_settings().max_question_chars
        if not value:
            raise ValueError("Please type a question.")
        if len(value) > limit:
            raise ValueError(f"Please keep questions under {limit} characters.")
        return value


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _expected_hosts(request: Request) -> set[str]:
    hosts = {urlsplit(o).netloc for o in get_settings().trusted_origins}
    for header in ("x-forwarded-host", "host"):
        if value := request.headers.get(header):
            hosts.add(value.split(",")[0].strip())
    return {h.split(":")[0].lower() for h in hosts if h}


async def ensure_human(
    request: Request, body: ChatRequest, ip_hash: str, session_token: str | None
) -> str | None:
    """Returns a new session token when a Turnstile check was just passed, None when the
    existing session is still valid (or bot checks are off locally). Raises 403 otherwise."""
    try:
        enabled = turnstile_enabled()
    except MissingSettingError as exc:
        log.error("turnstile_misconfigured", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant isn't available right now.",
            headers={"X-Error-Code": "config"},
        ) from exc
    if not enabled or verify_session(session_token, ip_hash):
        return None
    ok = await verify_turnstile(
        body.turnstile_token,
        action="chat",
        remote_ip=client_ip(request),
        expected_hosts=_expected_hosts(request),
    )
    if not ok:
        log_security_event("bot_check_failed", ip_hash=ip_hash, path="/chat")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete the quick verification and try again.",
            headers={"X-Error-Code": "verification"},
        )
    return issue_session(ip_hash)


async def refuse(session: str | None) -> AsyncIterator[str]:
    if session:
        yield sse("session", {"token": session})
    yield sse("token", {"text": REFUSAL})
    yield sse("done", {"sig": sign_answer(REFUSAL)})


async def run_graph(state: ChatState, session: str | None) -> AsyncIterator[str]:
    if session:
        yield sse("session", {"token": session})
    shown: list[str] = []  # what the visitor actually sees, for the answer signature
    try:
        async for item in get_graph().astream(state, stream_mode="custom"):
            if item["event"] == "token":
                shown.append(item["data"]["text"])
            elif item["event"] == "retract":
                shown = [item["data"]["text"]]
            yield sse(item["event"], item["data"])
    except ModelUnavailableError as exc:
        log.error("chat_models_unavailable", extra={"error": str(exc)})
        yield sse(
            "error",
            {
                "message": "The AI model is very busy right now. Please try again in a minute.",
                "code": "busy",
            },
        )
        shown = []
    except MissingSettingError as exc:
        log.error("chat_misconfigured", extra={"error": str(exc)})
        yield sse("error", {"message": "The assistant isn't configured yet.", "code": "config"})
        shown = []
    except Exception as exc:
        log.exception("chat_failed", extra={"error": str(exc)})
        yield sse(
            "error",
            {
                "message": "Sorry, something went wrong while answering. Please try again.",
                "code": "internal",
            },
        )
        shown = []
    answer = "".join(shown)
    yield sse("done", {"sig": sign_answer(answer)} if answer else {})


@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    x_chat_session: str | None = Header(default=None, max_length=256),
) -> StreamingResponse:
    ip_hash = await enforce_chat_limits(request)
    session = await ensure_human(request, body, ip_hash, x_chat_session)

    history, forged = verify_history(body.history)
    if forged:
        log_security_event("history_forgery", ip_hash=ip_hash, dropped=forged)

    user_turns = [t.content for t in history if t.role == "user"]
    guard = scan_conversation(body.message, user_turns)
    headers = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"}
    if guard.blocked:
        log_security_event(
            "prompt_injection_blocked",
            ip_hash=ip_hash,
            rules=guard.rules,
            text=body.message,
            score=guard.score,
        )
        return StreamingResponse(refuse(session), media_type="text/event-stream", headers=headers)
    if guard.suspicious:
        log_security_event(
            "prompt_injection_suspected", ip_hash=ip_hash, rules=guard.rules, score=guard.score
        )

    state: ChatState = {
        "question": body.message,
        "history": history,
        "suspicious": guard.suspicious,
        "nonce": new_nonce(),
        "ip_hash": ip_hash,
    }
    return StreamingResponse(
        run_graph(state, session), media_type="text/event-stream", headers=headers
    )
