from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from functools import cache, cached_property
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.utils import get_jwt_token_expires

logger = logging.getLogger(__name__)


def _is_transient_error(exc: Exception) -> bool:
    """Check if exception is a transient error worth retrying."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (502, 503, 504)
    return False


RETRY_TRANSIENT = dict(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=32),
    retry=retry_if_exception(_is_transient_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)


class TokenInfo:
    def __init__(self, token: str):
        self.token = token
        self.expires = get_jwt_token_expires(token)

    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires


class MPTInstallationAuth(httpx.Auth):
    requires_response_body = True

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.token_info: TokenInfo | None = None

    @retry(**RETRY_TRANSIENT)
    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        if not self.token_info or self.token_info.is_expired():
            token_request = self.build_token_request()
            token_response = yield token_request
            token_response.raise_for_status()
            await token_response.aread()
            self.update_token(token_response)

        request.headers["Authorization"] = f"Bearer {self.token_info.token}"
        yield request

    def build_token_request(self) -> httpx.Request:
        """Builds the token refresh request."""
        return httpx.Request(
            "POST",
            f"{settings.base_url}/integration/installations/-/token",
            headers={"Authorization": f"Bearer {settings.api_key}"},
            params={"account.id": self.account_id},
        )

    def update_token(self, response: httpx.Response) -> None:
        """Updates tokens after a successful refresh."""
        if response.status_code == 200:
            data = response.json()
            self.token_info = TokenInfo(data["token"])


class MPTExtensionAuth(httpx.Auth):
    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        request.headers["Authorization"] = f"Bearer {settings.api_key}"
        yield request



class MPTClient:
    def __init__(self, auth: httpx.Auth) -> None:
        self.auth = auth

    @cached_property
    def httpx_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=settings.base_url,
            auth=self.auth,
            timeout=httpx.Timeout(
                connect=10.0,
                read=180.0,
                write=2.0,
                pool=5.0,
            ),
        )

    @retry(**RETRY_TRANSIENT)
    async def get(
        self,
        endpoint: str,
        id: str,
        select: list | None = None,
    ) -> dict[str, Any]:
        url = f"{endpoint}/{id}"
        if select:
            url = f"{url}?select={','.join(select or [])}"
        response = await self.httpx_client.get(url)
        try:
            response.raise_for_status()
            return response.json()
        finally:
            await response.aclose()

    async def create(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        response: httpx.Response = await self.httpx_client.post(
            endpoint,
            json=payload,
        )
        try:
            response.raise_for_status()
            return response.json()
        finally:
            await response.aclose()

    async def update(self, endpoint: str, id: str, payload: dict) -> dict[str, Any]:
        response = await self.httpx_client.put(f"{endpoint}/{id}", json=payload)
        try:
            response.raise_for_status()
            return response.json()
        finally:
            await response.aclose()

    async def delete(self, endpoint: str, id: str) -> None:
        response = await self.httpx_client.delete(f"{endpoint}/{id}")
        try:
            response.raise_for_status()
        finally:
            await response.aclose()

    async def run_object_action(
        self, endpoint: str, id: str, action: str, payload: dict | None = None
    ) -> dict[str, Any] | None:
        response: httpx.Response = await self.httpx_client.post(
            f"{endpoint}/{id}/{action}",
            json=payload,
        )
        try:
            response.raise_for_status()
            return response.json()
        finally:
            await response.aclose()

    @retry(**RETRY_TRANSIENT)
    async def get_page(
        self,
        endpoint: str,
        limit: int,
        offset: int,
        query: str | None = None,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        rql = None
        if query or select:
            rql = f"{query or ''}&select={','.join(select or [])}"
        url = f"{endpoint}?{rql or ''}&limit={limit}&offset={offset}"

        response = await self.httpx_client.get(url)
        try:
            response.raise_for_status()
            page = response.json()
            return page
        finally:
            await response.aclose()

    async def count(
        self,
        endpoint: str,
        query: str | None = None,
    ) -> dict[str, Any]:
        page = await self.get_page(endpoint, limit=0, offset=0, query=query)
        return page["$meta"]["pagination"]["total"]

    async def first(
        self,
        endpoint: str,
        query: str | None = None,
        select: list[str] | None = None,
    ) -> dict[str, Any] | None:
        items = await self.get_page(
            endpoint,
            limit=1,
            offset=0,
            query=query,
            select=select,
        )
        if items["data"]:
            return items["data"][0]

    async def collection_iterator(
        self,
        endpoint: str,
        query: str | None = None,
        select: list[str] | None = None,
    ) -> AsyncGenerator[dict, None]:
        offset = 0
        while True:
            page = await self.get_page(
                endpoint, settings.rows_per_page, offset, query=query, select=select
            )
            items = page["data"]

            for item in items:
                yield item

            pagination_meta = page["$meta"]["pagination"]
            total = pagination_meta["total"]
            if total <= settings.rows_per_page + offset:
                break

            offset = offset + settings.rows_per_page

    async def get_user(self, user_id: str, select: list[str] | None = None) -> dict[str, Any]:
        return await self.get("accounts/users", user_id, select=select)

    async def get_account(self, account_id: str, select: list[str] | None = None) -> dict[str, Any]:
        return await self.get("accounts/accounts", account_id, select=select)

    async def get_token(self, user_id: str, select: list[str] | None = None) -> dict[str, Any]:
        return await self.get("accounts/api-tokens", user_id, select=select)

    async def get_order(self, order_id: str, select: list[str] | None = None) -> dict[str, Any]:
        return await self.get("commerce/orders", order_id, select=select)

    async def get_task(self, task_id: str, select: list[str] | None = None) -> dict[str, Any]:
        return await self.get("system/tasks", task_id, select=select)

    async def update_task(self, task_id: str, payload: dict) -> dict[str, Any]:
        return await self.update("system/tasks", task_id, payload=payload)

    async def start_task(self, task_id: str, instance_id: str) -> dict[str, Any]:
        task = await self.run_object_action("system/tasks", task_id, "execute")
        params = task["parameters"]
        params["instanceId"] = instance_id.upper()
        return await self.update_task(task_id, {"parameters": params})

    async def complete_task(self, task_id: str, payload: dict | None = None) -> dict[str, Any]:
        return await self.run_object_action("system/tasks", task_id, "complete", payload=payload)

    async def reschedule_task(self, task_id: str) -> dict[str, Any]:
        return await self.run_object_action("system/tasks", task_id, "reschedule")

    def get_orders(
        self, query: str | None = None, select: list[str] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("commerce/orders", query=query, select=select)


@cache
def get_installation_client(account_id: str) -> MPTClient:
    return MPTClient(MPTInstallationAuth(account_id))
