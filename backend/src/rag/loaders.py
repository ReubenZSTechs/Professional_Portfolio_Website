"""Turn the repo's editable content into SourceDocuments for chunking.

Sources:
  content/projects/*.mdx   one document per project (files starting with "_" are skipped)
  content/<name>.yaml      one document per entry, for the names in YAML_SOURCES (missing = skipped)
  knowledge/**/*.md        one document per file (RAG-only facts, not rendered on the site)

The YAML renderer is schema-agnostic on purpose: the site's zod schemas own the exact shape,
and this only needs readable "Key: value" text for embedding.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from core.logging import get_logger
from rag.models import SourceDocument

log = get_logger(__name__)

YAML_SOURCES = (
    "experience",
    "research",
    "awards",
    "skills",
    "education",
    "certifications",
    "leadership",
    "teaching",
    "languages",
)
# Frontmatter fields rendered into a project's "At a glance" section, in this order.
PROJECT_GLANCE_FIELDS = (
    "summary", "highlight", "role", "timeline", "status", "category", "series",
    "stack", "tags", "repo", "demo",
)  # fmt: skip
_TITLE_KEYS = ("title", "name", "role", "position", "degree", "field", "group", "award", "label")
_SUBTITLE_KEYS = ("company", "organization", "org", "institution", "issuer", "venue", "school")
# Presentational / ordering keys that mean nothing to a reader.
_SKIP_KEYS = frozenset(
    {"id", "slug", "order", "icon", "logo", "image", "cover", "color", "hidden", "featured"}
)


# --------------------------------------------------------------------------- helpers
def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "item"


_ACRONYMS = {"gpa": "GPA", "url": "URL", "ai": "AI", "llm": "LLM", "ml": "ML", "cv": "CV"}


def humanize(key: str) -> str:
    words = re.sub(r"[_\-]+", " ", re.sub(r"(?<=[a-z])(?=[A-Z])", " ", key)).split()
    words = [_ACRONYMS.get(w.lower(), w) for w in words]
    text = " ".join(words)
    return text[:1].upper() + text[1:]


def json_safe(value: Any) -> Any:
    """Frontmatter/YAML can contain dates; jsonb wants plain JSON."""
    return json.loads(json.dumps(value, default=str))


def is_placeholder(value: Any) -> bool:
    """`TODO: ...` values are dev-only placeholders (the site hides them); never index them."""
    return isinstance(value, str) and value.strip().upper().startswith("TODO")


def _scalar(value: Any) -> bool:
    return (
        value is None or isinstance(value, str | int | float | bool) or hasattr(value, "isoformat")
    )


def _fmt_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value).strip()


def _inline(values: list[Any]) -> bool:
    """Short tag-like lists render on one line; sentence lists (bullets) as "- " lines."""
    return all(
        _scalar(v) and len(_fmt_scalar(v)) <= 40 and not _fmt_scalar(v).endswith(".")
        for v in values
    )


def render_value(value: Any, indent: int = 0) -> list[str]:
    """Readable lines for arbitrary YAML data."""
    pad = "  " * indent
    if is_placeholder(value):
        return []
    if _scalar(value):
        text = _fmt_scalar(value)
        return [f"{pad}{line}" for line in text.splitlines()] if text else []
    if isinstance(value, list):
        value = [v for v in value if not is_placeholder(v)]
        if _inline(value):
            joined = ", ".join(_fmt_scalar(v) for v in value if _fmt_scalar(v))
            return [f"{pad}{joined}"] if joined else []
        lines: list[str] = []
        for item in value:
            sub = render_value(item, indent + 1)
            if sub:
                lines.append(f"{pad}- {sub[0].strip()}")
                lines.extend(sub[1:])
        return lines
    if isinstance(value, dict):
        lines = []
        for key, sub_value in value.items():
            if (
                str(key) in _SKIP_KEYS
                or sub_value in (None, "", [], {})
                or is_placeholder(sub_value)
            ):
                continue
            label = humanize(str(key))
            if _scalar(sub_value) and "\n" not in _fmt_scalar(sub_value):
                lines.append(f"{pad}{label}: {_fmt_scalar(sub_value)}")
            elif isinstance(sub_value, list) and _inline(sub_value):
                rendered = render_value(sub_value)
                if rendered:
                    lines.append(f"{pad}{label}: {rendered[0].strip()}")
            else:
                lines.append(f"{pad}{label}:")
                lines.extend(render_value(sub_value, indent + 1))
        return lines
    return [f"{pad}{value}"]


def _entry_title(entry: Any, fallback: str) -> str:
    if not isinstance(entry, dict):
        return _fmt_scalar(entry) if _scalar(entry) else fallback

    def first(keys: tuple[str, ...]) -> str | None:
        return next(
            (
                str(entry[k])
                for k in keys
                if isinstance(entry.get(k), str) and not is_placeholder(entry[k])
            ),
            None,
        )

    title, subtitle = first(_TITLE_KEYS), first(_SUBTITLE_KEYS)
    if title and subtitle and subtitle != title:
        return f"{title} — {subtitle}"
    return title or subtitle or fallback


def _yaml_entries(data: Any, stem: str) -> list[tuple[str | None, Any]]:
    """(title override, entry) pairs from a YAML file's top level."""
    if isinstance(data, list):
        return [(None, item) for item in data]
    if isinstance(data, dict):
        for key in ("items", "entries", stem):
            if isinstance(data.get(key), list):
                return [(None, item) for item in data[key]]
        if data and all(isinstance(v, list | dict) for v in data.values()):
            # e.g. skills.yaml: {languages: [...], frameworks: [...]} -> one entry per group
            return [(humanize(str(k)), v) for k, v in data.items()]
        return [(None, data)]
    return []


# --------------------------------------------------------------------------- loaders
def load_projects(projects_dir: Path) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    if not projects_dir.is_dir():
        log.info("no projects directory", extra={"path": str(projects_dir)})
        return docs
    for path in sorted(projects_dir.glob("*.mdx")):
        if path.name.startswith("_"):
            continue  # _template.mdx and other partials
        post = frontmatter.load(path)
        meta = json_safe(dict(post.metadata))
        if meta.get("draft"):
            continue
        slug = str(meta.get("slug") or path.stem)
        title = str(meta.get("title") or humanize(slug))
        glance = []
        for key in PROJECT_GLANCE_FIELDS:
            value = meta.get(key)
            if value in (None, "", []) or is_placeholder(value):
                continue
            rendered = render_value(value)
            if rendered:
                glance.append(f"{humanize(key)}: {' '.join(line.strip() for line in rendered)}")
        text = post.content
        if glance:
            text = "## At a glance\n\n" + "\n".join(glance) + "\n\n" + text
        docs.append(
            SourceDocument(
                source_type="project",
                source_id=f"project:{slug}",
                title=title,
                url=f"/projects/{slug}",
                text=text,
                metadata={**meta, "slug": slug, "file": f"content/projects/{path.name}"},
            )
        )
    return docs


def load_yaml_sources(
    content_dir: Path, names: Iterable[str] = YAML_SOURCES
) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    for stem in names:
        candidates = (content_dir / f"{stem}.yaml", content_dir / f"{stem}.yml")
        path = next((p for p in candidates if p.is_file()), None)
        if path is None:
            log.info("yaml source missing, skipped", extra={"source": stem})
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        used: set[str] = set()
        for index, (title_override, entry) in enumerate(_yaml_entries(data, stem)):
            if isinstance(entry, dict) and entry.get("hidden"):
                continue
            title = title_override or _entry_title(entry, f"{humanize(stem)} {index + 1}")
            fields = entry if isinstance(entry, dict) else {}
            key = slugify(str(fields.get("id") or fields.get("slug") or title))
            if key in used:  # same title twice (e.g. Rector's List 2024/2025): add the year
                when = next((fields[k] for k in ("year", "date", "start") if fields.get(k)), None)
                key = f"{key}-{slugify(str(when))}" if when else key
            while key in used:  # last resort: position (stable unless entries are reordered)
                key = f"{key}-{index}"
            used.add(key)
            body = render_value(entry if title_override is None else {title_override: entry})
            if not body:
                continue
            scalars = (
                {k: v for k, v in entry.items() if _scalar(v) and k not in _SKIP_KEYS}
                if isinstance(entry, dict)
                else {}
            )
            docs.append(
                SourceDocument(
                    source_type=stem,
                    source_id=f"{stem}:{key}",
                    title=title,
                    url=f"/#{stem}",
                    text=f"Category: {humanize(stem)}\n\n" + "\n".join(body),
                    metadata=json_safe({**scalars, "file": f"content/{path.name}"}),
                )
            )
    return docs


def load_knowledge(knowledge_dir: Path) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    if not knowledge_dir.is_dir():
        return docs
    for path in sorted(knowledge_dir.rglob("*.md")):
        post = frontmatter.load(path)
        if not post.content.strip():
            continue
        rel = path.relative_to(knowledge_dir).with_suffix("").as_posix()
        h1 = re.search(r"^#\s+(.+?)\s*$", post.content, re.MULTILINE)
        title = str(post.metadata.get("title") or (h1.group(1) if h1 else humanize(path.stem)))
        docs.append(
            SourceDocument(
                source_type="knowledge",
                source_id=f"knowledge:{rel}",
                title=title,
                url=post.metadata.get("url"),
                text=post.content,
                metadata=json_safe(
                    {**dict(post.metadata), "file": f"knowledge/{rel}{path.suffix}"}
                ),
            )
        )
    return docs


def load_all(content_dir: Path, knowledge_dir: Path) -> list[SourceDocument]:
    docs = [
        *load_projects(content_dir / "projects"),
        *load_yaml_sources(content_dir),
        *load_knowledge(knowledge_dir),
    ]
    ids = [d.source_id for d in docs]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError(f"duplicate source ids: {dupes}")
    return docs
