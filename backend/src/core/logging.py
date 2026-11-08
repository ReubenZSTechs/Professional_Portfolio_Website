"""Structured JSON logging (one JSON object per line), which Vercel's log viewer indexes.

Usage:
    from core.logging import get_logger
    log = get_logger(__name__)
    log.info("retrieved", extra={"k": 6, "hits": 4, "top_similarity": 0.71})

Anything passed in `extra` becomes a top-level JSON field.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Attributes every LogRecord has; anything else on the record came from `extra=`.
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}

_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str | int | None = None) -> None:
    """Install the JSON handler on the root logger (idempotent)."""
    global _configured
    if level is None:
        from core.config import get_settings

        level = get_settings().log_level
    root = logging.getLogger()
    root.setLevel(level if isinstance(level, int) else level.upper())
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers[:] = [handler]
    # Third-party HTTP clients are chatty at INFO.
    for noisy in ("httpx", "httpcore", "hpack", "google_genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
