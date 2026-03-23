# Adding Event Handlers

This guide explains how to add new event handlers to your extension to receive and process platform events.

## Checklist

- [ ] Register the event in `meta.yaml` under `events`.
- [ ] Add a `POST` handler in `backend/app/routers/events.py`.
- [ ] Ensure the `path` in `meta.yaml` matches the full URL produced by the router (prefix `/events` + route).
- [ ] Set `task: true` when the platform should create a task for the event.
- [ ] Use typed `Event` / `EventResponse` models from `app.schema`.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Event handlers allow your extension to react to changes in the SoftwareOne Marketplace Platform. When a business object (order, subscription, agreement, etc.) changes state, the platform can notify your extension by sending an event to a designated endpoint.

## Step 1: Register the Event in meta.yaml

First, declare the event subscription in your [meta.yaml](../meta.yaml) file under the `events` section:

```yaml
events:
  - event: platform.commerce.order.status_changed
    condition: "and(eq(status,Processing),eq(product.id,{{ settings.product_id }}))"
    path: "/events/orders"
    task: true
```

### Event Key Format

The `event` key follows a dotted notation pattern:

```
{src}.{module}.{object}.{action}
```

**Components:**

- `src`: Always `platform`
- `module`: The platform module (e.g., `commerce`, `accounts`, `catalog`)
- `object`: The business object type (e.g., `order`, `subscription`, `agreement`)
- `action`: The event trigger, which can be:
  - `created` — Object was created
  - `updated` — Object was modified
  - `deleted` — Object was removed
  - `status_changed` — Object status changed
  - `<custom>` — Any custom action defined by the platform

**Examples:**

```yaml
platform.commerce.order.created
platform.commerce.subscription.status_changed
platform.catalog.product.deleted
```

### Optional Filtering

You can optionally apply a filter using the `condition` field to receive only events matching specific criteria. The filter uses a function-based syntax and operates on the business object that triggered the event.

**Syntax:**

```yaml
condition: "and(eq(field,value),ne(other_field,value))"
```

**Available functions:**

See [Resource Query Language](https://docs.platform.softwareone.com/developer-resources/rest-api/resource-query-language) for a complete guide
about how to express condition.

**Examples:**

```yaml
# Only orders with status "Processing" for a specific product
condition: "and(eq(status,Processing),eq(product.id,PRD-123-456))"

# Subscriptions that are either Active or Suspended
condition: "or(eq(status,Active),eq(status,Suspended))"

# Orders above a certain value
condition: "eq(highValue,true)"
```

You can reference values from `settings.yaml` using Jinja2 template syntax:

```yaml
condition: "eq(product.id,{{ settings.product_id }})"
```

### Additional Fields

- `path`: The full URL the platform calls on your extension. Must equal the router prefix (`/events`) plus the route path declared with `@router.post(...)`.
- `task`: Set to `true` if the platform should create a task to track event processing.

## Step 2: Add the Endpoint in routers/events.py

Create a new `POST` endpoint in [backend/app/routers/events.py](../backend/app/routers/events.py). The router already carries the `/events` prefix:

```python
@router.post("/orders")  # full path: /events/orders
async def process_order(event: Event) -> EventResponse:
    """Handle order status-change events."""
    print(f"Received order event: {event.object.id}")
    print(f"Event type: {event.details.event_type}")
    return EventResponse.ok()
```

The decorator path is relative to the router prefix. The full URL (`/events` + `/orders` = `/events/orders`) must match the `path` in `meta.yaml`.

## Step 3: Understand Request and Response Models

### Request Body: `Event` Model

The platform sends event data as JSON matching the `Event` Pydantic model defined in [backend/app/schema.py](../backend/app/schema.py):

```python
class Event(BaseSchema):
    id: str                      # Unique message ID for correlation
    object: Object               # Information about the affected object
    details: Details             # Event metadata (type, timing)
    task: Task | None = None     # Optional task information
```

**Nested models:**

```python
class Object(BaseSchema):
    id: str              # Platform object ID
    name: str            # Object name
    object_type: str     # Object type (e.g., "Order", "Subscription")

class Details(BaseSchema):
    event_type: str      # The full event key (e.g., "platform.commerce.order.created")
    enqueue_time: datetime   # When platform received the event
    delivery_time: datetime  # When platform delivered to extension

class Task(BaseSchema):
    id: str              # Platform task ID if task tracking enabled
```

**Example event payload:**

```json
{
  "id": "MSG-001",
  "object": {
    "id": "ORD-1234-5678",
    "name": "Order for Product X",
    "objectType": "Order"
  },
  "details": {
    "eventType": "platform.commerce.order.status_changed",
    "enqueueTime": "2026-03-05T10:30:00Z",
    "deliveryTime": "2026-03-05T10:30:01Z"
  },
  "task": {
    "id": "TSK-9876-5432"
  }
}
```

### Response: `EventResponse` Model

Your endpoint must return an `EventResponse` indicating how the platform should proceed:

```python
class EventResponse(BaseSchema):
    response: Literal["OK", "Delay", "Cancel"]
    delay: int | None  # Required when response is "Delay"
```

**Response options:**

1. **OK** — Event processed successfully
   ```python
   return EventResponse.ok()
   ```

2. **Reschedule** — Retry the event after a specified delay (in seconds)
   ```python
   return EventResponse.reschedule(seconds=300)  # Retry in 5 minutes
   ```

3. **Cancel** — Stop processing this event (no retries)
   ```python
   return EventResponse.cancel()
   ```

## Event Handling Patterns

The platform waits for a response to event handlers for 100 seconds before timing out. Choose your pattern based on how long work takes.

### Pattern 1: Quick Fulfillment (Sync)

Use this pattern when work completes within the response timeout (100 seconds).

**meta.yaml**

```yaml
events:
  - event: platform.commerce.order.status_changed
    condition: "and(eq(status,Processing),eq(product.id,{{ settings.product_id }}))"
    path: "/events/orders"
    task: true
```

**routers/events.py**

```python
import logging

from app.dependencies import AuthContext, ExtensionClient, ExtensionContext, InstallationClient
from app.config import settings
from app.schema import Event, EventResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events")

@router.post("/orders")
async def process_order(
    event: Event,
    ctx: AuthContext,
    ext_ctx: ExtensionContext,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> EventResponse:
    """Provision service quickly (completes within timeout)."""
    order_id = event.object.id
    task_id = event.task.id

    # 1. Start task
    await ext_client.start_task(task_id, ext_ctx.instance_id)

    try:
        # 2. Fetch order
        order = await client.get_order(order_id)

        # 3. Check status — skip if not processing
        if order["status"] != "Processing":
            await ext_client.complete_task(task_id)
            return EventResponse.ok()

        # 4. Provision service in external system
        service_id = await provision_service(
            order,
            api_key=settings.external_api_key,
        )

        # 5. Create subscription in platform
        await client.create_subscription(
            order_id,
            external_id=service_id,
        )

        # 6. Complete order
        await client.complete_order(order_id)

        # 7. Complete task
        await ext_client.complete_task(task_id)

        return EventResponse.ok()

    except Exception as exc:
        await ext_client.reschedule_task(task_id)
        return EventResponse.reschedule(seconds=300)
```

### Pattern 2: Progressive Fulfillment (Reschedule)

Use this pattern when work requires multiple steps or external dependencies that may not be immediately ready.
The handler reschedules itself to resume later.

**meta.yaml**

```yaml
events:
  - event: platform.commerce.order.status_changed
    condition: "and(eq(status,Processing),eq(product.id,{{ settings.product_id }}))"
    path: "/events/orders"
    task: true
```

**routers/events.py**

```python
import logging

from app.dependencies import AuthContext, ExtensionClient, ExtensionContext, InstallationClient
from app.config import settings
from app.schema import Event, EventResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events")


@router.post("/orders")
async def process_order(
    event: Event,
    ctx: AuthContext,
    ext_ctx: ExtensionContext,
    client: InstallationClient,
    ext_client: ExtensionClient,
) -> EventResponse:
    """Provision service with possible rescheduling for setup/wait steps."""
    order_id = event.object.id
    task_id = event.task.id

    # 1. Start task
    await ext_client.start_task(task_id, ext_ctx.instance_id)

    try:
        # 2. Fetch order
        order = await client.get_order(order_id)

        # 3. Check status — skip if not processing
        if order["status"] != "Processing":
            await ext_client.complete_task(task_id)
            return EventResponse.ok()

        # 4. Check if external client exists and is ready
        client_key = order["buyer"]["externalId"]
        external_client = await get_external_client(
            client_key,
            api_key=settings.external_api_key,
        )

        if external_client is None:
            # 4a. Client doesn't exist — create and reschedule
            await create_external_client(
                client_key,
                order["buyer"],
                api_key=settings.external_api_key,
            )
            await ext_client.update_task(task_id, payload={"progress": 50})
            await ext_client.reschedule_task(task_id)
            return EventResponse.reschedule(seconds=120)  # Retry in 2 min

        if not external_client["is_ready"]:
            # 4b. Client exists but not ready — reschedule
            await ext_client.update_task(task_id, payload={"progress": 30})
            await ext_client.reschedule_task(task_id)
            return EventResponse.reschedule(seconds=60)  # Retry in 1 min

        # 4c. Client ready — provision service
        service_id = await provision_service(
            order,
            client_key=client_key,
            api_key=settings.external_api_key,
        )

        # 5. Create subscription
        await client.create_subscription(
            order_id,
            external_service_id=service_id,
        )

        # 6. Complete order
        await client.complete_order(order_id)

        # 7. Complete task
        await ext_client.complete_task(task_id)

        return EventResponse.ok()

    except Exception as exc:
        await ext_client.reschedule_task(task_id)
        return EventResponse.reschedule(seconds=300)
```

## Best Practices

1. **Respect the timeout** — handlers have 30–60 seconds before the platform times out.
   - Quick work: complete synchronously and return `ok()`.
   - Slow work: `reschedule()` to resume later in another invocation.
2. **Always start the task** — call `ext_client.start_task(task_id, ext_ctx.instance_id)` at the beginning.
3. **Complete the task** — call `ext_client.complete_task(task_id)` when work finishes successfully.
4. **Report progress** — call `ext_client.update_task(task_id, payload={"progress": 0-100})` during work.
5. **Check state before acting** — order status, client readiness, etc. The same event may be delivered multiple times (see Pattern 2).
6. **Use filters** to receive only relevant events (reduces noise and unnecessary invocations).
7. **Return appropriate responses**:
   - `ok()` — work completed successfully.
   - `reschedule(seconds=N)` — transient failure or work in progress; platform retries after N seconds.
   - `cancel()` — permanent failure or intentional skip; no retries.

## Troubleshooting

- **Event not received**: Check that the `event` key matches the platform event name exactly.
- **All events received**: Verify your `condition` filter syntax.
- **Settings not interpolated**: Ensure `settings.yaml` contains the referenced values.
- **Path mismatch**: The `path` in `meta.yaml` must equal the router prefix (`/events`) plus the route decorator path.

## See Also

- [Project Structure](project-structure.md) — Repository layout
- [Platform Context](platform-context.md) — Extension development guide for agents
- [meta.yaml](../meta.yaml) — Extension manifest reference
- [schema.py](../backend/app/schema.py) — Complete model definitions
- [routers/events.py](../backend/app/routers/events.py) — Event router
