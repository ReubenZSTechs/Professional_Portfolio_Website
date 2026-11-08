"""Node 2: the prompt-rewriter agent.

Turns "what stack did it use?" into "What tech stack does the Plantatio project use?",
repairs typos, translates to English for retrieval, and classifies the intent so the graph
can skip retrieval for greetings, off-topic or unsafe messages.
"""

from __future__ import annotations

import asyncio

from agent.graph.events import emit
from agent.graph.state import ChatState, RewriteResult, format_turns, load_prompt, load_schema
from core.config import get_settings
from core.logging import get_logger
from llm.gemini import GeminiError, get_gemini

log = get_logger(__name__)


def build_rewrite_input(state: ChatState) -> str:
    parts: list[str] = []
    if state.get("summary"):
        parts.append(f"Summary of the earlier conversation:\n{state['summary']}")
    recent = state.get("recent") or []
    if recent:
        parts.append(f"Recent turns:\n{format_turns(recent)}")
    parts.append(f"Latest visitor message:\n{state['question']}")
    return "\n\n".join(parts)


async def rewrite_query(state: ChatState) -> ChatState:
    emit("status", {"stage": "rewriting"})
    settings = get_settings()
    try:
        data = await asyncio.to_thread(
            get_gemini().generate_json,
            build_rewrite_input(state),
            load_schema("prompt_rewriter"),
            model=settings.gemini_rewrite_model,
            system=load_prompt("rewrite"),
            temperature=0.0,
            max_output_tokens=256,
        )
        rewrite = RewriteResult.model_validate(data)
        if not rewrite.standalone_query.strip():
            raise ValueError("empty standalone_query")
    except (GeminiError, ValueError) as exc:
        # Fall back to the raw question: retrieval still works, just less precisely.
        log.warning("rewrite_failed", extra={"error": str(exc)})
        rewrite = RewriteResult(standalone_query=state["question"])

    log.info(
        "rewrite",
        extra={
            "intent": rewrite.intent,
            "needs_retrieval": rewrite.needs_retrieval,
            "language": rewrite.language,
            "standalone_query": rewrite.standalone_query,
        },
    )
    return {"rewrite": rewrite}
