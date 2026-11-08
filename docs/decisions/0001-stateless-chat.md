# ADR 0001: Stateless chat, history sent by the browser

**Status:** accepted · **Date:** 2026-11-08

## Context
The API runs as Vercel serverless functions. Instances don't share memory and are recycled at any time, so an in-memory LangGraph checkpointer would lose conversations. A Postgres checkpointer would work but adds a table, cleanup jobs, and a session id to manage, for conversations that last a few minutes.

## Decision
The browser keeps the conversation and sends the last ≤10 exchanges with every question. The server stores nothing about the chat. `compile_history` trims long histories and summarises older turns, so the prompt stays small.

## Consequences
- No session storage, no cleanup, no privacy questions about stored chats.
- A refresh clears the conversation (acceptable for a portfolio).
- The client controls history, so the server clips and validates it (length, roles) and treats it as untrusted input.
