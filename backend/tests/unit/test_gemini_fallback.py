"""Model fallback: an overloaded / retired / slow Gemini model is skipped for the next one."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors as genai_errors

from core.config import Settings
from llm.gemini import GeminiClient, ModelUnavailableError, is_unavailable


def api_error(code: int) -> genai_errors.APIError:
    cls = genai_errors.ServerError if code >= 500 else genai_errors.ClientError
    return cls(code, {"error": {"code": code, "message": "x", "status": "X"}})


class FlakyModels:
    """Fails for the models listed in `failures` (model -> exception), answers otherwise."""

    def __init__(self, failures: dict[str, BaseException], fail_mid_stream: str | None = None):
        self.failures = failures
        self.fail_mid_stream = fail_mid_stream
        self.calls: list[str] = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        if model in self.failures:
            raise self.failures[model]
        return SimpleNamespace(text=f'{{"answer": "from {model}"}}')

    def generate_content_stream(self, *, model, contents, config):
        self.calls.append(model)
        if model in self.failures:
            raise self.failures[model]

        def chunks():
            yield SimpleNamespace(text=f"from {model}")
            if model == self.fail_mid_stream:
                raise api_error(503)

        return chunks()


class AsyncFlakyModels:
    def __init__(self, sync: FlakyModels):
        self.sync = sync

    async def generate_content_stream(self, *, model, contents, config):
        iterator = self.sync.generate_content_stream(model=model, contents=contents, config=config)

        async def agen():
            for chunk in iterator:
                yield chunk

        return agen()


SETTINGS = Settings(
    gemini_chat_model="chat-a",
    gemini_chat_fallback_models=["chat-b", "chat-c"],
    gemini_rewrite_model="rw-a",
    gemini_rewrite_fallback_models=["rw-b"],
)


def make(failures: dict[str, BaseException], **kw) -> tuple[GeminiClient, FlakyModels]:
    models = FlakyModels(failures, **kw)
    client = SimpleNamespace(models=models, aio=SimpleNamespace(models=AsyncFlakyModels(models)))
    return GeminiClient(SETTINGS, client=client), models


@pytest.mark.parametrize("code", [404, 429, 500, 503])
def test_generate_falls_back_on_unavailable_status(code):
    gemini, models = make({"chat-a": api_error(code)})
    assert gemini.generate("hi") == '{"answer": "from chat-b"}'
    assert models.calls == ["chat-a", "chat-b"]


def test_generate_falls_back_on_timeout():
    gemini, _models = make({"chat-a": httpx.ReadTimeout("slow")})
    assert "chat-b" in gemini.generate("hi")


def test_auth_errors_are_not_retried_on_other_models():
    gemini, models = make({"chat-a": api_error(401)})
    with pytest.raises(genai_errors.ClientError):
        gemini.generate("hi")
    assert models.calls == ["chat-a"]


def test_all_models_down_raises_model_unavailable():
    down = {m: api_error(503) for m in ["chat-a", "chat-b", "chat-c"]}
    gemini, models = make(down)
    with pytest.raises(ModelUnavailableError, match="chat-a"):
        gemini.generate("hi")
    assert models.calls == ["chat-a", "chat-b", "chat-c"]


def test_generate_json_uses_the_rewrite_chain():
    gemini, models = make({"rw-a": api_error(503)})
    assert gemini.generate_json("q", {"type": "object"}) == {"answer": "from rw-b"}
    assert models.calls == ["rw-a", "rw-b"]


def test_role_is_inferred_from_an_explicit_primary():
    gemini, _ = make({})
    assert gemini.candidates("rw-a", "chat") == ["rw-a", "rw-b"]
    assert gemini.candidates("custom", "chat") == ["custom", "chat-b", "chat-c"]
    assert gemini.candidates(None, "chat") == ["chat-a", "chat-b", "chat-c"]


def test_stream_falls_back_before_first_token():
    gemini, _models = make({"chat-a": api_error(503)})
    assert "".join(gemini.stream("hi")) == "from chat-b"


def test_stream_does_not_restart_after_text_was_sent():
    gemini, models = make({}, fail_mid_stream="chat-a")
    out = []
    with pytest.raises(genai_errors.ServerError):
        for delta in gemini.stream("hi"):
            out.append(delta)
    assert out == ["from chat-a"]  # no duplicated/mixed answer from another model
    assert models.calls == ["chat-a"]


async def test_astream_falls_back_before_first_token():
    gemini, models = make({"chat-a": api_error(503), "chat-b": httpx.ConnectTimeout("x")})
    out = [d async for d in gemini.astream("hi")]
    assert out == ["from chat-c"]
    assert models.calls == ["chat-a", "chat-b", "chat-c"]


def test_fallback_lists_accept_comma_separated_env(monkeypatch):
    monkeypatch.setenv("GEMINI_CHAT_FALLBACK_MODELS", "m1, m2 ,m3")
    assert Settings().gemini_chat_fallback_models == ["m1", "m2", "m3"]


def test_is_unavailable_classification():
    assert is_unavailable(api_error(503))
    assert is_unavailable(httpx.ReadTimeout("t"))
    assert not is_unavailable(api_error(400))
    assert not is_unavailable(ValueError("bad"))
