"""Normalise untrusted text before screening it or showing it to a model.

Attackers hide instructions with invisible characters ("ig<zero-width space>nore"), full-width or
look-alike letters ("ｉｇｎｏｒｅ"), right-to-left overrides, or by padding with thousands of
repeated characters. NFKC folds compatibility characters, and the rest are stripped.
"""

from __future__ import annotations

import re
import unicodedata

# Zero-width, bidi controls/overrides/isolates, word joiners, BOM, soft hyphen, tag characters.
_INVISIBLE_RANGES = (
    (0x00AD, 0x00AD),  # soft hyphen
    (0x180E, 0x180E),  # Mongolian vowel separator
    (0x200B, 0x200F),  # zero-width space/joiners, LRM/RLM
    (0x202A, 0x202E),  # bidi embeddings and overrides ("Trojan Source")
    (0x2060, 0x2064),  # word joiner, invisible operators
    (0x2066, 0x2069),  # bidi isolates
    (0xFEFF, 0xFEFF),  # BOM / zero-width no-break space
    (0xE0000, 0xE007F),  # Unicode tag characters (invisible ASCII smuggling)
)
_INVISIBLE = re.compile("[" + "".join(f"\\U{a:08x}-\\U{b:08x}" for a, b in _INVISIBLE_RANGES) + "]")
# C0/C1 control characters except tab and newline.
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_MANY_SPACES = re.compile(r"[ \t]{3,}")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_REPEATS = re.compile(r"(.)\1{20,}", re.DOTALL)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = _REPEATS.sub(lambda m: m.group(1) * 3, text)
    text = _MANY_SPACES.sub("  ", text)
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def fold_for_matching(text: str) -> str:
    """Aggressive fold used only for pattern matching (never shown to anyone): lower-case,
    accents removed, common leetspeak undone, separators collapsed ("i.g.n.o.r.e" → "ignore")."""
    text = unicodedata.normalize("NFKD", normalize_text(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = text.translate(
        str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"})
    )
    # Collapse single characters separated by dots/dashes/underscores/spaces: "i g n o r e".
    text = re.sub(
        r"\b(?:\w[\s._\-*]){3,}\w\b", lambda m: re.sub(r"[\s._\-*]", "", m.group(0)), text
    )
    return re.sub(r"\s+", " ", text)
