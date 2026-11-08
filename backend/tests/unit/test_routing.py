"""Expected behaviour of `route_after_rewrite` (backend/src/agent/graph/builder.py).

These tests describe the routing contract; they pass once the TODO(human) in builder.py is
implemented. Adjust them if you deliberately choose different behaviour, but keep the
safety cases: unsafe messages must never trigger retrieval.
"""

from __future__ import annotations

import pytest

from agent.graph.builder import route_after_rewrite
from agent.graph.state import RewriteResult


def state_for(**rewrite) -> dict:
    defaults = {"standalone_query": "What did Reuben build at FlyRank AI?"}
    return {"question": "q", "rewrite": RewriteResult(**{**defaults, **rewrite})}


def test_portfolio_question_retrieves():
    assert (
        route_after_rewrite(state_for(intent="portfolio_question", needs_retrieval=True))
        == "retrieve"
    )


@pytest.mark.parametrize("intent", ["greeting", "off_topic"])
def test_small_talk_answers_directly(intent):
    assert route_after_rewrite(state_for(intent=intent, needs_retrieval=False)) == "respond"


def test_unsafe_never_retrieves_even_if_rewriter_says_so():
    assert route_after_rewrite(state_for(intent="unsafe", needs_retrieval=True)) == "respond"


def test_portfolio_question_retrieves_even_if_rewriter_disagrees():
    # The rewriter is a small model; for questions about Reuben, grounding is never wasted.
    assert (
        route_after_rewrite(state_for(intent="portfolio_question", needs_retrieval=False))
        == "retrieve"
    )
