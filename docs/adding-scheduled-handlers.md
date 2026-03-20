# Adding Scheduled Handlers

This guide explains how to add scheduled (cron-based) handlers to your extension.
Scheduled handlers are invoked automatically by the platform at a configured cadence,
independent of any user action or business-object state change.

## Checklist

- [ ] Register the job in `meta.yaml` under `schedules`.
- [ ] Add a handler in `backend/app/routers/schedules.py`.
- [ ] Ensure the `path` in `meta.yaml` equals the router prefix (`/schedules`) plus the route path.
- [ ] Set a valid cron expression in the `cron` field.
- [ ] Return `EventResponse.ok()` on success, `EventResponse.reschedule()` for retryable failures.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Schedules let your extension run recurring maintenance or housekeeping tasks — for example,
syncing data, expiring stale records, or generating reports — without depending on a specific
platform event.  The platform triggers the endpoint according to a cron expression.

## Step 1: Register the Schedule in meta.yaml

Declare the schedule under the `schedules` section of [meta.yaml](../meta.yaml):

```yaml
schedules:
  - path: /schedules/dojob
    id: my.cron.job
    name: "My cron job"
    description: "Test cron job"
    cron: "* * * * *"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `path` | yes | Full URL the platform calls. Must equal `/schedules` + the route decorator path. |
| `id` | yes | Stable dot-namespaced identifier for the schedule. |
| `name` | yes | Human-readable display name. |
| `description` | yes | Human-readable description shown in the platform UI. |
| `cron` | yes | Standard five-field cron expression (`minute hour day month weekday`). |

## Step 2: Add the Handler in routers/schedules.py

Add a `POST` route to [backend/app/routers/schedules.py](../backend/app/routers/schedules.py).
The router carries the `/schedules` prefix automatically:

```python
from app.auth import AuthContext
from app.schema import EventResponse

# router is defined at module level with prefix="/schedules"

@router.post("/dojob")  # full path: /schedules/dojob
async def run_job(ctx: AuthContext) -> EventResponse:
    """Perform periodic maintenance for the current installation."""
    await perform_maintenance(ctx.installation_id)
    return EventResponse.ok()
```

The decorator path is relative to the router prefix.
`/schedules` + `/dojob` = `/schedules/dojob` must match `meta.yaml`.

## Response Options

| Method | Platform behaviour |
|--------|--------------------|
| `EventResponse.ok()` | Run completed — platform records success. |
| `EventResponse.reschedule(seconds=N)` | Transient failure — platform retries after N seconds. |
| `EventResponse.cancel()` | Permanent failure — platform records failure with no immediate retry. |

## Cron Expression Reference

```
┌───── minute        (0–59)
│ ┌─── hour          (0–23)
│ │ ┌─ day of month  (1–31)
│ │ │ ┌ month        (1–12)
│ │ │ │ ┌ day of week (0–7, 0 and 7 = Sunday)
* * * * *
```

Common examples:

| Expression | Meaning |
|------------|---------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour at :00 |
| `0 0 * * *` | Every day at midnight |
| `0 9 * * 1` | Every Monday at 09:00 |
| `0 0 1 * *` | First day of every month at midnight |

## Complete Example

### meta.yaml

```yaml
schedules:
  - path: /schedules/cleanup
    id: data.cleanup.daily
    name: "Daily data cleanup"
    description: "Remove expired records and generate daily usage report"
    cron: "0 2 * * *"
```

### routers/schedules.py

```python
import logging

from app.auth import AuthContext
from app.client import InstallationClient
from app.schema import EventResponse

logger = logging.getLogger(__name__)


@router.post("/cleanup")  # full path: /schedules/cleanup
async def daily_cleanup(
    ctx: AuthContext,
    client: InstallationClient,
) -> EventResponse:
    """Remove expired records and generate a daily usage report."""
    logger.info("Starting daily cleanup for installation %s", ctx.installation_id)

    deleted = await delete_expired_records(client)
    logger.info("Deleted %d expired records", deleted)

    await generate_usage_report(client)
    return EventResponse.ok()
```

## Best Practices

1. **Keep handlers idempotent** — the platform may invoke the same job twice if a previous run
   did not confirm completion.
2. **Log progress** with `logging.getLogger(__name__)` so runs are traceable.
3. **Use `reschedule`** for transient failures (e.g., downstream APIs temporarily unavailable).
4. **Avoid heavy computation** in the handler body; delegate to helper functions so the handler
   stays readable and testable.

## Troubleshooting

- **Handler not invoked**: Verify the `path` in `meta.yaml` and the cron expression are correct.
- **Path mismatch**: `meta.yaml` `path` must equal the full combined URL (`/schedules` + decorator path).
- **Cron expression not as expected**: Use an online cron expression validator to confirm timing.

## See Also

- [Adding Deferred Handlers](adding-deferred-handlers.md) — On-demand background tasks
- [Platform Context](platform-context.md) — Extension development guide for agents
- [meta.yaml](../meta.yaml) — Extension manifest reference
- [routers/schedules.py](../backend/app/routers/schedules.py) — Schedules router
