# Platform Context

A complete reference for agents and developers working on a SoftwareOne Marketplace Platform
extension.  Read this document before making substantive changes to understand how the
extension runtime works end-to-end.

---

## What is a Marketplace Extension?

A Marketplace Extension is a FastAPI web service that the SoftwareOne Marketplace Platform
invokes to hook into commerce workflows. The extension:

- **Receives events** when platform objects change state (orders, subscriptions, agreements, …).
- **Exposes a REST API** consumed by the platform UI or external clients.
- **Renders UI sockets** via frontend bundles served as static assets.

---

## Repository Layout

```
backend/app/       — FastAPI service (stable)
  routers/         — One module per endpoint category (see below)
  auth.py          — JWT → AuthContext dependency
  client.py        — InstallationClient / ExtensionClient HTTP clients
  dependencies.py  — AuthContext / ExtensionContext / client dependencies
  config.py        — Dynaconf settings (settings.yaml + EXT_* env vars)
  extension.py     — FastAPI app, router mounting, static file serving
  schema.py        — Pydantic models shared across all routers
  main.py          — CLI entry point (runext)
frontend/          — TypeScript/SCSS source (build output → static/)
static/            — Generated frontend bundles (do not hand-edit)
meta.yaml          — Extension manifest (events, plugs)
settings.yaml      — Public configuration (env-overridable via EXT_* prefix)
.secrets.yaml      — Private secrets — git-ignored, never commit
```

See [docs/project-structure.md](project-structure.md) for the full tree.

---

## Router Map

Each endpoint category lives in its own router module and has a dedicated URL prefix.

| Router file | Prefix | Declared in meta.yaml | Purpose |
|-------------|--------|-----------------------|---------|
| `routers/events.py` | `/events` | `events[].path` | Platform event handlers |
| `routers/api.py` | `/api/v1` | not declared | Authenticated REST endpoints |
| `routers/bypass.py` | `/bypass` | not declared | Unauthenticated / internal endpoints |

**Rule**: always add a handler to the router that matches its category.  Never add event
handlers to `api.py` or REST endpoints to `events.py`.

---

## meta.yaml and Router Alignment

`meta.yaml` is a Jinja2 template that declares extension capabilities to the platform.
The `path` field for events **must** equal the router prefix plus the route decorator path.

```yaml
# meta.yaml — declare the capability
events:
  - event: platform.commerce.order.status_changed
    path: "/events/orders"       # /events (prefix) + /orders (decorator)
    task: true
```

```python
# routers/events.py — implement the capability
@router.post("/orders")          # router prefix is /events
async def process_order(event: Event) -> EventResponse: ...
```

Any mismatch between `meta.yaml` `path` and the actual route URL will silently break
delivery.  Always update both files in the same change.

---

## Configuration System

Settings flow through three layers, with later layers overriding earlier ones:

1. `settings.yaml` — committed public defaults.
2. `.secrets.yaml` — local secrets (git-ignored).
3. `EXT_*` environment variables — runtime overrides (e.g. `EXT_ENV_DOMAIN=s1.dev`).

Access settings anywhere via `from app.config import settings`:

```python
from app.config import settings

url = settings.base_url        # computed by Dynaconf @format/@jinja
ext_id = settings.extension_id
key = settings.api_key         # from .secrets.yaml or EXT_API_KEY
```

Never hardcode API URLs, extension IDs, product IDs, or secrets in source files.

See [docs/settings.md](settings.md) for the full reference.

---

## Authentication Model

The platform authenticates requests to the extension with a signed JWT placed in
`Authorization: Bearer <token>`.

The `AuthContext` FastAPI dependency decodes this token and provides:

| Property | Type | Always present |
|----------|------|----------------|
| `account_id` | `str` | yes |
| `account_type` | `str` | yes |
| `installation_id` | `str` | yes (resolved automatically if absent from token) |
| `user_id` | `str \| None` | no — only for user-initiated calls |
| `token_id` | `str \| None` | no — only for API-token calls |

Bypass endpoints (`routers/bypass.py`) have no auth — never inject `AuthContext` there.

See [docs/injectable-dependencies.md](injectable-dependencies.md) for the full reference.

---

## Client Abstractions

### InstallationClient

An authenticated `httpx.AsyncClient` scoped to the current installation.
Tokens are acquired and refreshed automatically.

```python
from app.dependencies import InstallationClient

@router.get("/management/account")
async def get_account(ctx: AuthContext, client: InstallationClient) -> dict:
    return await client.get_account(ctx.account_id)
```

Use `InstallationClient` for any API call made on behalf of a specific account/installation.

### ExtensionClient

An authenticated client using the extension's own API key (vendor-scoped).
Use this for operations that do not belong to a specific installation, such as
listing all installations or admin-level lookups.

```python
from app.dependencies import ExtensionClient

@router.post("/bypass/admin/reset")
async def reset(client: ExtensionClient) -> dict:
    return await client.list_installations()
```

### ExtensionContext

Runtime metadata for the running extension instance, injected as a dependency.
Use this when you need values such as the current `instance_id`.

```python
from app.dependencies import ExtensionContext

@router.post("/events/orders")
async def process_order(ext_ctx: ExtensionContext) -> EventResponse:
    instance_id = ext_ctx.instance_id
    return EventResponse.ok()
```

---

### Event task lifecycle

When an event handler runs with `task: true`, follow this sequence:

1. `ext_client.start_task(task_id, ext_ctx.instance_id)` — mark the task as in-progress for the current extension instance.
2. `ext_client.update_task(task_id, payload={"progress": 50})` — report progress as an integer 0–100 at suitable intervals.
3. `ext_client.reschedule_task(task_id)` - mark the task as rescheduled.
4. `ext_client.complete_task(task_id)` — mark the task as done.

If work fails, call `ext_client.update_task(task_id, payload={"error": str(exc)})` before returning `reschedule()` or `cancel()`.

## Response Lifecycle for Events and Tasks

Platform-facing event handlers return an
`EventResponse` that tells the platform what to do next:

```python
from app.schema import EventResponse

EventResponse.ok()                    # Success — proceed / mark done
EventResponse.cancel()                # Permanent failure — stop retrying
EventResponse.reschedule(seconds=300) # Transient failure — retry in 5 minutes
```

---

## Schema Conventions

All models inherit `BaseSchema`:

```python
from typing import Annotated
from pydantic import Field
from app.schema import BaseSchema

class MyResponse(BaseSchema):
    order_id: Annotated[str, Field(alias="orderId", description="Platform order ID.")]
    total: Annotated[float, Field(description="Order total amount.")]
```

`BaseSchema` configuration:
- `extra="forbid"` — unknown fields raise a validation error.
- `populate_by_name=True` — both the Python name and the camelCase alias are accepted.
- `from_attributes=True` — models can be constructed from ORM-like objects.

---

## Development Commands

```bash
# Backend
cd backend && uv sync                                         # install deps
runext                                                        # start extension
runext -r                                                     # start with auto-reload
EXT_ENV_DOMAIN=s1.dev runext                                  # override domain
cd backend && uv run ruff check --fix . && uv run ruff format .  # lint + format

# Frontend (verify scaffold files exist before running)
cd frontend && npm install && npm run build                   # build once
cd frontend && npm run start                                  # watch mode

# Docker
docker compose build && docker compose run --rm bash         # dev container
docker compose run --rm app                                   # run extension

# Debugging
mrok agent dev console   # spy extension traffic in terminal
mrok agent dev web       # spy extension traffic in browser
```

---

## Adding New Capabilities — Quick Reference

| Task | Guide |
|------|-------|
| React to a platform event | [adding-event-handlers.md](adding-event-handlers.md) |
| Add an authenticated REST endpoint | [adding-api-endpoints.md](adding-api-endpoints.md) |
| Add an unauthenticated / internal endpoint | [adding-unauthenticated-endpoints.md](adding-unauthenticated-endpoints.md) |

---

## Common Pitfalls

| Pitfall | Consequence | Fix |
|---------|-------------|-----|
| `meta.yaml` path ≠ router URL | Events silently not delivered | Align `path` with prefix + decorator |
| Hardcoded API URL or key | Broken in other environments, security risk | Use `settings.*` or `EXT_*` env vars |
| Using `requests` instead of `InstallationClient` | Blocking I/O in async context | Use the injected `client` dependency |
| Sync handler in async FastAPI app | Thread-pool exhaustion | Mark all handlers `async def` |
| Editing `static/` directly | Overwritten on next `npm run build` | Edit source in `frontend/src/` |
| Committing `.secrets.yaml` | Credential leak | The file is git-ignored; keep it local |
| Returning raw `dict` with no model | Undocumented API, no validation | Define a `BaseSchema` response model |
