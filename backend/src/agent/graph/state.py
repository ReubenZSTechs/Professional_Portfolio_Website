"""Shared state passed between LangGraph nodes, plus the prompt/schema loaders the nodes use."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

from tools.rag_search import RagSearchResult

SRC_DIR = Path(__file__).resolve().parents[2]  # backend/src

Role = Literal["user", "assistant"]
Intent = Literal["portfolio_question", "greeting", "off_topic", "unsafe"]


class Turn(BaseModel):
    role: Role
    content: str = Field(max_length=12_000)
    # HMAC the server attached to an assistant answer (docs/security.md, history integrity).
    sig: str | None = Field(default=None, max_length=128)


class RewriteResult(BaseModel):
    """Output of the prompt-rewriter agent (schemas/prompt_rewriter.schema.json)."""

    standalone_query: str
    intent: Intent = "portfolio_question"
    needs_retrieval: bool = True
    language: str = Field(default="en", max_length=8)


class ChatState(TypedDict, total=False):
    # Input
    question: str
    history: list[Turn]
    # Guardrails: flagged by the input guard (not blocked), and the spotlighting id.
    suspicious: bool
    nonce: str
    ip_hash: str  # for security-event logs only (salted hash, never the raw IP)
    # compile_history
    recent: list[Turn]  # the turns kept verbatim
    summary: str | None  # summary of older turns, if any
    # rewrite_query
    rewrite: RewriteResult
    # retrieve
    retrieval: RagSearchResult | None
    # respond
    answer: str


@cache
def load_prompt(name: str) -> str:
    """Read backend/src/prompts/<name>.md (cached for the life of the process)."""
    return (SRC_DIR / "prompts" / f"{name}.md").read_text(encoding="utf-8").strip()


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Read backend/src/schemas/<name>.schema.json."""
    schema = json.loads((SRC_DIR / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    # Gemini's response_json_schema doesn't need the JSON-Schema meta keys.
    return {k: v for k, v in schema.items() if k not in {"$schema", "title", "description"}}


def format_turns(turns: list[Turn]) -> str:
    """Plain-text transcript used inside prompts."""
    return "\n".join(
        f"{'Visitor' if t.role == 'user' else 'Assistant'}: {t.content}" for t in turns
    )
