from __future__ import annotations

import itertools

from rag.chunker import (
    CHARS_PER_TOKEN,
    chunk_document,
    clean_mdx,
    pack,
    split_sections,
)
from rag.models import SourceDocument

MDX = """import { Metric } from "@/components/mdx"
export const meta = { draft: false }

# Plantatio

Intro paragraph before any section.

## How it works

{/* editor note: never index this */}
<Pipeline steps={["Question", "Decompose", "Answer"]} highlight={2} />

<Decision title="Graph over vectors">
    Multi-hop questions need a graph.
</Decision>

```tsx
<Metric value="ignored" />
## not a heading
```

## Results

<Metrics>
  <Metric value="92%" label="Top-1 accuracy" />
  <Metric value={44} label="Tests" className="mt-4" />
</Metrics>

Scores pending. <Todo>Add the RAGAS scores.</Todo> p < 0.05 and x<y and z>w stay.

See <https://example.com> and <strong>bold</strong> text.
"""


def doc(text: str, title: str = "Plantatio") -> SourceDocument:
    return SourceDocument(
        source_type="project",
        source_id="project:plantatio",
        title=title,
        url="/projects/plantatio",
        text=text,
        metadata={"featured": True},
    )


class TestCleanMdx:
    def test_drops_imports_exports_and_comments(self):
        out = clean_mdx(MDX)
        assert "import" not in out.split("```")[0]
        assert "export const" not in out
        assert "editor note" not in out

    def test_keeps_component_props_as_text(self):
        out = clean_mdx(MDX)
        assert "Pipeline (steps: Question, Decompose, Answer)" in out
        assert "Metric (value: 92%; label: Top-1 accuracy)" in out
        assert "Metric (value: 44; label: Tests)" in out  # numeric expression, className dropped
        assert "Decision (title: Graph over vectors)" in out
        assert "highlight" not in out

    def test_children_text_kept_and_dedented(self):
        out = clean_mdx(MDX)
        assert "\nMulti-hop questions need a graph." in out

    def test_todo_placeholders_removed(self):
        assert "RAGAS" not in clean_mdx(MDX)
        assert "Scores pending." in clean_mdx(MDX)

    def test_prose_angle_brackets_and_autolinks_survive(self):
        out = clean_mdx(MDX)
        assert "p < 0.05 and x<y and z>w stay." in out
        assert "<https://example.com>" in out
        assert "<strong>" not in out and "bold text" in out

    def test_code_fences_untouched(self):
        out = clean_mdx(MDX)
        assert '<Metric value="ignored" />' in out
        assert "## not a heading" in out


class TestSplitSections:
    def test_heading_paths_and_title_h1(self):
        md = "# Doc\n\nintro\n\n## A\n\na body\n\n### A1\n\na1 body\n\n## B\n\nb body\n"
        sections = split_sections(md, title="Doc")
        assert [(s.label, s.body) for s in sections] == [
            (None, "intro"),
            ("A", "a body"),
            ("A > A1", "a1 body"),
            ("B", "b body"),
        ]

    def test_headings_inside_code_fences_are_ignored(self):
        md = "## Real\n\n```\n## fake\n```\n"
        sections = split_sections(md)
        assert len(sections) == 1
        assert "## fake" in sections[0].body

    def test_empty_sections_dropped(self):
        assert [s.label for s in split_sections("## Empty\n## Full\n\ntext")] == ["Full"]


class TestPack:
    def test_short_body_is_one_window(self):
        assert pack("short", 100, 10) == ["short"]

    def test_windows_respect_max_and_overlap(self):
        paragraphs = [f"Paragraph {i} " + "word " * 30 for i in range(12)]
        body = "\n\n".join(p.strip() for p in paragraphs)
        windows = pack(body, max_chars=500, overlap_chars=200)
        assert len(windows) > 1
        assert all(len(w) <= 500 for w in windows)
        # the last paragraph of each window is repeated at the start of the next one
        for prev, nxt in itertools.pairwise(windows):
            assert nxt.split("\n\n")[0] == prev.split("\n\n")[-1]
        # nothing lost
        for p in paragraphs:
            assert any(p.strip() in w for w in windows)

    def test_oversized_paragraph_split_by_sentences_then_words(self):
        body = " ".join(f"Sentence number {i} is here." for i in range(200))
        windows = pack(body, max_chars=300, overlap_chars=50)
        assert all(len(w) <= 300 for w in windows)
        assert "Sentence number 199 is here." in windows[-1]


class TestChunkDocument:
    def test_prefix_indices_and_metadata(self):
        chunks = chunk_document(doc(MDX))
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
        assert chunks[0].section is None
        assert chunks[0].content.startswith("Plantatio\n\nIntro paragraph")
        results = next(c for c in chunks if c.section == "Results")
        assert results.content.startswith("Plantatio — Results\n\n")
        assert all(c.metadata == {"featured": True} for c in chunks)
        assert all(c.url == "/projects/plantatio" for c in chunks)

    def test_long_section_becomes_several_chunks(self):
        body = "## Long\n\n" + "\n\n".join("lorem ipsum dolor sit amet " * 12 for _ in range(60))
        chunks = chunk_document(doc(body), max_tokens=200, overlap_tokens=20)
        assert len(chunks) > 3
        header = "Plantatio — Long\n\n"
        assert all(c.content.startswith(header) for c in chunks)
        assert all(len(c.content) - len(header) <= 200 * CHARS_PER_TOKEN for c in chunks)

    def test_hash_depends_on_model_and_dim(self):
        chunk = chunk_document(doc("text"))[0]
        h = chunk.hash("gemini-embedding-001", 768)
        assert h == chunk.hash("gemini-embedding-001", 768)
        assert h != chunk.hash("gemini-embedding-001", 1536)
        assert h != chunk.hash("other-model", 768)
