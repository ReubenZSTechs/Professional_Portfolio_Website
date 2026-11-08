# ADR 0004: Content as files (YAML + MDX) instead of a CMS

**Status:** accepted · **Date:** 2026-11-08

## Context
Reuben wants to edit text, pin projects and reorder sections without touching code. A hosted CMS adds an account, an API and a sync step between the CMS and the RAG index.

## Decision
All content lives in `content/` as YAML and MDX, validated by zod schemas at build time. The homepage is assembled from `content/home.yaml` through a section registry. Pushing to `main` redeploys the site (Vercel) and re-indexes the chatbot (GitHub Actions), so the site and the chatbot never disagree.

## Consequences
- Every change is versioned and reviewable; previews come free on branches.
- Editing needs git (or GitHub's web editor). If browser-based editing is wanted later, a git-backed editor such as Keystatic can sit on the same files.
- Invalid content fails the build instead of shipping a broken page.
