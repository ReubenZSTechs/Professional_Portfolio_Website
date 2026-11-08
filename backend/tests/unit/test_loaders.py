from __future__ import annotations

from pathlib import Path

import pytest

from rag.loaders import load_all, load_projects, load_yaml_sources

PROJECT = """---
title: Plantatio
slug: plantatio
summary: GraphRAG over an agronomy knowledge graph.
role: "TODO: solo or team?"
stack: [Python, Neo4j]
featured: true
order: 3
---

## The problem

Growers can't read papers.
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    projects = tmp_path / "content" / "projects"
    projects.mkdir(parents=True)
    (projects / "plantatio.mdx").write_text(PROJECT)
    (projects / "_template.mdx").write_text("---\ntitle: Template\n---\nignore me")
    (projects / "draft.mdx").write_text("---\ntitle: Draft\ndraft: true\n---\nhidden")
    content = tmp_path / "content"
    (content / "experience.yaml").write_text(
        "- company: FlyRank AI\n  role: Backend AI Engineer\n  start: Jun 2026\n"
        "  bullets:\n    - Built agents.\n    - Cut token cost by 15%.\n"
    )
    (content / "awards.yaml").write_text(
        "- { title: Rector's List, issuer: CIT, year: '2025' }\n"
        "- { title: Rector's List, issuer: CIT, year: '2024' }\n"
    )
    (content / "skills.yaml").write_text("languages: [Python, SQL]\nframeworks: [FastAPI]\n")
    (content / "certifications.yaml").write_text("[]\n")
    (content / "site.yaml").write_text("name: not indexed\n")
    knowledge = tmp_path / "knowledge" / "projects"
    knowledge.mkdir(parents=True)
    (knowledge / "sigap.md").write_text("# SIGAP notes\n\nExtra facts.\n")
    (tmp_path / "knowledge" / "empty.md").write_text("")
    return tmp_path


def test_projects(repo: Path):
    [doc] = load_projects(repo / "content" / "projects")
    assert doc.source_id == "project:plantatio"
    assert doc.url == "/projects/plantatio"
    assert doc.metadata["featured"] is True and doc.metadata["order"] == 3
    assert doc.text.startswith("## At a glance\n\nSummary: GraphRAG")
    assert "Stack: Python, Neo4j" in doc.text
    assert "TODO" not in doc.text  # placeholder frontmatter values are not indexed


def test_yaml_entries(repo: Path):
    docs = {d.source_id: d for d in load_yaml_sources(repo / "content")}
    exp = docs["experience:backend-ai-engineer-flyrank-ai"]
    assert exp.title == "Backend AI Engineer — FlyRank AI"
    assert exp.url == "/#experience"
    assert "- Cut token cost by 15%." in exp.text
    # same title twice -> stable ids disambiguated by year
    assert "awards:rector-s-list-cit" in docs and "awards:rector-s-list-cit-2024" in docs
    # dict of lists -> one entry per group
    assert docs["skills:languages"].text.endswith("Languages: Python, SQL")
    # missing/empty files and non-RAG files are skipped
    assert not any(k.startswith(("certifications:", "site:", "research:")) for k in docs)


def test_load_all_includes_knowledge(repo: Path):
    docs = load_all(repo / "content", repo / "knowledge")
    ids = {d.source_id for d in docs}
    assert "knowledge:projects/sigap" in ids
    assert not any(i.startswith("knowledge:empty") for i in ids)
    sigap = next(d for d in docs if d.source_id == "knowledge:projects/sigap")
    assert sigap.title == "SIGAP notes"


def test_missing_dirs_are_fine(tmp_path: Path):
    assert load_all(tmp_path / "content", tmp_path / "knowledge") == []
