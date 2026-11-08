"""Streaming output guard: stop an answer that leaks the system prompt.

Checked after every streamed chunk:
  1. the canary token (a random marker placed in the system prompt at runtime; it never appears
     in normal answers, so seeing it proves the prompt is being echoed),
  2. any run of LEAK_NGRAM consecutive words copied from the system or rewrite prompt,
  3. chat-template / role markers echoed back.
On a hit the respond node stops streaming and sends a `retract` event that replaces the
partial answer with the standard refusal.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

LEAK_NGRAM = 10
CANARY = f"CANARY-{secrets.token_hex(8)}"  # new on every cold start, never in the repo

_WORDS = re.compile(r"[a-z0-9']+")
_MARKERS = re.compile(r"<\|(?:im_start|im_end|system)\|>|\[/?INST\]|<</?SYS>>", re.I)


def _words(text: str) -> list[str]:
    return _WORDS.findall(text.lower())


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


@dataclass
class OutputGuard:
    secret_texts: tuple[str, ...]
    # Text the model may legitimately say (e.g. the public refusal line): never counted as a leak.
    public_texts: tuple[str, ...] = ()
    canary: str = CANARY

    def __post_init__(self) -> None:
        self._secret_ngrams: set[tuple[str, ...]] = set()
        for text in self.secret_texts:
            # Strip markdown and placeholders so formatting differences don't hide a copy.
            self._secret_ngrams |= _ngrams(_words(re.sub(r"[*_`#{}]", " ", text)), LEAK_NGRAM)
        for text in self.public_texts:
            self._secret_ngrams -= _ngrams(_words(text), LEAK_NGRAM)

    def check(self, text: str) -> str | None:
        """Returns the reason when `text` (the answer so far) must be retracted."""
        if self.canary in text:
            return "canary"
        if _MARKERS.search(text):
            return "role_marker"
        if self._secret_ngrams and _ngrams(_words(text), LEAK_NGRAM) & self._secret_ngrams:
            return "prompt_leak"
        return None
