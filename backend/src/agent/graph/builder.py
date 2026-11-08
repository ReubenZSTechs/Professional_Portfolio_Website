"""Assembles the chat graph.

    START → compile_history → rewrite_query ─┬─▶ retrieve ─▶ respond → END
                                             └────────────▶ respond → END

The conditional edge after `rewrite_query` decides whether the question needs Reuben's
documents. See docs/agent-graph.md for the full walkthrough.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graph.nodes.compile_history import compile_history
from agent.graph.nodes.respond import respond
from agent.graph.nodes.retrieve import retrieve
from agent.graph.nodes.rewrite_query import rewrite_query
from agent.graph.state import ChatState

Route = Literal["retrieve", "respond"]


def route_after_rewrite(state: ChatState) -> Route:
    """Decide where the graph goes after the prompt-rewriter agent.

    `state["rewrite"]` is a RewriteResult with:
      - intent: "portfolio_question" | "greeting" | "off_topic" | "unsafe"
      - needs_retrieval: bool  (the rewriter's own opinion)
      - standalone_query: str  (the cleaned-up English query)

    Return "retrieve" to search Reuben's documents first, or "respond" to answer directly
    (respond.py already handles greetings/off-topic politely and "unsafe" with a fixed reply).
    """
    rewrite = state["rewrite"]  # state is a dict; the RewriteResult inside it uses attributes

    # Safety first: manipulation attempts never touch Reuben's documents, whatever the
    # small rewriter model thought about retrieval.
    if rewrite.intent == "unsafe":
        return "respond"

    # Questions about Reuben are always grounded. The rewriter is a cheap model and can
    # misjudge needs_retrieval; one extra vector search is cheaper than an ungrounded answer.
    if rewrite.intent == "portfolio_question":
        return "retrieve"

    # Greetings and off-topic messages: trust the rewriter (normally False → answer directly).
    return "retrieve" if rewrite.needs_retrieval else "respond"


def build_graph(router: Callable[[ChatState], Route] = route_after_rewrite) -> CompiledStateGraph:
    graph = StateGraph(ChatState)
    graph.add_node("compile_history", compile_history)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("respond", respond)

    graph.add_edge(START, "compile_history")
    graph.add_edge("compile_history", "rewrite_query")
    graph.add_conditional_edges(
        "rewrite_query", router, {"retrieve": "retrieve", "respond": "respond"}
    )
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


@lru_cache
def get_graph() -> CompiledStateGraph:
    """Compiled once per process; warm serverless invocations reuse it."""
    return build_graph()
