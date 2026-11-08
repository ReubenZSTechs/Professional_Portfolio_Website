"""Deterministic pre-LLM screening of visitor input.

Runs before any model call, so a blocked attack costs nothing and can't be argued with. The
LLM-based check (the rewriter's `unsafe` intent) still runs afterwards for anything subtler.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass, field

from agent.guardrails.normalize import fold_for_matching, normalize_text
from agent.guardrails.patterns import BLOCK_SCORE, RULES, SUSPICIOUS_SCORE


@dataclass(frozen=True)
class GuardResult:
    score: float = 0.0
    rules: tuple[str, ...] = field(default_factory=tuple)

    @property
    def blocked(self) -> bool:
        return self.score >= BLOCK_SCORE

    @property
    def suspicious(self) -> bool:
        return self.score >= SUSPICIOUS_SCORE


_BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/_-]{24,}={0,2}")


def _decoded_payloads(text: str) -> list[str]:
    """Decode base64-looking chunks so smuggled instructions are scanned for what they say."""
    found = []
    for token in _BASE64_TOKEN.findall(text)[:5]:
        padded = token + "=" * (-len(token) % 4)
        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                raw = decoder(padded)
            except (binascii.Error, ValueError):
                continue
            decoded = raw.decode("utf-8", "ignore")
            printable = sum(ch.isprintable() or ch.isspace() for ch in decoded)
            if len(decoded) >= 12 and printable / len(decoded) > 0.9:
                found.append(decoded)
                break
    return found


def scan(text: str, *, _depth: int = 0) -> GuardResult:
    folded = fold_for_matching(text)
    hits = [rule for rule in RULES if rule.pattern.search(folded)]
    score = sum(r.weight for r in hits)
    rules = [r.id for r in hits]
    if _depth == 0:
        for payload in _decoded_payloads(normalize_text(text)):
            inner = scan(payload, _depth=1)
            if inner.score:
                score += inner.score
                rules += ["payload.decoded"] + [f"decoded:{r}" for r in inner.rules]
    return GuardResult(score=round(score, 2), rules=tuple(dict.fromkeys(rules)))


def scan_conversation(question: str, user_turns: list[str]) -> GuardResult:
    """Screen the new question plus earlier user turns, so a payload split across messages
    ("remember X" … "now do X") is still caught. Earlier turns count at half weight."""
    current = scan(question)
    earlier = scan("\n".join(user_turns)) if user_turns else GuardResult()
    rules = tuple(dict.fromkeys(current.rules + earlier.rules))
    return GuardResult(score=round(current.score + earlier.score * 0.5, 2), rules=rules)
