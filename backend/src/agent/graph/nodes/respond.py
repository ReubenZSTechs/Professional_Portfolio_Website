"""Node 4: the answering agent. Streams a grounded, cited answer token by token."""

from __future__ import annotations

import re

from google.genai import types

from agent.graph.events import emit
from agent.graph.state import ChatState, load_prompt
from core.config import get_settings
from core.logging import get_logger
from llm.gemini import get_gemini

log = get_logger(__name__)

# Matches [3] and grouped citations like [2, 4].
CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

# Fixed replies for messages that should never reach the answering model.
CANNED = {
    "unsafe": (
        "I can only answer questions about Reuben's work: his projects, experience, skills "
        "and research. What would you like to know?"
    ),
}

NO_CONTEXT_NOTE = (
    "No passages matched this question. Tell the visitor you don't have that information in "
    "Reuben's portfolio, and suggest a related question you could answer or contacting him."
)
NO_RETRIEVAL_NOTE = (
    "This message does not need Reuben's documents (it is a greeting or off-topic). Reply in "
    "one or two friendly sentences and steer back to what you can help with: Reuben's projects, "
    "experience, skills and research."
)


def build_contents(state: ChatState) -> list[types.Content]:
    """Gemini chat contents: recent turns, then the question with its numbered context."""
    contents: list[types.Content] = []
    if state.get("summary"):
        contents.append(
            types.Content(
                role="user", parts=[types.Part(text=f"(Earlier conversation: {state['summary']})")]
            )
        )
        contents.append(types.Content(role="model", parts=[types.Part(text="Understood.")]))
    for turn in state.get("recent") or []:
        role = "user" if turn.role == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn.content)]))

    retrieval = state.get("retrieval")
    rewrite = state["rewrite"]
    if retrieval is None:
        note = NO_RETRIEVAL_NOTE
    elif retrieval.empty:
        note = NO_CONTEXT_NOTE
    else:
        note = f"Context passages:\n\n{retrieval.context}"

    prompt = (
        f"{note}\n\n"
        f"Visitor's question: {state['question']}\n"
        f"(Interpreted as: {rewrite.standalone_query})"
    )
    contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
    return contents


def cited_numbers(answer: str) -> set[int]:
    return {int(n) for group in CITATION.findall(answer) for n in group.split(",")}


async def respond(state: ChatState) -> ChatState:
    rewrite = state["rewrite"]

    if rewrite.intent in CANNED:
        answer = CANNED[rewrite.intent]
        emit("token", {"text": answer})
        return {"answer": answer}

    emit("status", {"stage": "answering"})
    system = load_prompt("system").replace("{language}", rewrite.language or "en")
    parts: list[str] = []
    settings = get_settings()
    async for delta in get_gemini().astream(
        build_contents(state),
        system=system,
        temperature=0.3,
        max_output_tokens=settings.answer_max_output_tokens,
        thinking_level=settings.gemini_chat_thinking_level or None,
    ):
        parts.append(delta)
        emit("token", {"text": delta})
    answer = "".join(parts)

    retrieval = state.get("retrieval")
    if retrieval and not retrieval.empty:
        # Only show the sources the answer actually cites, keeping their original numbers
        # so the [n] markers already streamed to the browser still match.
        used = cited_numbers(answer)
        sources = [
            {
                "id": s.n,
                "type": s.type,
                "title": s.title,
                "section": s.section,
                "snippet": s.snippet,
                "url": s.url,
            }
            for s in retrieval.sources
            if s.n in used
        ]
        emit("sources", {"sources": sources})
        log.info("answered", extra={"retrieved": len(retrieval.sources), "cited": sorted(used)})
    return {"answer": answer}
