from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from ..db import queries
from ..middleware.auth import AuthenticatedUser, get_current_user
from ..models.api import ModelCatalogEntryRead, ProviderCredentialStatusRead
from ..services.credential_service import CredentialError, CredentialService, supported_provider, utcnow_iso
from ..services.model_catalog import list_model_catalog_payload

router = APIRouter(prefix='/settings', tags=['settings'])


class ProviderCredentialUpsert(BaseModel):
    api_key: str


@router.get('/model-catalog', response_model=list[ModelCatalogEntryRead])
def get_model_catalog(current_user: AuthenticatedUser = Depends(get_current_user)):
    del current_user
    return list_model_catalog_payload()


@router.get('/credentials', response_model=list[ProviderCredentialStatusRead])
def list_credentials(current_user: AuthenticatedUser = Depends(get_current_user)):
    stored = {item['provider']: item for item in queries.list_user_api_credentials(user_id=current_user.id)}
    response: list[dict[str, object]] = []
    for provider in sorted({entry['provider'] for entry in list_model_catalog_payload()}):
        row = stored.get(provider)
        response.append(
            {
                'provider': provider,
                'has_key': bool(row),
                'updated_at': row.get('updated_at') if row else None,
            }
        )
    return response


@router.put('/credentials/{provider}', response_model=ProviderCredentialStatusRead)
def save_credential(provider: str, payload: ProviderCredentialUpsert, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        normalized_provider = supported_provider(provider)
        encrypted_api_key = CredentialService().encrypt(payload.api_key)
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record = queries.upsert_user_api_credential(
        {
            'user_id': current_user.id,
            'provider': normalized_provider,
            'encrypted_api_key': encrypted_api_key,
            'updated_at': utcnow_iso(),
        }
    )
    return {
        'provider': normalized_provider,
        'has_key': True,
        'updated_at': record.get('updated_at'),
    }


@router.delete('/credentials/{provider}', status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(provider: str, current_user: AuthenticatedUser = Depends(get_current_user)):
    try:
        normalized_provider = supported_provider(provider)
    except CredentialError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    queries.delete_user_api_credential(user_id=current_user.id, provider=normalized_provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
