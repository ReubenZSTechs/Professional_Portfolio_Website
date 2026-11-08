"""Progress events that nodes push to the client while the graph runs.

Nodes call `emit(...)`; the chat route reads them from `graph.astream(stream_mode="custom")`
and forwards each one as a Server-Sent Event. Outside a streaming run (e.g. in unit tests
that call a node directly) `emit` is a no-op.
"""

from __future__ import annotations

from typing import Any, Literal

from langgraph.config import get_stream_writer

EventName = Literal["status", "token", "sources", "error"]


def emit(event: EventName, data: dict[str, Any]) -> None:
    try:
        writer = get_stream_writer()
    except RuntimeError:  # not inside a LangGraph run
        return
    writer({"event": event, "data": data})
