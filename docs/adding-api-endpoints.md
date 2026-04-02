# Adding API Endpoints

This guide explains how to add authenticated REST endpoints to your extension.
These endpoints are designed for consumption by the platform UI or external API clients
that present a valid JWT token issued by the SoftwareOne Marketplace.

## Checklist

- [ ] Add the handler in `backend/app/routers/api.py`.
- [ ] Inject `AuthContext` for caller identity.
- [ ] Inject `ExtensionContext` for extension runtime metadata.
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

Unlike event handlers, these endpoints are **not** declared in
`meta.yaml` — they are plain FastAPI routes called directly by clients.

## Adding a Handler in routers/api.py

```python
from app.dependencies import AuthContext, ExtensionContext

# router is defined at module level with prefix="/api/v1"

@router.get("/me")  # full path: /api/v1/me
async def who_am_i(
    auth_ctx: AuthContext,
    ext_ctx: ExtensionContext,
):
    return {
        "auth": auth_ctx.model_dump(),
        "ext": ext_ctx.model_dump(),
    }
```

## Working with Dependencies

### AuthContext

`AuthContext` is a typed FastAPI dependency that provides caller identity extracted from
the JWT token.  Import and inject it with `Annotated`:

```python
from app.dependencies import AuthContext

@router.get("/example")
async def example(ctx: AuthContext) -> ...:
    print(ctx.account_id)      # str — always present
    print(ctx.account_type)    # str — always present
    print(ctx.installation_id) # str | None
    print(ctx.user_id)         # str | None
    print(ctx.token_id)        # str | None
```

See [docs/injectable-dependencies.md](injectable-dependencies.md) for the full reference.

### ExtensionContext

`ExtensionContext` provides runtime metadata for the running extension instance.
Use it to access values like the current extension and instance IDs.

```python
from app.dependencies import ExtensionContext

@router.get("/me")
async def example(ext_ctx: ExtensionContext) -> dict:
    return {
        "extension_id": ext_ctx.extension_id,
        "instance_id": ext_ctx.instance_id,
        "account_id": ext_ctx.account_id,
        "domain": ext_ctx.domain,
    }
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
from app.dependencies import AuthContext, ExtensionContext


@router.get("/me")
async def who_am_i(
    auth_ctx: AuthContext,
    ext_ctx: ExtensionContext,
) -> dict:
    """Return caller identity and extension runtime context."""
    return {
        "auth": auth_ctx.model_dump(),
        "ext": ext_ctx.model_dump(),
    }
```

## Best Practices

1. **Always type-annotate** handler parameters and return values.
2. **Use dependency injection** (`AuthContext`, `ExtensionContext`) — never parse auth headers
   manually or instantiate HTTP clients inside handlers.
3. **Define Pydantic models** for non-trivial request/response shapes instead of returning raw dicts.
4. **Log with `logging.getLogger(__name__)`** — avoid `print`.
5. **Keep handlers thin** — delegate business logic to helper functions or service modules.

## Troubleshooting

- **401 Unauthorized**: Token is missing, expired, or the `Authorization` header is malformed.
- **403 Forbidden**: Token is valid but the claims do not satisfy a dependency's requirements.
- **422 Unprocessable Entity**: Request body or query parameters failed Pydantic validation.

## See Also

- [Injectable Dependencies](injectable-dependencies.md) — Full reference for `AuthContext`, `ExtensionContext`, `InstallationClient`, and `ExtensionClient`
- [Platform Context](platform-context.md) — Extension development guide for agents
- [Adding Unauthenticated Endpoints](adding-unauthenticated-endpoints.md) — Bypass routes without auth
- [routers/api.py](../backend/app/routers/api.py) — Authenticated API router
- [schema.py](../backend/app/schema.py) — Pydantic model definitions
