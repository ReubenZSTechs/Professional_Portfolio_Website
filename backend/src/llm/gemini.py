"""Thin wrapper around the google-genai SDK.

Keeps model ids, retries and embedding post-processing in one place so the graph nodes and the
ingest script never touch the SDK directly (and tests can swap in a fake client).

    gemini = get_gemini()
    text = gemini.generate("Hello", system="Be brief.")
    data = gemini.generate_json(prompt, schema=REWRITER_SCHEMA, model=settings.gemini_rewrite_model)
    for delta in gemini.stream(prompt, system=SYSTEM_PROMPT): ...
    vectors = gemini.embed(["chunk one", "chunk two"], task_type="RETRIEVAL_DOCUMENT")
"""

from __future__ import annotations

import json
import math
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from functools import lru_cache
from typing import Any, Literal, TypeVar, overload

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel

from core.config import GEMINI_NATIVE_EMBED_DIM, Settings, get_settings
from core.logging import get_logger

log = get_logger(__name__)

TaskType = Literal[
    "RETRIEVAL_DOCUMENT",
    "RETRIEVAL_QUERY",
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION",
    "CLUSTERING",
    "QUESTION_ANSWERING",
    "FACT_VERIFICATION",
    "CODE_RETRIEVAL_QUERY",
]

# `contents` accepted by the SDK: a string, a list of strings/Content objects, etc.
Contents = str | Sequence[Any]
ModelT = TypeVar("ModelT", bound=BaseModel)
T = TypeVar("T")

# One embed_content request carries at most this many texts (batchEmbedContents limit).
MAX_EMBED_BATCH = 100


class GeminiError(RuntimeError):
    """The model returned something unusable (empty, blocked, or invalid JSON)."""


def l2_normalize(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return list(vector)
    return [x / norm for x in vector]


class ModelUnavailableError(GeminiError):
    """Every model in the fallback chain was overloaded, rate-limited, missing or timed out."""


# Statuses that mean "this model can't serve you right now": try the next one in the chain.
#   404 retired/unknown model · 408 timeout · 429 rate limit · 5xx overloaded/unavailable
FALLBACK_STATUS_CODES = frozenset({404, 408, 429, 500, 502, 503, 504})

Role = Literal["chat", "rewrite"]


def is_unavailable(exc: BaseException) -> bool:
    """True for errors where another model might succeed (as opposed to bad input or bad keys)."""
    if isinstance(exc, genai_errors.APIError):
        return exc.code in FALLBACK_STATUS_CODES
    return isinstance(exc, httpx.TimeoutException | httpx.TransportError | TimeoutError)


class GeminiClient:
    def __init__(self, settings: Settings | None = None, client: genai.Client | None = None):
        self.settings = settings or get_settings()
        self._client = client

    @property
    def client(self) -> genai.Client:
        # Created on first use so importing this module never needs an API key.
        if self._client is None:
            self._client = genai.Client(
                api_key=self.settings.require("gemini_api_key"),
                http_options=types.HttpOptions(
                    timeout=int(self.settings.gemini_timeout_seconds * 1000),  # ms
                    # One quick retry for blips; anything longer is handled by moving on to the
                    # next model, which beats retrying an overloaded one for minutes.
                    retry_options=types.HttpRetryOptions(
                        attempts=2, initial_delay=0.5, max_delay=2.0
                    ),
                ),
            )
        return self._client

    # ------------------------------------------------------------------ model chains
    def candidates(self, model: str | None, role: Role) -> list[str]:
        """The primary model followed by its fallbacks, without duplicates.

        The role is inferred from the model when it is one of the configured primaries, so
        `generate(model=settings.gemini_rewrite_model)` gets the rewrite fallbacks."""
        s = self.settings
        primary = model or (s.gemini_rewrite_model if role == "rewrite" else s.gemini_chat_model)
        if primary == s.gemini_rewrite_model:
            role = "rewrite"
        elif primary == s.gemini_chat_model:
            role = "chat"
        fallbacks = (
            s.gemini_rewrite_fallback_models if role == "rewrite" else s.gemini_chat_fallback_models
        )
        return list(dict.fromkeys([primary, *fallbacks]))

    def _unavailable(self, models: list[str], errors: list[str]) -> ModelUnavailableError:
        detail = "; ".join(errors)
        return ModelUnavailableError(f"No Gemini model available (tried {models}): {detail}")

    def _with_fallback(self, models: list[str], call: Callable[[str], T]) -> T:
        errors: list[str] = []
        for i, model in enumerate(models):
            try:
                result = call(model)
            except Exception as exc:
                if not is_unavailable(exc):
                    raise
                errors.append(f"{model}: {type(exc).__name__} {getattr(exc, 'code', '')}".strip())
                if i + 1 < len(models):
                    log.warning(
                        "gemini_fallback",
                        extra={
                            "failed_model": model,
                            "next_model": models[i + 1],
                            "error": str(exc)[:200],
                        },
                    )
                continue
            if i > 0:
                log.info("gemini_fallback_used", extra={"model": model})
            return result
        raise self._unavailable(models, errors)

    # ------------------------------------------------------------------ generation
    def _config(
        self,
        *,
        system: str | None,
        temperature: float | None,
        max_output_tokens: int | None,
        thinking_level: str | None = None,
        **extra: Any,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level)
            if thinking_level
            else None,
            **extra,
        )

    def generate(
        self,
        contents: Contents,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        config = self._config(
            system=system, temperature=temperature, max_output_tokens=max_output_tokens
        )

        def call(m: str) -> str:
            text = self.client.models.generate_content(
                model=m, contents=contents, config=config
            ).text
            if not text:
                raise GeminiError(f"Empty response from {m}")
            return text

        return self._with_fallback(self.candidates(model, "chat"), call)

    @overload
    def generate_json(self, contents: Contents, schema: type[ModelT], **kwargs: Any) -> ModelT: ...
    @overload
    def generate_json(
        self, contents: Contents, schema: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]: ...
    def generate_json(
        self,
        contents: Contents,
        schema: type[BaseModel] | dict[str, Any],
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = 0.0,
        max_output_tokens: int | None = None,
    ) -> BaseModel | dict[str, Any]:
        """Structured output. `schema` is a Pydantic model (returns an instance) or a JSON
        Schema dict such as backend/src/schemas/prompt_rewriter.schema.json (returns a dict)."""
        is_model = isinstance(schema, type) and issubclass(schema, BaseModel)
        schema_kwarg = "response_schema" if is_model else "response_json_schema"
        config = self._config(
            system=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            **{schema_kwarg: schema},
        )

        def call(m: str) -> tuple[str, str]:
            text = self.client.models.generate_content(
                model=m, contents=contents, config=config
            ).text
            if not text:
                raise GeminiError(f"Empty JSON response from {m}")
            return m, text

        used, text = self._with_fallback(self.candidates(model, "rewrite"), call)
        try:
            if is_model:
                return schema.model_validate_json(text)  # type: ignore[union-attr]
            data = json.loads(text)
        except ValueError as exc:  # json.JSONDecodeError and pydantic.ValidationError
            raise GeminiError(f"{used} returned invalid JSON: {text[:200]!r}") from exc
        if not isinstance(data, dict):
            raise GeminiError(f"{used} returned JSON that is not an object: {text[:200]!r}")
        return data

    def stream(
        self,
        contents: Contents,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> Iterator[str]:
        """Yield text deltas as they arrive. Falls back to the next model only if the current
        one fails before producing any text (a half-streamed answer can't be restarted)."""
        config = self._config(
            system=system, temperature=temperature, max_output_tokens=max_output_tokens
        )
        models = self.candidates(model, "chat")
        errors: list[str] = []
        for m in models:
            started = False
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=m, contents=contents, config=config
                ):
                    if chunk.text:
                        started = True
                        yield chunk.text
                return
            except Exception as exc:
                if started or not is_unavailable(exc):
                    raise
                errors.append(f"{m}: {type(exc).__name__} {getattr(exc, 'code', '')}".strip())
                log.warning("gemini_fallback", extra={"failed_model": m, "error": str(exc)[:200]})
        raise self._unavailable(models, errors)

    async def astream(
        self,
        contents: Contents,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        thinking_level: str | None = None,
    ) -> AsyncIterator[str]:
        """Async variant of `stream` (same fallback rules), for the LangGraph respond node."""
        config = self._config(
            system=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
        )
        models = self.candidates(model, "chat")
        errors: list[str] = []
        for m in models:
            started = False
            try:
                response = await self.client.aio.models.generate_content_stream(
                    model=m, contents=contents, config=config
                )
                finish = None
                async for chunk in response:
                    candidates = getattr(chunk, "candidates", None)
                    if candidates and candidates[0].finish_reason:
                        finish = candidates[0].finish_reason
                    if chunk.text:
                        started = True
                        yield chunk.text
                if finish == types.FinishReason.MAX_TOKENS:
                    log.warning(
                        "gemini_answer_truncated",
                        extra={"model": m, "max_output_tokens": max_output_tokens},
                    )
                return
            except Exception as exc:
                if started or not is_unavailable(exc):
                    raise
                errors.append(f"{m}: {type(exc).__name__} {getattr(exc, 'code', '')}".strip())
                log.warning("gemini_fallback", extra={"failed_model": m, "error": str(exc)[:200]})
        raise self._unavailable(models, errors)

    # ------------------------------------------------------------------ embeddings
    def embed(
        self,
        texts: Sequence[str],
        task_type: TaskType,
        *,
        model: str | None = None,
        dim: int | None = None,
    ) -> list[list[float]]:
        """Embed up to MAX_EMBED_BATCH texts in one request (see rag.embedder for batching).

        Vectors are L2-normalised when `dim` < 3072, as Google requires for truncated
        gemini-embedding-001 outputs, so cosine distance in pgvector behaves.
        """
        if not texts:
            return []
        if len(texts) > MAX_EMBED_BATCH:
            raise ValueError(f"embed() takes at most {MAX_EMBED_BATCH} texts; use rag.embedder")
        dim = dim or self.settings.embed_dim
        response = self.client.models.embed_content(
            model=model or self.settings.gemini_embed_model,
            contents=list(texts),
            config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=dim),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != len(texts):
            raise GeminiError(f"Asked for {len(texts)} embeddings, got {len(embeddings)}")
        vectors: list[list[float]] = []
        for emb in embeddings:
            values = list(emb.values or [])
            if len(values) != dim:
                raise GeminiError(f"Expected {dim}-d embedding, got {len(values)}-d")
            vectors.append(l2_normalize(values) if dim < GEMINI_NATIVE_EMBED_DIM else values)
        return vectors


@lru_cache
def get_gemini() -> GeminiClient:
    """Lazy process-wide singleton (warm serverless invocations reuse the HTTP client)."""
    return GeminiClient()
