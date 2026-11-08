"""Lazy Supabase client using the service-role key (server-only; bypasses RLS)."""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from core.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(
        settings.require("supabase_url"),
        settings.require("supabase_service_role_key"),
    )
