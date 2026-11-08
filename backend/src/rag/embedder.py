"""Batch embedding with retry/backoff on top of llm.gemini.GeminiClient.embed."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from core.logging import get_logger
from llm.gemini import MAX_EMBED_BATCH, GeminiClient, TaskType, get_gemini

log = get_logger(__name__)


def batched[T](items: Sequence[T], size: int) -> list[Sequence[T]]:
    if size < 1:
        raise ValueError("batch size must be >= 1")
    return [items[i : i + size] for i in range(0, len(items), size)]


def embed_texts(
    texts: Sequence[str],
    *,
    task_type: TaskType = "RETRIEVAL_DOCUMENT",
    gemini: GeminiClient | None = None,
    batch_size: int | None = None,
    max_attempts: int = 4,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list[list[float]]:
    """Embed any number of texts, `batch_size` per request, preserving order.

    The SDK already retries transient HTTP errors; this outer loop adds a longer backoff for
    free-tier quota (429) bursts during a full re-index.
    """
    gemini = gemini or get_gemini()
    size = min(batch_size or gemini.settings.embed_batch_size, MAX_EMBED_BATCH)
    vectors: list[list[float]] = []
    batches = batched(texts, size)
    for n, batch in enumerate(batches, start=1):
        for attempt in range(1, max_attempts + 1):
            try:
                vectors.extend(gemini.embed(batch, task_type))
                break
            except Exception as exc:  # SDK raises several error types; retry them all
                if attempt == max_attempts:
                    raise
                delay = base_delay * 2 ** (attempt - 1)
                log.warning(
                    "embed batch failed, retrying",
                    extra={"batch": n, "attempt": attempt, "delay_s": delay, "error": str(exc)},
                )
                sleep(delay)
        log.info("embedded batch", extra={"batch": n, "of": len(batches), "size": len(batch)})
    return vectors


def embed_query(query: str, *, gemini: GeminiClient | None = None) -> list[float]:
    """Single query embedding with the RETRIEVAL_QUERY task type (asymmetric retrieval)."""
    gemini = gemini or get_gemini()
    return gemini.embed([query], "RETRIEVAL_QUERY")[0]
