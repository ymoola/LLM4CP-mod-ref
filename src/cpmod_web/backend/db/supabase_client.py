from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from ..config import get_settings


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError('Supabase backend credentials are not configured.')
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
