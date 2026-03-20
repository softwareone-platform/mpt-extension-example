# Adding Webhook Handlers

This guide explains how to add new validation webhook handlers to your extension.
Webhook handlers let the platform ask your extension to approve or reject a business object
before an operation completes (e.g., validating a draft order before it is submitted).

## Checklist

- [ ] Register the webhook in `meta.yaml` under `webhooks`.
- [ ] Add a `POST` handler in `backend/app/routers/webhooks.py`.
- [ ] Ensure the `path` in `meta.yaml` equals the router prefix (`/webhooks`) plus the route path.
- [ ] Add `criteria` in `meta.yaml` to limit which objects trigger this webhook.
- [ ] Return a validation response from `app.schema`.
- [ ] Follow Python 3.12 type annotations.
- [ ] Lint: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests.

## Overview

Validation webhooks are synchronous calls: the platform sends a `POST` request and waits for
your extension to approve or reject the object before continuing.  Unlike events, webhooks
require a prompt response — avoid long-running work inside the handler.

## Step 1: Register the Webhook in meta.yaml

Declare the webhook under the `webhooks` section of [meta.yaml](../meta.yaml):

```yaml
webhooks:
  - type: validatePurchaseOrderDraft
    description: "Draft order validation"
    path: /webhooks/orders/validate
    criteria:
      product.id: "{{ settings.product_id }}"
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `type` | yes | Platform webhook type identifier. |
| `description` | yes | Human-readable description shown in the platform UI. |
| `path` | yes | Full URL the platform calls. Must equal `/webhooks` + the route decorator path. |
| `criteria` | no | Key/value object-property filter. Only objects matching **all** criteria trigger the webhook. Supports Jinja2 references to `settings`. |

## Step 2: Add the Handler in routers/webhooks.py

Add a `POST` route to [backend/app/routers/webhooks.py](../backend/app/routers/webhooks.py).
The router carries the `/webhooks` prefix automatically:

```python
from app.schema import Event, EventResponse

# router is defined at module level with prefix="/webhooks"

@router.post("/orders/validate")  # full path: /webhooks/orders/validate
async def validate_order(event: Event) -> EventResponse:
    """Validate a draft purchase order before submission."""
    order_id = event.object.id

    if not passes_business_rules(order_id):
        return EventResponse.cancel()

    return EventResponse.ok()
```

The decorator path is relative to the router prefix.
`/webhooks` + `/orders/validate` = `/webhooks/orders/validate` must match `meta.yaml`.

## Response Options

| Method | Platform behaviour |
|--------|--------------------|
| `EventResponse.ok()` | Validation passed — platform continues the operation. |
| `EventResponse.cancel()` | Validation failed — platform blocks the operation. |
| `EventResponse.reschedule(seconds=N)` | Temporary failure — platform retries after N seconds. |

## Complete Example

### meta.yaml

```yaml
webhooks:
  - type: validatePurchaseOrderDraft
    description: "Block orders that exceed the credit limit"
    path: /webhooks/orders/validate
    criteria:
      product.id: "{{ settings.product_id }}"
```

### routers/webhooks.py

```python
from app.client import InstallationClient
from app.schema import Event, EventResponse


@router.post("/orders/validate")  # full path: /webhooks/orders/validate
async def validate_order(
    event: Event,
    client: InstallationClient,
) -> EventResponse:
    """Validate a draft purchase order against the account credit limit."""
    order = await client.get_order(event.object.id)
    account = await client.get_account(order["buyer"]["id"])

    if order["totalAmount"] > account["creditLimit"]:
        return EventResponse.cancel()

    return EventResponse.ok()
```

## Best Practices

1. **Respond quickly** — the platform waits for your reply; offload slow work to a deferred task.
2. **Use `criteria`** to narrow which objects trigger validations and reduce unnecessary calls.
3. **Use `EventResponse.reschedule`** only for genuine transient failures (e.g., downstream service unavailable).
4. **Do not mutate state** inside a webhook handler; reserve writes for event handlers.

## Troubleshooting

- **Webhook not triggered**: Verify `type` matches the platform webhook type exactly and `criteria` values are correct.
- **Path mismatch**: `meta.yaml` `path` must equal the full combined URL (`/webhooks` + `@router.post(...)` path).
- **Timeout**: Move any slow logic to a background deferred task and return `ok()` immediately.

## See Also

- [Adding Event Handlers](adding-event-handlers.md) — React to state changes asynchronously
- [Adding Deferred Handlers](adding-deferred-handlers.md) — Offload slow work to background tasks
- [Platform Context](platform-context.md) — Extension development guide for agents
- [meta.yaml](../meta.yaml) — Extension manifest reference
- [routers/webhooks.py](../backend/app/routers/webhooks.py) — Webhook router
