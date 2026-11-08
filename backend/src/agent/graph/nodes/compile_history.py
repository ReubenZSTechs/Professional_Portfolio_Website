"""Node 1: keep the conversation short enough to be cheap and focused.

The browser sends up to MAX_HISTORY_TURNS exchanges. The most recent turns are kept verbatim;
anything older is condensed into a short summary by the small rewrite model, so long chats
don't grow the prompt (and the token bill) without bound.
"""

from __future__ import annotations

import asyncio

from agent.graph.state import ChatState, Turn, format_turns, load_prompt
from core.config import get_settings
from core.logging import get_logger
from llm.gemini import GeminiError, get_gemini

log = get_logger(__name__)

KEEP_VERBATIM = 6  # messages (3 exchanges) kept word for word
MAX_TURN_CHARS = 2_000  # long pasted messages are clipped before they reach any prompt


def _clip(turn: Turn) -> Turn:
    if len(turn.content) <= MAX_TURN_CHARS:
        return turn
    return Turn(role=turn.role, content=turn.content[:MAX_TURN_CHARS] + " …")


async def compile_history(state: ChatState) -> ChatState:
    settings = get_settings()
    history = [_clip(t) for t in state.get("history", []) if t.content.strip()]
    history = history[-settings.max_history_turns * 2 :] if settings.max_history_turns else []

    if len(history) <= KEEP_VERBATIM:
        return {"recent": history, "summary": None}

    older, recent = history[:-KEEP_VERBATIM], history[-KEEP_VERBATIM:]
    try:
        summary = await asyncio.to_thread(
            get_gemini().generate,
            format_turns(older),
            model=settings.gemini_rewrite_model,
            system=load_prompt("summarize"),
            temperature=0.0,
            max_output_tokens=300,
        )
    except GeminiError as exc:
        # A missing summary only makes follow-ups slightly less precise; don't fail the chat.
        log.warning("history_summary_failed", extra={"error": str(exc)})
        summary = None
    return {"recent": recent, "summary": summary}
