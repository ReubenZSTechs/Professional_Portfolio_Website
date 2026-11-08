# ADR 0002: Python (FastAPI + LangGraph) backend, TypeScript (Next.js) frontend

**Status:** accepted · **Date:** 2026-11-08

## Context
The site showcases agentic-AI engineering, and Reuben's agent work is in Python and LangGraph. The frontend benefits from React, static generation and typed components.

## Decision
Next.js (TypeScript) at the repo root for pages. A FastAPI app (`backend/src`, entry `api/index.py`) for `/api/py/*`, deployed as a Vercel Python function in the same project. The contract between them is the SSE format in `docs/api.md`, mirrored by `src/lib/api.ts`.

## Consequences
- One repo, one deploy, one domain: no CORS in production.
- Two toolchains (npm + pip) and two test suites; CI runs both.
- The agent can also be self-hosted unchanged (`deploy/home_server`).
