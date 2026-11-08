"""Supabase reads/writes on public.documents used by ingestion."""

from __future__ import annotations

from typing import Any

from supabase import Client

from rag.sync import INDEX_COLUMNS

PAGE_SIZE = 1000  # PostgREST's default max rows per request
WRITE_BATCH = 100


def fetch_index(client: Client) -> list[dict[str, Any]]:
    """Every chunk's key, hash and patchable columns (no embeddings)."""
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        page = (
            client.table("documents")
            .select(INDEX_COLUMNS)
            .order("source_id")
            .order("chunk_index")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def upsert_rows(client: Client, rows: list[dict[str, Any]]) -> None:
    for i in range(0, len(rows), WRITE_BATCH):
        client.table("documents").upsert(
            rows[i : i + WRITE_BATCH], on_conflict="source_id,chunk_index"
        ).execute()


def patch_rows(client: Client, patches: list[tuple[str, dict[str, Any]]]) -> None:
    for row_id, fields in patches:
        client.table("documents").update(fields).eq("id", row_id).execute()


def delete_ids(client: Client, ids: list[str]) -> None:
    for i in range(0, len(ids), WRITE_BATCH):
        client.table("documents").delete().in_("id", ids[i : i + WRITE_BATCH]).execute()
