"""Gemini wrapper, embedder, retriever and rag_search with the SDK and Supabase faked."""

from __future__ import annotations

import math
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from core.config import Settings
from llm.gemini import GeminiClient, GeminiError
from rag.embedder import embed_texts
from rag.retriever import retrieve
from tools.rag_search import format_context, rag_search, to_sources

DIM = 128  # smallest allowed EMBED_DIM; < 3072 so normalisation applies


class FakeModels:
    def __init__(self, *, text: str = "", fail_times: int = 0):
        self.text = text
        self.fail_times = fail_times
        self.embed_calls: list[dict[str, Any]] = []
        self.generate_calls: list[dict[str, Any]] = []

    def embed_content(self, *, model, contents, config):
        self.embed_calls.append({"model": model, "contents": contents, "config": config})
        if self.fail_times:
            self.fail_times -= 1
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        dim = config.output_dimensionality
        # deterministic, non-normalised vectors: [i+1, 1, 1, ...]
        embeddings = [
            SimpleNamespace(values=[float(i + 1)] + [1.0] * (dim - 1)) for i in range(len(contents))
        ]
        return SimpleNamespace(embeddings=embeddings)

    def generate_content(self, *, model, contents, config):
        self.generate_calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(text=self.text)

    def generate_content_stream(self, *, model, contents, config):
        return iter(
            [SimpleNamespace(text="Hel"), SimpleNamespace(text=None), SimpleNamespace(text="lo")]
        )


def make_gemini(**kw) -> tuple[GeminiClient, FakeModels]:
    models = FakeModels(**kw)
    return GeminiClient(Settings(embed_dim=DIM), client=SimpleNamespace(models=models)), models


# ----------------------------------------------------------------------------- gemini
def test_embed_normalises_truncated_dimensions():
    gemini, models = make_gemini()
    [vec] = gemini.embed(["hello"], "RETRIEVAL_DOCUMENT")
    assert len(vec) == DIM
    assert math.isclose(math.sqrt(sum(x * x for x in vec)), 1.0)
    cfg = models.embed_calls[0]["config"]
    assert cfg.task_type == "RETRIEVAL_DOCUMENT"
    assert cfg.output_dimensionality == DIM


def test_embed_full_dimension_left_as_is():
    models = FakeModels()
    gemini = GeminiClient(Settings(embed_dim=3072), client=SimpleNamespace(models=models))
    [vec] = gemini.embed(["hello"], "RETRIEVAL_QUERY")
    assert vec[0] == 1.0 and len(vec) == 3072


def test_embed_rejects_oversized_batch():
    gemini, _ = make_gemini()
    with pytest.raises(ValueError):
        gemini.embed(["x"] * 101, "RETRIEVAL_DOCUMENT")


def test_generate_json_with_dict_schema():
    gemini, models = make_gemini(text='{"standalone_query": "q", "needs_retrieval": true}')
    schema = {"type": "object", "properties": {"standalone_query": {"type": "string"}}}
    out = gemini.generate_json("prompt", schema)
    assert out == {"standalone_query": "q", "needs_retrieval": True}
    cfg = models.generate_calls[0]["config"]
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema == schema
    assert models.generate_calls[0]["model"] == "gemini-3.5-flash-lite"


def test_generate_json_with_pydantic_schema():
    class Rewrite(BaseModel):
        standalone_query: str

    gemini, _ = make_gemini(text='{"standalone_query": "what stack did Plantatio use?"}')
    assert gemini.generate_json("p", Rewrite).standalone_query.startswith("what stack")


def test_generate_json_invalid_raises():
    gemini, _ = make_gemini(text="not json")
    with pytest.raises(GeminiError):
        gemini.generate_json("p", {"type": "object"})


def test_generate_and_stream():
    gemini, models = make_gemini(text="answer")
    assert gemini.generate("hi", system="be brief") == "answer"
    assert models.generate_calls[0]["config"].system_instruction == "be brief"
    assert models.generate_calls[0]["model"] == "gemini-3.6-flash"
    assert "".join(gemini.stream("hi")) == "Hello"


# ----------------------------------------------------------------------------- embedder
def test_embed_texts_batches_in_order():
    gemini, models = make_gemini()
    vectors = embed_texts([f"t{i}" for i in range(5)], gemini=gemini, batch_size=2)
    assert len(vectors) == 5
    assert [len(c["contents"]) for c in models.embed_calls] == [2, 2, 1]


def test_embed_texts_retries_with_backoff():
    gemini, _ = make_gemini(fail_times=2)
    sleeps: list[float] = []
    vectors = embed_texts(["a"], gemini=gemini, sleep=sleeps.append, base_delay=1.0)
    assert len(vectors) == 1
    assert sleeps == [1.0, 2.0]


def test_embed_texts_gives_up():
    gemini, _ = make_gemini(fail_times=10)
    with pytest.raises(RuntimeError):
        embed_texts(["a"], gemini=gemini, sleep=lambda _: None, max_attempts=3)


# ----------------------------------------------------------------------------- retrieval
ROWS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "source_type": "project",
        "source_id": "project:plantatio",
        "title": "Plantatio",
        "url": "/projects/plantatio",
        "section": "How it works",
        "chunk_index": 2,
        "content": "Plantatio — How it works\n\nA four-node LangGraph pipeline over typed state.",
        "metadata": {"featured": True},
        "similarity": 0.81234,
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "source_type": "experience",
        "source_id": "experience:flyrank",
        "title": "Backend AI Engineer — FlyRank AI",
        "url": "/#experience",
        "section": None,
        "chunk_index": 0,
        "content": "Backend AI Engineer — FlyRank AI\n\nCategory: Experience",
        "metadata": {},
        "similarity": 0.66,
    },
]


class FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=self.rows))


def test_retrieve_calls_rpc_with_query_embedding():
    gemini, models = make_gemini()
    db = FakeSupabase(ROWS)
    chunks = retrieve(
        "langgraph?", k=4, min_similarity=0.3, filter={"source_type": "project"},
        gemini=gemini, supabase=db,
    )  # fmt: skip
    assert [c.source_id for c in chunks] == ["project:plantatio", "experience:flyrank"]
    name, params = db.calls[0]
    assert name == "match_documents"
    assert params["match_count"] == 4
    assert params["min_similarity"] == 0.3
    assert params["filter"] == {"source_type": "project"}
    assert len(params["query_embedding"]) == DIM
    assert models.embed_calls[0]["config"].task_type == "RETRIEVAL_QUERY"


def test_retrieve_uses_settings_defaults():
    gemini, _ = make_gemini()
    db = FakeSupabase([])
    assert retrieve("q", gemini=gemini, supabase=db) == []
    params = db.calls[0][1]
    assert params["match_count"] == 6
    assert params["filter"] == {}


def test_blank_query_makes_no_calls():
    gemini, models = make_gemini()
    db = FakeSupabase(ROWS)
    assert retrieve("   ", gemini=gemini, supabase=db) == []
    assert db.calls == [] and models.embed_calls == []


def test_rag_search_formats_context_and_sources():
    gemini, _ = make_gemini()
    result = rag_search("q", gemini=gemini, supabase=FakeSupabase(ROWS))
    assert result.context.startswith(
        "[1] Plantatio — How it works (/projects/plantatio)\nA four-node LangGraph pipeline"
    )
    assert "[2] Backend AI Engineer — FlyRank AI (/#experience)" in result.context
    first = result.sources[0]
    assert (first.n, first.type, first.url, first.similarity) == (
        1, "project", "/projects/plantatio", 0.8123,
    )  # fmt: skip
    assert first.snippet == "A four-node LangGraph pipeline over typed state."


def test_format_helpers_on_empty():
    assert format_context([]) == ""
    assert to_sources([]) == []
