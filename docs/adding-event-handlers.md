# Adding Event Handlers

This guide explains how to add new event handlers to your extension to receive and process platform events.

## Overview

Event handlers allow your extension to react to changes in the SoftwareOne Marketplace Platform. When a business object (order, subscription, agreement, etc.) changes state, the platform can notify your extension by sending an event to a designated endpoint.

## Step 1: Register the Event in meta.yaml

First, declare the event subscription in your [meta.yaml](../meta.yaml) file under the `events` section:

```yaml
events:
  - event: platform.commerce.order.status_changed
    condition: "and(eq(status,Processing),eq(product.id,{{ settings.product_id }}))"
    path: "/api/v1/events/orders"
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
platform.accounts.agreement.updated
platform.catalog.product.deleted
```

### Optional Filtering

You can optionally apply a filter using the `condition` field to receive only events matching specific criteria. The filter uses a function-based syntax and operates on the business object that triggered the event.

**Syntax:**

```yaml
condition: "and(eq(field,value),ne(other_field,value))"
```

**Available functions:**

- `eq(field, value)` — Equal to
- `ne(field, value)` — Not equal to
- `and(expr1, expr2, ...)` — Logical AND
- `or(expr1, expr2, ...)` — Logical OR

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

- `path`: The endpoint path in your extension that will receive the event (must match the route in [api.py](../backend/app/api.py))
- `task`: Set to `true` if the platform should create a task to track event processing

## Step 2: Add the Endpoint in api.py

Create a new POST endpoint in [backend/app/api.py](../backend/app/api.py) to receive the event:

```python
@router.post("/events/orders")
async def process_order(event: Event):
    # Your event processing logic here
    print(f"Received order event: {event.object.id}")
    print(f"Event type: {event.details.event_type}")
    
    # Return appropriate response
    return EventResponse.ok()
```

The endpoint path must match the `path` specified in `meta.yaml`.

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

## Complete Example

### meta.yaml

```yaml
events:
  - event: platform.commerce.subscription.status_changed
    condition: "eq(status,Active)"
    path: "/api/v1/events/subscriptions"
    task: true
```

### api.py

```python
from fastapi import APIRouter
from app.schema import Event, EventResponse

router = APIRouter(prefix="/api/v1")

@router.post("/events/subscriptions")
async def process_subscription_event(event: Event):
    """
    Handle subscription status change events.
    Only receives events for subscriptions that became Active (due to filter).
    """
    subscription_id = event.object.id
    event_type = event.details.event_type
    task_id = event.task.id if event.task else None
    
    print(f"Processing subscription {subscription_id}")
    print(f"Event: {event_type}")
    print(f"Task: {task_id}")
    
    try:
        # Your business logic here
        # e.g., provision resources, send notifications, update external systems
        
        # Success
        return EventResponse.ok()
        
    except TemporaryError:
        # Retry in 5 minutes
        return EventResponse.reschedule(seconds=300)
        
    except PermanentError:
        # Don't retry
        return EventResponse.cancel()
```

## Best Practices

1. **Use filters** to reduce noise and only receive relevant events
2. **Return appropriate responses**:
   - Use `OK` for successful processing
   - Use `Delay` for temporary failures (network issues, rate limits) or for long running process 
   - Use `Cancel` for permanent failures (invalid data, business rule violations) or to just skip the event
3. **Log event IDs** for troubleshooting and correlation with platform logs
4. **Enable task tracking** (`task: true`) for long-running or critical operations
5. **Handle idempotency** — the same event may be delivered multiple times
6. **Process quickly** — long-running operations should be offloaded to background tasks

## Troubleshooting

- **Event not received**: Check that the `event` key matches the platform event name exactly
- **All events received**: Verify your `condition` filter syntax
- **Settings not interpolated**: Ensure `settings.yaml` contains the referenced values
- **Path mismatch**: Confirm the `path` in meta matches the route decorator in api.py

## See Also

- [Project Structure](project-structure.md) — Understanding the codebase layout
- [meta.yaml](../meta.yaml) — Event configuration reference
- [schema.py](../backend/app/schema.py) — Complete model definitions
- [api.py](../backend/app/api.py) — API implementation examples
