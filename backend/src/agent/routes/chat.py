"""POST /api/py/chat: streams the agent's answer as Server-Sent Events.

Event order: status* → token* → sources? → done   (or error → done)
Wire format documented in docs/api.md; the browser client is src/lib/api.ts.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from agent.graph.builder import get_graph
from agent.graph.state import ChatState, Turn
from core.config import MissingSettingError, get_settings
from core.logging import get_logger
from core.rate_limit import enforce_rate_limit
from llm.gemini import ModelUnavailableError

log = get_logger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[Turn] = Field(default_factory=list, max_length=60)

    @field_validator("message")
    @classmethod
    def check_length(cls, value: str) -> str:
        value = value.strip()
        limit = get_settings().max_question_chars
        if not value:
            raise ValueError("Please type a question.")
        if len(value) > limit:
            raise ValueError(f"Please keep questions under {limit} characters.")
        return value


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_graph(state: ChatState) -> AsyncIterator[str]:
    try:
        async for item in get_graph().astream(state, stream_mode="custom"):
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
    except MissingSettingError as exc:
        log.error("chat_misconfigured", extra={"error": str(exc)})
        yield sse("error", {"message": "The assistant isn't configured yet.", "code": "config"})
    except Exception as exc:
        log.exception("chat_failed", extra={"error": str(exc)})
        yield sse(
            "error",
            {
                "message": "Sorry, something went wrong while answering. Please try again.",
                "code": "internal",
            },
        )
    yield sse("done", {})


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> StreamingResponse:
    settings = get_settings()
    await enforce_rate_limit(
        request,
        "chat",
        max_requests=settings.rate_limit_chat_max,
        window_seconds=settings.rate_limit_chat_window_seconds,
    )
    state: ChatState = {"question": body.message, "history": body.history}
    return StreamingResponse(
        run_graph(state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
