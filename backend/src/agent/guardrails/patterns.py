"""Weighted prompt-injection rules, matched against `fold_for_matching(text)`.

Weights add up; ≥ BLOCK_SCORE blocks without calling the model, ≥ SUSPICIOUS_SCORE flags the
request so the rewriter and answering prompts get an extra caution note.

Rules are deliberately specific to avoid false positives on real recruiter questions such as
"did he act as team lead?" or "what instructions did he follow at FlyRank?". Add a benign and an
attack example to backend/tests/unit/test_security_guardrails.py for every new rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BLOCK_SCORE = 1.0
SUSPICIOUS_SCORE = 0.4


@dataclass(frozen=True)
class Rule:
    id: str
    weight: float
    pattern: re.Pattern[str]


def _r(rule_id: str, weight: float, regex: str) -> Rule:
    return Rule(rule_id, weight, re.compile(regex, re.IGNORECASE))


_PREV = r"(?:all|any|the|your|my|previous|prior|above|earlier|preceding|initial|original|system|these|those)"
_INSTR = r"(?:instructions?|prompts?|rules?|directives?|guidelines?|polic(?:y|ies)|constraints?|context|messages?)"

RULES: tuple[Rule, ...] = (
    # --- Instruction override -------------------------------------------------------------
    _r(
        "override.ignore",
        1.0,
        rf"\b(?:ignore|disregard|forget|override|bypass|skip|drop)\b(?:\s+\w+){{0,3}}\s+{_PREV}\b(?:\s+\w+){{0,2}}\s+{_INSTR}\b",
    ),
    _r(
        "override.new_instructions",
        1.0,
        r"\b(?:new|updated|real|actual|true)\s+(?:system\s+)?instructions?\s*(?:are|:|follow)",
    ),
    _r(
        "override.from_now_on",
        0.6,
        r"\bfrom now on\b.{0,40}\b(?:you (?:will|must|are)|respond|answer|act|ignore)\b",
    ),
    _r(
        "override.id_abaikan",
        1.0,
        r"\b(?:abaikan|lupakan|acuhkan|hiraukan|jangan ikuti|langgar)\b.{0,40}\b(?:instruksi|perintah|aturan|prompt|arahan|pedoman)\b",
    ),
    _r(
        "override.id_mulai_sekarang",
        0.6,
        r"\b(?:mulai sekarang|dari sekarang)\b.{0,40}\b(?:kamu|anda)\b.{0,20}\b(?:harus|adalah|akan)\b",
    ),
    # --- System prompt / instruction extraction ----------------------------------------------
    _r(
        "extract.system_prompt",
        0.6,
        r"\b(?:system|initial|hidden|secret|developer|original)\s+(?:prompt|message|instructions?)\b",
    ),
    _r(
        "extract.reveal",
        0.6,
        r"\b(?:reveal|show|print|display|output|repeat|dump|leak|tell me|give me|copy|paste|spell out|translate)\b.{0,40}\b(?:your|the|all)\s+(?:system\s+)?(?:prompt|instructions|rules|configuration|guidelines)\b",
    ),
    _r(
        "extract.verbatim",
        1.0,
        r"\b(?:repeat|print|output|copy)\b.{0,30}\b(?:everything|all text|the text|words?)\b.{0,20}\b(?:above|before|verbatim|so far)\b",
    ),
    _r(
        "extract.id_prompt",
        1.0,
        r"\b(?:tampilkan|tunjukkan|bocorkan|ulangi|cetak|beritahu)\b.{0,40}\b(?:prompt|instruksi|perintah sistem|aturan)\b",
    ),
    _r("extract.id_prompt_sistem", 0.6, r"\bprompt\s+sistem\b"),
    # Asking the bot about *its own* prompt/instructions (not Reuben's, which is a fair question).
    _r(
        "extract.your_prompt",
        1.0,
        r"\b(?:your|the (?:bot|assistant|chatbot|ai)'?s?)\s+(?:own\s+)?(?:system\s+|hidden\s+|secret\s+|initial\s+|original\s+|internal\s+)?(?:prompt|instructions|configuration|system message)\b",
    ),
    _r(
        "extract.id_your_prompt",
        1.0,
        r"\b(?:prompt|instruksi|aturan|perintah)\s+(?:sistem\s+)?(?:kamu|anda|mu)\b",
    ),
    # --- Persona / jailbreak ------------------------------------------------------------------
    _r("persona.you_are_now", 0.6, r"\byou are (?:now|no longer)\b"),
    _r(
        "persona.act_as_ai",
        0.6,
        r"\b(?:act|behave|respond|roleplay|role-play)\s+as\s+(?:an?\s+)?(?:different|new|unrestricted|uncensored|evil|unfiltered|other)?\s*(?:ai|assistant|chatbot|bot|model|gpt|character|persona|person)\b",
    ),
    _r("persona.pretend", 0.5, r"\bpretend\s+(?:to be|you(?:'re| are)|that you)\b"),
    _r(
        "persona.jailbreak_terms",
        0.7,
        r"\b(?:jailbreak|jailbroken|do anything now|developer mode|god mode|dan mode|unfiltered mode|no restrictions|without (?:any )?restrictions)\b",
    ),
    _r(
        "persona.no_filters",
        0.5,
        r"\b(?:without (?:any )?|no |remove (?:all |any |the |your )?|disable (?:all |any |the |your )?|turn off (?:all |the |your )?|lift (?:all |the )?)(?:filters?|restrictions?|limits?|limitations?|censorship|guardrails?|safety)\b",
    ),
    _r("persona.dan", 0.8, r"\bdan\b.{0,20}\b(?:mode|prompt|which stands)\b"),
    _r(
        "persona.id_berpura",
        0.6,
        r"\b(?:berpura-pura|berperan sebagai|bertindak sebagai)\b.{0,30}\b(?:ai|asisten|bot|model)\b",
    ),
    # --- Fake role / chat-template markers --------------------------------------------------
    _r(
        "marker.chat_template",
        1.0,
        r"<\|(?:im_start|im_end|system|user|assistant|endoftext|start_header_id|eot_id)\|>|\[/?inst\]|<</?sys>>",
    ),
    _r(
        "marker.role_header",
        1.0,
        r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:system|assistant|developer)\s*(?:message|prompt)?\s*:",
    ),
    _r(
        "marker.xml_role",
        0.7,
        r"</?\s*(?:system|instructions?|developer|assistant|visitor_message|passages?)\b[^>]*>",
    ),
    # --- Encoded / smuggled payloads ------------------------------------------------------------
    _r("payload.base64", 0.5, r"(?:[a-z0-9+/]{4}){12,}(?:[a-z0-9+/]{2}==|[a-z0-9+/]{3}=)?"),
    _r(
        "payload.decode",
        0.5,
        r"\b(?:decode|decrypt|base64|rot13|hex)\b.{0,30}\b(?:and|then)\b.{0,20}\b(?:follow|execute|run|do|obey)\b",
    ),
    # --- Tool / code execution attempts -------------------------------------------------------
    _r(
        "tools.execute",
        0.6,
        r"\b(?:execute|run|eval)\b.{0,20}\b(?:code|command|script|shell|sql|query|python)\b",
    ),
    _r(
        "tools.exfil",
        0.7,
        r"\b(?:send|post|upload|forward|exfiltrate)\b.{0,40}\b(?:to|into)\b.{0,20}(?:https?://|webhook|email|url)",
    ),
)
