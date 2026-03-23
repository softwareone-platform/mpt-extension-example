# Adding Unauthenticated Endpoints

This guide explains how to add unauthenticated (bypass) endpoints to your extension.
Bypass endpoints are reachable without a JWT bearer token and are intended for internal
tooling, health checks, admin operations, or any route the platform itself needs to call
without installation-scoped authentication.

The `bypass` router shares the `/bypass` prefix with the auto-generated OpenAPI docs
(`/bypass/docs`, `/bypass/openapi.json`, `/bypass/redoc`).

## Checklist

- [ ] Add the handler in `backend/app/routers/bypass.py`.
- [ ] Do **not** inject `AuthContext` or `InstallationClient` (no auth is available).
- [ ] Return a typed Pydantic response model or a plain `dict`.
- [ ] Ensure the endpoint does **not** expose sensitive data or allow unauthorised writes.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Bypass endpoints are useful for:

- **Health / readiness checks** — lightweight `GET` routes consumed by load balancers or orchestrators.
- **Internal admin operations** — triggers that run under the extension's own identity, not a caller's JWT.
- **Public metadata** — read-only information that does not require caller authentication.

Because there is no authentication, bypass endpoints must never modify data or return
information that should be protected by caller identity.

## Adding a Handler in routers/bypass.py

```python
# router is defined at module level with prefix="/bypass"

@router.get("/health")  # full path: /bypass/health
async def health_check() -> dict:
    """Return a simple liveness indicator."""
    return {"status": "ok"}
```

No dependency injection is needed — and no auth is available.

## Complete Example

### Health and version endpoint

```python
import logging
from typing import Annotated

from pydantic import Field

from app.config import settings
from app.schema import BaseSchema

logger = logging.getLogger(__name__)


class HealthResponse(BaseSchema):
    status: Annotated[str, Field(description="Liveness indicator.")]
    extension_id: Annotated[str, Field(alias="extensionId", description="Extension ID from settings.")]


@router.get("/health")  # full path: /bypass/health
async def health_check() -> HealthResponse:
    """Return liveness and basic identity information."""
    return HealthResponse(status="ok", extension_id=settings.extension_id)
```

### Admin trigger (extension-scoped, no caller auth)

```python
from app.dependencies import ExtensionClient
from app.schema import BaseSchema


class TriggerResponse(BaseSchema):
    queued: int


@router.post("/admin/requeue-failed")  # full path: /bypass/admin/requeue-failed
async def requeue_failed_tasks(client: ExtensionClient) -> TriggerResponse:
    """Re-queue all failed tasks using the extension's own credentials."""
    tasks = await client.list_failed_tasks()
    for task in tasks:
        await client.requeue_task(task["id"])
    return TriggerResponse(queued=len(tasks))
```

## Security Considerations

- Bypass endpoints are **publicly reachable** — any client that can reach the extension host
  can call them.
- Never return secrets, credentials, or user-scoped data from a bypass endpoint.
- Treat any data received by a bypass endpoint as untrusted; validate inputs with Pydantic.
- Admin-style write operations should be guarded by a shared secret or IP allowlist at the
  infrastructure level (e.g., compose.yaml port binding or reverse-proxy rules).

## Troubleshooting

- **404 Not Found**: Verify the path in `routers/bypass.py` matches what you are calling
  (`/bypass` + decorator path).
- **422 Unprocessable Entity**: Request body failed Pydantic validation.

## See Also

- [Adding API Endpoints](adding-api-endpoints.md) — Authenticated endpoints requiring a JWT
- [Platform Context](platform-context.md) — Extension development guide for agents
- [routers/bypass.py](../backend/app/routers/bypass.py) — Bypass router
- [extension.py](../backend/app/extension.py) — OpenAPI docs mount (`/bypass/docs`)
