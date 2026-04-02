from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.client import MPTClient, MPTExtensionAuth, get_installation_client
from app.config import settings
from app.schema import AuthContext as _AuthContext, ExtensionContext as _ExtensionContext
from app.utils import get_jwt_token_claims

security = HTTPBearer()


def _get_extension_context(request: Request) -> _ExtensionContext:
    return request.app.state.ctx


ExtensionContext = Annotated[_ExtensionContext, Depends(_get_extension_context)]


def _get_extension_client() -> MPTClient:
    return MPTClient(MPTExtensionAuth())


ExtensionClient = Annotated[MPTClient, Depends(_get_extension_client)]


async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ext_client: ExtensionClient,
) -> _AuthContext:
    token = credentials.credentials

    claims = get_jwt_token_claims(token)

    account_id = claims["https://claims.softwareone.com/accountId"]
    account_type = claims["https://claims.softwareone.com/accountType"]
    installation_id = claims.get("https://claims.softwareone.com/installationId")
    user_id = claims.get("https://claims.softwareone.com/userId")
    token_id = claims.get("https://claims.softwareone.com/apiTokenId")
    if not installation_id:
        query = f"and(eq(account.id,{account_id}),eq(status,Installed))"
        installation = await ext_client.first(
            f"/integration/extensions/{settings.extension_id}/installations",
            query=query,
        )
        if installation:
            installation_id = installation["id"]

    return _AuthContext(
        account_id=account_id,
        account_type=account_type,
        installation_id=installation_id,
        user_id=user_id,
        token_id=token_id,
    )


AuthContext = Annotated[_AuthContext, Depends(get_auth_context)]


def _get_installation_client(ctx: AuthContext) -> MPTClient:
    return get_installation_client(ctx.account_id)


InstallationClient = Annotated[MPTClient, Depends(_get_installation_client)]
