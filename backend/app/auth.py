from typing import Annotated

import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.schema import AuthContext as _AuthContext
from app.utils import get_jwt_token_claims



security = HTTPBearer()


async def resolve_installation(account_id: str) -> str:
    query = f"and(eq(account.id,{account_id}),eq(status,Installed))"
    url = f"integration/extensions/{settings.extension_id}/installations?{query}"
    response = httpx.get(
        f"{settings.base_url}/{url}",
        headers={"Authorization": f"Bearer {settings.api_key}"}
    )
    response.raise_for_status()
    data = response.json()
    return data["data"][0]["id"]



async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> _AuthContext:

    token = credentials.credentials

    claims = get_jwt_token_claims(token)

    account_id = claims["https://claims.softwareone.com/accountId"]
    account_type = claims["https://claims.softwareone.com/accountType"]
    installation_id = claims.get("https://claims.softwareone.com/installationId")
    user_id = claims.get("https://claims.softwareone.com/userId")
    token_id = claims.get("https://claims.softwareone.com/apiTokenId")
    if not installation_id:
        installation_id = await resolve_installation(account_id)

    return _AuthContext(
        account_id=account_id,
        account_type=account_type,
        installation_id=installation_id,
        user_id=user_id,
        token_id=token_id,
    )


AuthContext = Annotated[_AuthContext, Depends(get_auth_context)]
