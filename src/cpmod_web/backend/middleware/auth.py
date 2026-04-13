from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from ..db.supabase_client import get_supabase_admin


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None = None


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing Authorization header.')
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid bearer token.')
    return token


def get_current_user(authorization: str | None = Header(default=None)) -> AuthenticatedUser:
    token = _extract_bearer_token(authorization)
    client = get_supabase_admin()
    response = client.auth.get_user(token)
    user = getattr(response, 'user', None)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unable to authenticate user.')
    return AuthenticatedUser(id=str(user.id), email=getattr(user, 'email', None))
