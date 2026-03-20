# Adding API Endpoints

This guide explains how to add authenticated REST endpoints to your extension.
These endpoints are designed for consumption by the platform UI or external API clients
that present a valid JWT token issued by the SoftwareOne Marketplace.

## Checklist

- [ ] Add the handler in `backend/app/routers/api.py`.
- [ ] Inject `AuthContext` for identity and `InstallationClient` for API access.
- [ ] Define request/response shapes as Pydantic models in `backend/app/schema.py` (or reuse existing ones).
- [ ] Keep the handler `async` and return a typed response model.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Authenticated endpoints live under the `/api/v1` prefix in
[backend/app/routers/api.py](../backend/app/routers/api.py).  Every request to these routes
must carry a valid `Authorization: Bearer <token>` header.  The `AuthContext` dependency
decodes the JWT and resolves the installation automatically.

Unlike events, webhooks, deferrables, and schedules, these endpoints are **not** declared in
`meta.yaml` — they are plain FastAPI routes called directly by clients.

## Adding a Handler in routers/api.py

```python
from app.auth import AuthContext
from app.client import InstallationClient
from app.schema import BaseSchema

# router is defined at module level with prefix="/api/v1"

class WhoAmIResponse(BaseSchema):
    account_id: str
    account_type: str
    installation_id: str


@router.get("/management/whoami")  # full path: /api/v1/management/whoami
async def whoami(ctx: AuthContext, client: InstallationClient) -> WhoAmIResponse:
    """Return identity information for the authenticated caller."""
    return WhoAmIResponse(
        account_id=ctx.account_id,
        account_type=ctx.account_type,
        installation_id=ctx.installation_id,
    )
```

## Working with Dependencies

### AuthContext

`AuthContext` is a typed FastAPI dependency that provides caller identity extracted from
the JWT token.  Import and inject it with `Annotated`:

```python
from app.auth import AuthContext

@router.get("/example")
async def example(ctx: AuthContext) -> ...:
    print(ctx.account_id)      # str — always present
    print(ctx.account_type)    # str — always present
    print(ctx.installation_id) # str — always present
    print(ctx.user_id)         # str | None
    print(ctx.token_id)        # str | None
```

See [docs/injectable-dependencies.md](injectable-dependencies.md) for the full reference.

### InstallationClient

`InstallationClient` provides an authenticated `httpx` client scoped to the current
installation.  Use its helper methods instead of making raw HTTP calls:

```python
from app.client import InstallationClient

@router.get("/management/account")
async def get_account(ctx: AuthContext, client: InstallationClient) -> dict:
    """Return the account information for the current installation."""
    return await client.get_account(ctx.account_id)
```

## Defining Response Models

All response models must inherit `BaseSchema` from `app.schema`:

```python
from typing import Annotated
from pydantic import Field
from app.schema import BaseSchema

class OrderSummary(BaseSchema):
    id: Annotated[str, Field(description="Platform order ID.")]
    status: Annotated[str, Field(description="Current order status.")]
    total_amount: Annotated[float, Field(alias="totalAmount", description="Order total.")]
```

`BaseSchema` enforces:
- `extra="forbid"` — unknown fields are rejected.
- `populate_by_name=True` — both the Python name and the alias are accepted on input.

## Complete Example

```python
import logging
from typing import Annotated

from pydantic import Field

from app.auth import AuthContext
from app.client import InstallationClient
from app.schema import BaseSchema

logger = logging.getLogger(__name__)


class AccountDetails(BaseSchema):
    id: Annotated[str, Field(description="Platform account ID.")]
    name: Annotated[str, Field(description="Account display name.")]
    type: Annotated[str, Field(description="Account type.")]


@router.get("/management/account")  # full path: /api/v1/management/account
async def get_account(ctx: AuthContext, client: InstallationClient) -> AccountDetails:
    """Return details of the account associated with the current installation."""
    logger.info("Fetching account %s", ctx.account_id)
    raw = await client.get_account(ctx.account_id)
    return AccountDetails.model_validate(raw)
```

## Best Practices

1. **Always type-annotate** handler parameters and return values.
2. **Use dependency injection** (`AuthContext`, `InstallationClient`) — never parse auth headers
   manually or instantiate HTTP clients inside handlers.
3. **Define Pydantic models** for non-trivial request/response shapes instead of returning raw dicts.
4. **Log with `logging.getLogger(__name__)`** — avoid `print`.
5. **Keep handlers thin** — delegate business logic to helper functions or service modules.

## Troubleshooting

- **401 Unauthorized**: Token is missing, expired, or the `Authorization` header is malformed.
- **403 Forbidden**: Token is valid but the claims do not satisfy a dependency's requirements.
- **422 Unprocessable Entity**: Request body or query parameters failed Pydantic validation.

## See Also

- [Injectable Dependencies](injectable-dependencies.md) — Full reference for `AuthContext` and `InstallationClient`
- [Platform Context](platform-context.md) — Extension development guide for agents
- [Adding Unauthenticated Endpoints](adding-unauthenticated-endpoints.md) — Bypass routes without auth
- [routers/api.py](../backend/app/routers/api.py) — Authenticated API router
- [schema.py](../backend/app/schema.py) — Pydantic model definitions
