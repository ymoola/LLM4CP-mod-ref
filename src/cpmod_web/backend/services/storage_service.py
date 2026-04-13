from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..db.supabase_client import get_supabase_admin


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_supabase_admin()

    def upload_bytes(self, *, bucket: str, path: str, content: bytes, content_type: str) -> str:
        self.client.storage.from_(bucket).upload(
            path,
            content,
            file_options={'content-type': content_type, 'upsert': 'true'},
        )
        return path

    def upload_text(self, *, bucket: str, path: str, content: str, content_type: str = 'text/plain') -> str:
        return self.upload_bytes(bucket=bucket, path=path, content=content.encode('utf-8'), content_type=content_type)

    def upload_json(self, *, bucket: str, path: str, payload: dict[str, Any]) -> str:
        return self.upload_text(bucket=bucket, path=path, content=json.dumps(payload, indent=2), content_type='application/json')

    def download_text(self, *, bucket: str, path: str) -> str:
        data = self.client.storage.from_(bucket).download(path)
        return data.decode('utf-8') if isinstance(data, (bytes, bytearray)) else str(data)

    def create_signed_url(self, *, bucket: str, path: str, expires_in: int = 3600) -> str | None:
        try:
            response = self.client.storage.from_(bucket).create_signed_url(path, expires_in)
            if isinstance(response, dict):
                return response.get('signedURL') or response.get('signed_url')
            return getattr(response, 'get', lambda *_: None)('signedURL')
        except Exception:
            return None

    def delete_paths(self, *, bucket: str, paths: list[str]) -> None:
        clean_paths = [path for path in paths if path]
        if not clean_paths:
            return
        try:
            self.client.storage.from_(bucket).remove(clean_paths)
        except Exception:
            # Best-effort cleanup only; DB state should still be allowed to proceed.
            return
