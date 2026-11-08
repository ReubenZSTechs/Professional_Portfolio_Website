"""Markdown / MDX chunker.

Pipeline for one SourceDocument:
  1. `clean_mdx`: drop import/export lines and comments, drop <Todo> placeholders, and turn JSX
     components into plain text that keeps their props (so `<Metric value="92%" label="Top-1" />`
     becomes `Metric (value: 92%; label: Top-1)`). Fenced code blocks are left untouched.
  2. `split_sections`: split on markdown headings, tracking the heading path ("A > B").
  3. Each section body is packed into windows of ~max_tokens with a small overlap
     (paragraph-aligned; long paragraphs fall back to sentences, then words).
  4. Every chunk is prefixed with "Title — Section" so it is self-describing when embedded and
     when shown to the answering model.

Token counts are estimated at ~4 characters per token, which is close enough for English prose
and keeps this module dependency-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag.models import Chunk, SourceDocument

CHARS_PER_TOKEN = 4
DEFAULT_MAX_TOKENS = 800
DEFAULT_OVERLAP_TOKENS = 80

# Props that are presentational or point at assets; they add noise to embeddings.
IGNORED_PROPS = frozenset(
    {
        "as", "class", "className", "color", "height", "highlight", "href", "icon", "id", "key",
        "priority", "size", "src", "style", "target", "tone", "variant", "width",
    }
)  # fmt: skip
# Lowercase names treated as HTML tags (anything else after "<" is prose, e.g. "a<b and c>d").
HTML_TAGS = frozenset(
    {
        "a", "abbr", "b", "blockquote", "br", "code", "del", "details", "div", "em", "figcaption",
        "figure", "hr", "i", "img", "kbd", "li", "mark", "ol", "p", "pre", "s", "small", "span",
        "strong", "sub", "summary", "sup", "table", "tbody", "td", "th", "thead", "tr", "u", "ul",
    }
)  # fmt: skip
# Components whose content must never be indexed (dev-only "fill this in" placeholders).
DROPPED_COMPONENTS = frozenset({"Todo"})

_FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_TAG_NAME_RE = re.compile(r"[A-Za-z][\w.\-]*")
_IMPORT_EXPORT_RE = re.compile(r"^(?:import|export)\s.*$", re.MULTILINE)
_JSX_COMMENT_RE = re.compile(r"\{/\*.*?\*/\}", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_STRING_LITERAL_RE = re.compile(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`([^`]*)`')
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?%?")
_LIST_ITEM_RE = re.compile(r"(?:[-*+]|\d+[.)])\s")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    return -(-len(text) // CHARS_PER_TOKEN)


# --------------------------------------------------------------------------- fences
def _split_fences(text: str) -> list[tuple[bool, str]]:
    """Split text into (is_code, segment) runs so code blocks are never rewritten."""
    segments: list[tuple[bool, str]] = []
    buf: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        match = _FENCE_RE.match(line)
        if fence is None and match:
            if buf:
                segments.append((False, "".join(buf)))
            buf, fence = [line], match.group(2)[0] * len(match.group(2))
        elif fence is not None and match and match.group(2).startswith(fence):
            buf.append(line)
            segments.append((True, "".join(buf)))
            buf, fence = [], None
        else:
            buf.append(line)
    if buf:
        segments.append((fence is not None, "".join(buf)))
    return segments


# --------------------------------------------------------------------------- JSX
@dataclass
class _Tag:
    name: str
    props: list[tuple[str, str]]
    closing: bool
    self_closing: bool
    end: int  # index just past '>'


def _scan_balanced(text: str, start: int) -> int:
    """`text[start]` is '{'; return the index just past its matching '}' (or -1)."""
    depth, i, quote = 0, start, None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'`":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _brace_value(expr: str) -> str | None:
    """Readable text from a JSX expression prop: its string literals, or a bare number."""
    inner = expr.strip()[1:-1].strip()
    literals = []
    for match in _STRING_LITERAL_RE.finditer(inner):
        literal = next(g for g in match.groups() if g is not None).strip()
        if literal:
            literals.append(literal)
    if literals:
        return ", ".join(literals)
    if _NUMBER_RE.fullmatch(inner):
        return inner
    return None  # identifiers, booleans, arrow functions: nothing worth embedding


def _parse_tag(text: str, start: int) -> _Tag | None:
    """Parse a JSX/HTML tag starting at text[start] == '<'. None if it isn't one."""
    i = start + 1
    closing = i < len(text) and text[i] == "/"
    if closing:
        i += 1
    name_match = _TAG_NAME_RE.match(text, i)
    if not name_match:
        return None
    name = name_match.group(0)
    if not name[0].isupper() and name.lower() not in HTML_TAGS:
        return None
    i = name_match.end()
    if i >= len(text) or text[i] not in " \t\r\n/>":
        return None  # e.g. an autolink <https://...>

    props: list[tuple[str, str]] = []
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch == ">":
            return _Tag(name, props, closing, False, i + 1)
        elif ch == "/" and text.startswith("/>", i):
            return _Tag(name, props, closing, True, i + 2)
        elif ch == "{":  # spread props {...rest}
            end = _scan_balanced(text, i)
            if end < 0:
                return None
            i = end
        else:
            attr = re.match(r"[^\s=/>{]+", text[i:])
            if not attr:
                return None
            key = attr.group(0)
            i += len(key)
            if i < len(text) and text[i] == "=":
                i += 1
                if i < len(text) and text[i] in "\"'":
                    quote = text[i]
                    end = text.find(quote, i + 1)
                    if end < 0:
                        return None
                    props.append((key, text[i + 1 : end]))
                    i = end + 1
                elif i < len(text) and text[i] == "{":
                    end = _scan_balanced(text, i)
                    if end < 0:
                        return None
                    value = _brace_value(text[i:end])
                    if value is not None:
                        props.append((key, value))
                    i = end
                else:
                    return None
            # bare boolean props (e.g. `featured`) carry no text
    return None


def _render_component(tag: _Tag) -> str:
    shown = [(k, " ".join(v.split())) for k, v in tag.props if k not in IGNORED_PROPS and v.strip()]
    if not shown:
        return "\n"
    return "\n" + f"{tag.name} (" + "; ".join(f"{k}: {v}" for k, v in shown) + ")\n"


def _strip_jsx(text: str) -> str:
    out: list[str] = []
    i = 0
    drop_depth = 0  # >0 while inside a DROPPED_COMPONENTS element
    while i < len(text):
        lt = text.find("<", i)
        if lt < 0:
            if not drop_depth:
                out.append(text[i:])
            break
        if not drop_depth:
            out.append(text[i:lt])
        tag = _parse_tag(text, lt)
        if tag is None:
            if not drop_depth:
                out.append("<")
            i = lt + 1
            continue
        i = tag.end
        if tag.name in DROPPED_COMPONENTS:
            if not tag.self_closing:
                drop_depth += -1 if tag.closing else 1
                drop_depth = max(drop_depth, 0)
            continue
        if drop_depth:
            continue
        if tag.name[0].isupper():  # React component
            out.append("\n" if tag.closing else _render_component(tag))
        elif tag.name.lower() == "br":
            out.append("\n")
        # other lowercase HTML tags: drop the tag, keep the text between them
    return "".join(out)


def _dedent_line(line: str) -> str:
    """Children of JSX blocks are indented in MDX source; un-indent them so they don't read as
    markdown code blocks. Nested list items keep their indentation."""
    stripped = line.strip()
    return line.rstrip() if _LIST_ITEM_RE.match(stripped) else stripped


def clean_mdx(text: str) -> str:
    """MDX/markdown -> plain markdown that is safe and meaningful to embed."""
    parts: list[str] = []
    for is_code, segment in _split_fences(text):
        if is_code:
            parts.append(segment)
            continue
        segment = _IMPORT_EXPORT_RE.sub("", segment)
        segment = _JSX_COMMENT_RE.sub("", segment)
        segment = _HTML_COMMENT_RE.sub("", segment)
        segment = _strip_jsx(segment)
        segment = "\n".join(_dedent_line(line) for line in segment.split("\n"))
        parts.append(segment)
    return re.sub(r"\n{3,}", "\n\n", "".join(parts)).strip()


# --------------------------------------------------------------------------- sections
@dataclass
class Section:
    path: list[str]
    body: str

    @property
    def label(self) -> str | None:
        return " > ".join(self.path) or None


def split_sections(markdown: str, title: str | None = None) -> list[Section]:
    """Split on headings (outside code fences). A level-1 heading equal to the document title
    is treated as the title, not as a section."""
    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    buf: list[str] = []

    def flush() -> None:
        body = "\n".join(buf).strip()
        if body:
            sections.append(Section([h for _, h in stack], body))
        buf.clear()

    for is_code, segment in _split_fences(markdown):
        if is_code:
            buf.append(segment.rstrip("\n"))
            continue
        for line in segment.split("\n"):
            match = _HEADING_RE.match(line)
            if not match:
                buf.append(line)
                continue
            flush()
            level, heading = len(match.group(1)), match.group(2).strip()
            if level == 1 and title and heading.casefold() == title.casefold():
                stack.clear()
                continue
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
    flush()
    return sections


# --------------------------------------------------------------------------- packing
def _paragraphs(body: str) -> list[str]:
    """Blank-line separated blocks, keeping fenced code blocks whole."""
    units: list[str] = []
    for is_code, segment in _split_fences(body):
        if is_code:
            units.append(segment.strip("\n"))
        else:
            units.extend(p.strip() for p in re.split(r"\n\s*\n", segment) if p.strip())
    return units


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Split one oversized unit into sentences, then word runs, each <= max_chars."""
    pieces: list[str] = []
    for sentence in _SENTENCE_RE.split(text):
        if len(sentence) <= max_chars:
            pieces.append(sentence)
            continue
        words, cur = sentence.split(" "), ""
        for word in words:
            while len(word) > max_chars:  # pathological: a giant token (URL, base64)
                if cur:
                    pieces.append(cur)
                    cur = ""
                pieces.append(word[:max_chars])
                word = word[max_chars:]
            candidate = f"{cur} {word}" if cur else word
            if len(candidate) > max_chars:
                pieces.append(cur)
                cur = word
            else:
                cur = candidate
        if cur:
            pieces.append(cur)
    # Re-pack sentences so we don't emit one tiny unit per sentence.
    packed: list[str] = []
    for piece in pieces:
        if packed and len(packed[-1]) + 1 + len(piece) <= max_chars:
            packed[-1] = f"{packed[-1]} {piece}"
        else:
            packed.append(piece)
    return packed


def _overlap_tail(units: list[str], overlap_chars: int, room: int) -> list[str]:
    """The trailing units of a finished window to repeat at the start of the next one."""
    budget = min(overlap_chars, room)
    if budget <= 0:
        return []
    tail: list[str] = []
    size = 0
    for unit in reversed(units):
        add = len(unit) + (2 if tail else 0)
        if size + add > budget:
            break
        tail.insert(0, unit)
        size += add
    if tail and len(tail) < len(units):
        return tail
    if tail:  # whole window fits in the overlap budget: repeating it all adds nothing
        return []
    # Last unit is longer than the budget: carry its last ~budget chars from a word boundary.
    last = units[-1]
    cut = last[-budget:]
    space = cut.find(" ")
    cut = cut[space + 1 :] if 0 <= space < len(cut) - 1 else cut
    return [f"…{cut}"] if cut else []


def pack(body: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Greedy paragraph packing into windows of <= max_chars with ~overlap_chars of overlap."""
    if len(body) <= max_chars:
        return [body]
    units: list[str] = []
    for paragraph in _paragraphs(body):
        units.extend(
            [paragraph] if len(paragraph) <= max_chars else _hard_split(paragraph, max_chars)
        )

    windows: list[list[str]] = []
    cur: list[str] = []
    cur_len = 0
    for unit in units:
        sep = 2 if cur else 0
        if cur and cur_len + sep + len(unit) > max_chars:
            windows.append(cur)
            cur = _overlap_tail(cur, overlap_chars, room=max_chars - len(unit) - 2)
            cur_len = len("\n\n".join(cur))
            sep = 2 if cur else 0
        cur.append(unit)
        cur_len += sep + len(unit)
    if cur:
        windows.append(cur)
    return ["\n\n".join(w) for w in windows]


# --------------------------------------------------------------------------- public API
def chunk_document(
    doc: SourceDocument,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap_tokens must be smaller than max_tokens")
    max_chars = max_tokens * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    chunks: list[Chunk] = []
    for section in split_sections(clean_mdx(doc.text), title=doc.title):
        header = f"{doc.title} — {section.label}" if section.label else doc.title
        for window in pack(section.body, max_chars, overlap_chars):
            chunks.append(
                Chunk(
                    source_type=doc.source_type,
                    source_id=doc.source_id,
                    title=doc.title,
                    url=doc.url,
                    section=section.label,
                    chunk_index=len(chunks),
                    content=f"{header}\n\n{window}",
                    metadata=dict(doc.metadata),
                )
            )
    return chunks
