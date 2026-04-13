from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from ..config import get_settings
from .model_catalog import LLMProvider, list_supported_providers


class CredentialError(RuntimeError):
    pass


class CredentialService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.credential_encryption_secret:
            raise CredentialError('CPMOD_WEB_CREDENTIAL_ENCRYPTION_SECRET is not configured.')
        digest = hashlib.sha256(settings.credential_encryption_secret.encode('utf-8')).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, api_key: str) -> str:
        if not api_key.strip():
            raise CredentialError('API key cannot be empty.')
        return self._fernet.encrypt(api_key.strip().encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_api_key: str) -> str:
        try:
            return self._fernet.decrypt(encrypted_api_key.encode('utf-8')).decode('utf-8')
        except Exception as exc:  # pragma: no cover - defensive, environment-dependent
            raise CredentialError('Unable to decrypt stored provider key.') from exc


def supported_provider(provider: str) -> LLMProvider:
    normalized = provider.strip().lower()
    if normalized not in set(list_supported_providers()):
        raise CredentialError(f'Unsupported provider: {provider!r}.')
    return normalized  # type: ignore[return-value]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
