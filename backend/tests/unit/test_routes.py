"""HTTP-level tests for /api/py/chat, /contact and /health (graph, Supabase and Resend faked)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agent import main
from agent.routes import chat as chat_route
from agent.routes import contact as contact_route


class FakeGraph:
    async def astream(self, state, stream_mode):
        assert stream_mode == "custom"
        yield {"event": "status", "data": {"stage": "rewriting"}}
        yield {"event": "token", "data": {"text": f"echo: {state['question']}"}}


async def no_limit(*args, **kwargs):
    return "iphash"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(chat_route, "get_graph", lambda: FakeGraph())
    monkeypatch.setattr(chat_route, "enforce_rate_limit", no_limit)
    monkeypatch.setattr(contact_route, "enforce_rate_limit", no_limit)
    return TestClient(main.app)


def parse_sse(text: str) -> list[tuple[str, str]]:
    frames = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        frames.append((lines["event"], lines["data"]))
    return frames


def test_chat_streams_events_then_done(client):
    res = client.post("/api/py/chat", json={"message": "hello", "history": []})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    events = [e for e, _ in parse_sse(res.text)]
    assert events == ["status", "token", "done"]


def test_chat_rejects_overlong_question(client):
    res = client.post("/api/py/chat", json={"message": "x" * 501})
    assert res.status_code == 422
    assert "under 500 characters" in res.json()["detail"]


def test_chat_reports_graph_errors_as_event(client, monkeypatch):
    class Broken:
        async def astream(self, state, stream_mode):
            raise RuntimeError("db down")
            yield  # pragma: no cover

    monkeypatch.setattr(chat_route, "get_graph", lambda: Broken())
    events = parse_sse(client.post("/api/py/chat", json={"message": "hi"}).text)
    assert [e for e, _ in events] == ["error", "done"]
    assert "db down" not in events[0][1]  # internals never leak to the browser


def test_contact_honeypot_pretends_success_without_storing(client, monkeypatch):
    stored = []
    monkeypatch.setattr(contact_route, "get_supabase", lambda: stored.append("x"))
    res = client.post(
        "/api/py/contact",
        json={
            "name": "Bot",
            "email": "bot@example.com",
            "message": "buy stuff now!!",
            "company": "Spam Inc",
        },
    )
    assert res.json() == {"ok": True}
    assert stored == []


def test_contact_saves_then_emails(client, monkeypatch):
    calls = []

    class Table:
        def insert(self, row):
            calls.append(("insert", row["email"]))
            return self

        def execute(self):
            return None

    class Supa:
        def table(self, name):
            assert name == "contact_messages"
            return Table()

    monkeypatch.setattr(contact_route, "get_supabase", lambda: Supa())
    monkeypatch.setattr(
        contact_route, "send_contact_email", lambda *a: calls.append(("email", a[1]))
    )
    res = client.post(
        "/api/py/contact",
        json={
            "name": "Ana",
            "email": "ana@example.com",
            "message": "We'd love to talk about a role.",
        },
    )
    assert res.status_code == 200
    assert calls == [("insert", "ana@example.com"), ("email", "ana@example.com")]


def test_contact_email_failure_still_succeeds(client, monkeypatch):
    class Supa:
        def table(self, name):
            return self

        def insert(self, row):
            return self

        def execute(self):
            return None

    def boom(*a):
        raise RuntimeError("resend down")

    monkeypatch.setattr(contact_route, "get_supabase", lambda: Supa())
    monkeypatch.setattr(contact_route, "send_contact_email", boom)
    res = client.post(
        "/api/py/contact",
        json={"name": "Ana", "email": "ana@example.com", "message": "Hello there, quick question."},
    )
    assert res.status_code == 200


def test_contact_rejects_bad_email(client):
    res = client.post(
        "/api/py/contact", json={"name": "A", "email": "nope", "message": "long enough message"}
    )
    assert res.status_code == 422
    assert res.json()["detail"] == "Please enter a valid email address."


def test_health_reports_configuration_flags_only(client):
    body = client.get("/api/py/health").json()
    assert body["status"] == "ok"
    assert set(body["configured"]) == {"gemini", "supabase", "resend"}


def test_chat_reports_busy_models_politely(client, monkeypatch):
    from llm.gemini import ModelUnavailableError

    class Busy:
        async def astream(self, state, stream_mode):
            raise ModelUnavailableError("all 503")
            yield  # pragma: no cover

    monkeypatch.setattr(chat_route, "get_graph", lambda: Busy())
    events = parse_sse(client.post("/api/py/chat", json={"message": "hi"}).text)
    assert [e for e, _ in events] == ["error", "done"]
    assert '"code": "busy"' in events[0][1]
