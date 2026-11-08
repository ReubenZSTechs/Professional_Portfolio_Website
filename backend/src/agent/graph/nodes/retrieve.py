"""Node 3: search Reuben's documents with the rewritten query."""

from __future__ import annotations

import asyncio

from agent.graph.events import emit
from agent.graph.state import ChatState
from core.logging import get_logger
from tools.rag_search import RagSearchResult, rag_search

log = get_logger(__name__)


async def retrieve(state: ChatState) -> ChatState:
    emit("status", {"stage": "retrieving"})
    query = state["rewrite"].standalone_query
    try:
        result = await asyncio.to_thread(rag_search, query)
    except Exception as exc:  # network / database failure
        # Answering with "I don't have that" beats a 500; the error is logged for us.
        log.error("retrieval_failed", extra={"error": str(exc)})
        result = RagSearchResult(query=query)
    return {"retrieval": result}
