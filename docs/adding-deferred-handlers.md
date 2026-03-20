# Adding Deferred Handlers

This guide explains how to add deferred background-task handlers to your extension.
Deferred handlers let the platform trigger a task asynchronously — useful for long-running
work that cannot complete within a webhook's synchronous response window.

## Checklist

- [ ] Register the deferrable in `meta.yaml` under `deferrables`.
- [ ] Add a handler in `backend/app/routers/deferreds.py` using the HTTP method declared in `meta.yaml`.
- [ ] Ensure the `path` in `meta.yaml` equals the router prefix (`/deferreds`) plus the route path.
- [ ] Callers invoke the endpoint with the `MPT-async: true` request header to trigger async execution.
- [ ] Read the task ID from the `MPT-Task-Id` request header inside the handler.
- [ ] Call `ext_client.start_task(task_id)` before doing any work.
- [ ] Report progress with `ext_client.update_task(task_id, payload={"progress": <0-100>})` during processing.
- [ ] Call `ext_client.complete_task(task_id)` when work succeeds.
- [ ] Use FastAPI `BackgroundTasks` to schedule the actual processing and return `EventResponse.ok()` immediately.
- [ ] Use `AuthContext` and/or `InstallationClient` if the handler needs API access.
- [ ] Return `EventResponse.ok()` on success, `EventResponse.reschedule()` for retryable failures.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Deferrables are background tasks the platform invokes on behalf of an installation.
A typical pattern is to accept an event synchronously (returning `ok()`), then trigger a
deferrable to carry out the actual work.  The platform can retry deferrables on failure.

### How Async Invocation Works

1. A caller sends a request to the deferrable path with the header `MPT-async: true`.
2. The platform intercepts the request, creates a background task, and returns immediately
   with a `202 Accepted` response containing the `MPT-Task-Id` response header.
3. The platform later invokes the handler asynchronously, forwarding the same `MPT-Task-Id`
   as a **request** header so the handler can identify its own task.
4. The handler uses `ExtensionClient` to report progress, mark completion, or record errors
   on that task ID throughout its execution.

```
Caller                 Platform                Extension handler
  │                       │                          │
  │── POST /deferreds/x ──▶│                          │
  │   MPT-async: true      │                          │
  │                        │── create task ──▶ [task] │
  │◀── 202 Accepted ───────│                          │
  │    MPT-Task-Id: TSK-…  │                          │
  │                        │                          │
  │             (async)    │── POST /deferreds/x ─────▶│
  │                        │   MPT-Task-Id: TSK-…      │
  │                        │                    handler runs
  │                        │◀── EventResponse.ok() ───│
```

## Step 1: Register the Deferrable in meta.yaml

Declare the deferrable under the `deferrables` section of [meta.yaml](../meta.yaml):

```yaml
deferrables:
  - path: "/deferreds/synchronize"
    method: GET
    description: "Run a background synchronization task"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `path` | yes | Full URL the platform calls. Must equal `/deferreds` + the route decorator path. |
| `method` | yes | HTTP method (`GET` or `POST`). |
| `description` | yes | Human-readable description shown in the platform UI. |

## Step 2: Add the Handler in routers/deferreds.py

Add a route to [backend/app/routers/deferreds.py](../backend/app/routers/deferreds.py).
The router carries the `/deferreds` prefix automatically.

The platform forwards the `MPT-Task-Id` header when it invokes the handler. Inject
`Request` to read it, then use `ExtensionClient` to update the task throughout execution:

```python
import logging

from fastapi import BackgroundTasks, Request

from app.auth import AuthContext
from app.client import ExtensionClient, InstallationClient
from app.schema import EventResponse

logger = logging.getLogger(__name__)

# router is defined at module level with prefix="/deferreds"

async def _do_synchronize(
    task_id: str,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> None:
    """Background worker: synchronize orders for the current installation."""
    await ext_client.start_task(task_id)

    orders = await client.list_orders()
    total = len(orders)

    for idx, order in enumerate(orders, start=1):
        await process_order_locally(order)
        progress = int(idx / total * 100)
        await ext_client.update_task(task_id, payload={"progress": progress})

    await ext_client.complete_task(task_id)


@router.get("/synchronize")  # full path: /deferreds/synchronize
async def synchronize(
    request: Request,
    background_tasks: BackgroundTasks,
    ctx: AuthContext,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> EventResponse:
    """Schedule a background synchronization task and return immediately."""
    task_id = request.headers["MPT-Task-Id"]
    background_tasks.add_task(_do_synchronize, task_id, client, ext_client)
    return EventResponse.ok()
```

The decorator path is relative to the router prefix.
`/deferreds` + `/synchronize` = `/deferreds/synchronize` must match `meta.yaml`.

## Task Status Management

The task lifecycle follows three steps in order:

| Step | Call | When |
|------|------|------|
| 1 — Start | `ext_client.start_task(task_id)` | Immediately before doing any work. Marks the task as in-progress. |
| 2 — Progress | `ext_client.update_task(task_id, payload={"progress": 50})` | Periodically during long-running work. `progress` is an integer from `0` to `100`. |
| 3 — Complete | `ext_client.complete_task(task_id)` | After all work has finished successfully. |

On failure, record the error before returning a non-OK response:

```python
await ext_client.update_task(task_id, payload={"error": str(exc)})
return EventResponse.reschedule(seconds=300)  # or .cancel()
```

The task ID is always available at `request.headers["MPT-Task-Id"]`.

## Response Options

| Method | Platform behaviour |
|--------|--------------------|
| `EventResponse.ok()` | Task completed — platform marks the task as done. |
| `EventResponse.reschedule(seconds=N)` | Transient failure — platform retries after N seconds. |
| `EventResponse.cancel()` | Permanent failure — platform marks the task as failed with no retry. |

## Complete Example

### meta.yaml

```yaml
deferrables:
  - path: "/deferreds/orders/fulfill"
    method: POST
    description: "Provision resources for a new order"
```

### routers/deferreds.py

```python
import logging

from fastapi import BackgroundTasks, Request

from app.auth import AuthContext
from app.client import ExtensionClient, InstallationClient
from app.schema import EventResponse

logger = logging.getLogger(__name__)


async def _generate_report(
    task_id: str,
    account_id: str,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> None:
    """Background worker: generate a sales report and attach it to the task."""
    await ext_client.start_task(task_id)

    await ext_client.update_task(task_id, payload={"progress": 10})
    data = await client.get_account_orders(account_id)

    await ext_client.update_task(task_id, payload={"progress": 50})
    report_bytes = generate_excel_report(data)  # your implementation

    await ext_client.update_task(task_id, payload={"progress": 90})
    await client.upload_task_attachment(task_id, "report.xlsx", report_bytes)

    await ext_client.complete_task(task_id)


@router.post("/reports/generate")  # full path: /deferreds/reports/generate
async def generate_report(
    request: Request,
    background_tasks: BackgroundTasks,
    ctx: AuthContext,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> EventResponse:
    """Schedule Excel report generation in the background and return immediately."""
    task_id = request.headers["MPT-Task-Id"]
    background_tasks.add_task(_generate_report, task_id, ctx.account_id, client, ext_client)
    return EventResponse.ok()
```

## Best Practices

1. **Offload slow work** — return `ok()` from webhooks/events immediately, then let the platform
   invoke a deferrable for the actual processing.
2. **Handle idempotency** — the platform may call the same deferrable multiple times on retry.
3. **Use `reschedule`** for transient errors (rate limits, downstream unavailability) with
   an appropriate back-off interval.
4. **Use `cancel`** for permanent failures where retrying would not help.

## Troubleshooting

- **Task not invoked**: Check that `method` in `meta.yaml` matches the `@router.get` / `@router.post` decorator.
- **Path mismatch**: `meta.yaml` `path` must equal the full combined URL (`/deferreds` + decorator path).
- **Infinite reschedule loop**: Guard against repeated failures with a counter stored on the task object.

## See Also

- [Adding Event Handlers](adding-event-handlers.md) — Trigger deferrables from event handlers
- [Adding Webhook Handlers](adding-webhook-handlers.md) — Synchronous validation before triggering deferrables
- [Platform Context](platform-context.md) — Extension development guide for agents
- [meta.yaml](../meta.yaml) — Extension manifest reference
- [routers/deferreds.py](../backend/app/routers/deferreds.py) — Deferreds router
