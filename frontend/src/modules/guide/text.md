# Building Extensions for SoftwareONE Marketplace

## What Is an Extension?

An Extension is a third-party web application whose UI plugs into the SoftwareONE Marketplace platform. Each Extension can contribute one or more **Plugs** — independent UI pieces, each targeting a named **Socket** (a predefined place in the platform UI, such as an order detail sidebar or a top-level navigation section). A Plug is a JavaScript bundle that the platform loads into an iframe when the corresponding Socket is rendered.

The three terms to remember: **Extension** is your app, **Socket** is where it appears, **Plug** is what you ship to fill that socket.

## Extension Structure

A typical extension has two parts:

- **Frontend** — React/TypeScript UI, organised as one module per Plug, each built into its own JS bundle.
- **Backend** — Python/FastAPI service handling platform events, validation webhooks, background tasks, scheduled jobs, and custom API endpoints.

A `meta.yaml` manifest at the project root ties everything together — it declares your Plugs, event subscriptions, webhooks, and schedules. The platform reads this manifest when your extension registers.

```
my-extension/
├── meta.yaml                # Manifest: plugs, events, webhooks, schedules
├── settings.yaml            # Configuration: extension ID, base URL, product ID
├── .secrets.yaml            # Credentials (git-ignored): API key
├── frontend/
│   ├── src/modules/
│   │   ├── orders/index.tsx       # Plug entry point → /static/orders.js
│   │   └── settings/index.tsx     # Plug entry point → /static/settings.js
│   ├── esbuild.config.js
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py          # Bootstrap: registers with platform, starts server
│   │   ├── extension.py     # FastAPI app, mounts routers
│   │   ├── config.py        # Loads settings.yaml + .secrets.yaml via Dynaconf
│   │   ├── auth.py          # JWT auth, provides AuthContext dependency
│   │   ├── client.py        # HTTP client for Marketplace API with auto-auth
│   │   ├── schema.py        # Pydantic models
│   │   └── routers/
│   │       ├── events.py    # Platform event handlers
│   │       ├── webhooks.py  # Validation webhooks
│   │       ├── deferreds.py # Background tasks
│   │       ├── schedules.py # Cron jobs
│   │       ├── api.py       # Your REST endpoints (authenticated)
│   │       └── bypass.py    # Internal/unauthenticated endpoints
│   └── pyproject.toml
├── Dockerfile
└── compose.yaml
```

## The Manifest: meta.yaml

The manifest is a Jinja2 template — you can reference values from `settings.yaml` using `{{ settings.xxx }}`. It declares everything your extension offers to the platform.

```yaml
version: 1.0.0

plugs:
  - id: order-sidebar
    socket: portal.commerce.orders.detail.sidebar
    name: Order Details
    description: Shows extended order information
    href: /static/orders.js
    condition: eq(product.id, {{ settings.product_id }})  # optional: only show for specific product

  - id: my-settings
    socket: portal.my-extension.settings
    name: Settings
    description: Extension configuration page
    href: /static/settings.js

events:
  - event: platform.commerce.order.status_changed
    path: /events/orders
    condition: "and(eq(status,Processing),eq(product.id,{{ settings.product_id }}))"
    task: true   # deliver asynchronously via deferrables

webhooks:
  - type: validatePurchaseOrderDraft
    description: Validates order drafts before submission
    path: /webhooks/validate-order
    criteria:
      product.id: "{{ settings.product_id }}"

deferrables:
  - path: /deferreds/sync-accounts
    method: POST
    description: Synchronises account data in background

schedules:
  - path: /schedules/daily-cleanup
    id: daily.cleanup
    name: Daily Cleanup
    description: Removes stale temporary data
    cron: "0 3 * * *"
```

Each plug entry maps a socket to a JS bundle. The `condition` field is optional — use it to restrict when the plug appears (e.g. only for a specific product). The `href` must point to a built bundle served by your extension's static files.

**Important**: the `path` values in events, webhooks, deferrables, and schedules must exactly match your FastAPI router prefix + route decorator path. For example, if your events router has `prefix="/events"` and a route `@router.post("/orders")`, the path in meta.yaml must be `/events/orders`. A mismatch causes silent delivery failure.

## Frontend: Building Plug UIs

### Setup and Entry Points

Each Plug has its own entry point under `frontend/src/modules/<name>/index.tsx`. The SDK provides a `setup()` function that receives the root DOM element — you render your app into it:

```tsx
import { setup } from '@mpt-extension/sdk'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { App } from './App'

setup((element) => {
  const root = createRoot(element)
  root.render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
})
```

You can optionally return a cleanup function from the callback (e.g. `() => root.unmount()`).

### Reading Platform Context

The platform passes context to your Plug — this includes data relevant to where the Plug is rendered (e.g. the current order, account, or product). Use `useMPTContext()` to access it reactively:

```tsx
import { useMPTContext } from '@mpt-extension/sdk-react'

function OrderInfo() {
  const { order, account } = useMPTContext()

  return (
    <div>
      <h2>Order {order.id}</h2>
      <p>Account: {account.name}</p>
    </div>
  )
}
```

The context updates automatically when the platform pushes changes — your component re-renders with fresh data.

### Making API Calls

The SDK provides `http`, a pre-configured axios instance. It automatically manages JWT authentication — requesting fresh tokens from the platform before they expire. Use it exactly like axios:

```tsx
import { http } from '@mpt-extension/sdk'

// Call your own extension backend
const response = await http.get('/api/v1/settings')

// Call the Marketplace API
const order = await http.get('https://api.s1.show/public/v1/commerce/orders/ORD-1234')
```

You never need to handle tokens manually — the SDK intercepts every request, checks if the current token is still valid (with a 60-second buffer), and transparently refreshes it if needed.

### Emitting Events to the Platform

Use `useMPTEmit()` to notify the platform about actions in your UI:

```tsx
import { useMPTEmit } from '@mpt-extension/sdk-react'

function ConfirmButton() {
  const emit = useMPTEmit()

  return (
    <button onClick={() => emit('confirmed', { orderId: 'ORD-1234' })}>
      Confirm
    </button>
  )
}
```

### Listening to Platform Events

Use `useMPTListen()` to react to events the platform sends to your Plug:

```tsx
import { useMPTListen } from '@mpt-extension/sdk-react'

function StatusTracker() {
  const [status, setStatus] = useState('unknown')

  useMPTListen('status-updated', (data) => {
    setStatus(data.status)
  }, [])

  return <span>Status: {status}</span>
}
```

The third argument is a dependency array (like `useEffect`). The listener is cleaned up automatically on unmount.

### Opening Modals

Modals are managed by the platform shell. You open them by ID, pass context data, and receive a result when they close:

```tsx
import { useMPTModal } from '@mpt-extension/sdk-react'

function Actions() {
  const modal = useMPTModal()

  const handleConfirm = () => {
    modal.open('confirm-dialog', {
      context: { orderId: 'ORD-1234', action: 'approve' },
      onClose: (result) => {
        if (result?.accepted) {
          // user confirmed
        }
      },
    })
  }

  return <button onClick={handleConfirm}>Approve Order</button>
}
```

Inside the modal Plug itself, call `modal.close(data)` to pass a result back:

```tsx
function ConfirmDialog() {
  const { orderId } = useMPTContext()
  const modal = useMPTModal()

  return (
    <div>
      <p>Approve order {orderId}?</p>
      <button onClick={() => modal.close({ accepted: true })}>Yes</button>
      <button onClick={() => modal.close({ accepted: false })}>No</button>
    </div>
  )
}
```

### Build Configuration

Frontend modules are built with esbuild. The config auto-discovers entry points and produces one IIFE bundle per module:

```js
// esbuild.config.js (simplified)
const entryPoints = glob.sync('./src/modules/*/index.tsx')

esbuild.build({
  entryPoints,
  outdir: '../static',
  bundle: true,
  format: 'iife',
  target: 'es2020',
  sourcemap: true,
  plugins: [sassPlugin({ loadPaths: ['node_modules'] })],
})
```

Run `npm run build` to produce bundles in the `/static` directory.

### Frontend Dependencies

```json
{
  "@mpt-extension/sdk": "0.0.4",
  "@mpt-extension/sdk-react": "0.0.4",
  "react": "^19.2.0",
  "react-dom": "^19.1.0",
  "react-router": "^7.13.0",
  "axios": "^1.10.0"
}
```

Optionally add `@softwareone-platform/sdk-react-ui-v0` for platform-consistent look and feel (components and design tokens ship in a single package).

## Backend: Handling Events and API

### Configuration

Extension configuration is managed by Dynaconf, loading from two files at the project root:

**settings.yaml** — public config, committed to git:
```yaml
env_domain: "s1.show"
base_url: "@format https://api.{this.env_domain}/public/v1"
extension_id: "EXT-1234-5678"
product_id: "PRD-1234-5678"
```

**.secrets.yaml** — credentials, git-ignored:
```yaml
api_key: "idt:EXT-1234-5678:your_secret_key_here"
```

Environment variables with `EXT_` prefix override any setting (e.g. `EXT_API_KEY`).

### Authentication

Incoming requests from the platform carry a JWT token. The `AuthContext` dependency extracts claims and makes them available in your handlers:

```python
from app.auth import AuthContext

@router.post("/orders")
async def handle_order(auth: AuthContext):
    print(auth.account_id)        # Account making the request
    print(auth.installation_id)   # Extension installation ID
    print(auth.user_id)           # User ID (if user-initiated)
```

AuthContext fields: `account_id`, `account_type`, `installation_id`, `user_id` (optional), `token_id` (optional).

### Calling the Marketplace API

The `InstallationClient` dependency provides an HTTP client pre-authenticated for the current installation:

```python
from app.client import InstallationClient

@router.post("/orders")
async def handle_order(auth: AuthContext, client: InstallationClient):
    order = await client.get("commerce/orders", "ORD-1234")
    user = await client.get_user(auth.user_id)

    # Paginate through collections
    async for order in client.get_orders(query="eq(status,Processing)"):
        print(order["id"])

    # Update resources
    await client.update("commerce/orders", "ORD-1234", {"notes": "Processed"})
```

Key client methods: `get()`, `create()`, `update()`, `delete()`, `get_page()`, `collection_iterator()`, and convenience methods like `get_order()`, `get_user()`, `get_account()`, `get_task()`, `complete_task()`.

### Event Handlers

Events are platform notifications delivered to your extension (e.g. order status changed). Define them in `meta.yaml` and implement matching routes:

```python
# backend/app/routers/events.py
from app.schema import Event, EventResponse

router = APIRouter(prefix="/events")

@router.post("/orders")
async def process_order(event: Event, client: InstallationClient):
    order = await client.get_order(event.object.id)

    if order["status"] == "Processing":
        # Do your business logic
        await client.complete_task(event.task.id, {"output": "done"})
        return EventResponse.ok()

    return EventResponse.reschedule(seconds=60)  # retry later
```

`EventResponse` has three factory methods: `.ok()`, `.cancel()`, `.reschedule(seconds)`.

### Validation Webhooks

Webhooks let you validate platform operations before they happen (e.g. reject invalid order drafts):

```python
# backend/app/routers/webhooks.py
router = APIRouter(prefix="/webhooks")

@router.post("/validate-order")
async def validate_order(request: Request):
    body = await request.json()
    order = body.get("order", {})

    if not order.get("notes"):
        return {"status": "failed", "message": "Notes are required"}

    return {"status": "success"}
```

### Background Tasks and Schedules

Deferrables handle async work; schedules run on cron. Both follow the same router pattern:

```python
# backend/app/routers/deferreds.py
router = APIRouter(prefix="/deferreds")

@router.post("/sync-accounts")
async def sync_accounts(client: InstallationClient):
    async for account in client.collection_iterator("accounts"):
        # sync logic
        pass
    return {"status": "completed"}
```

```python
# backend/app/routers/schedules.py
router = APIRouter(prefix="/schedules")

@router.post("/daily-cleanup")
async def daily_cleanup(client: ExtensionClient):
    # cleanup logic
    return {"status": "completed"}
```

### Backend Bootstrap

The entry point `runext` (defined in `pyproject.toml`) runs `app/main.py`, which:

1. Validates required settings (`extension_id`, `base_url`, `api_key`)
2. Renders `meta.yaml` (Jinja2 template with settings)
3. Registers the extension instance with the platform API
4. Saves an identity file for secure networking (OpenZiti)
5. Starts the FastAPI server

### Running with Docker

```yaml
# compose.yaml
services:
  app:
    build: .
    working_dir: /workspace
    volumes:
      - .:/workspace
    command: runext
```

```bash
docker compose up app        # start the extension
docker compose run bash      # shell into container for debugging
```

## Getting Started

1. Clone `mpt-extension-example` as your starting point.
2. Update `settings.yaml` with your extension ID and product ID.
3. Add your API key to `.secrets.yaml`.
4. Define your Plugs, events, and webhooks in `meta.yaml`.
5. Create a frontend module under `frontend/src/modules/<plug-name>/index.tsx` for each Plug.
6. Implement backend handlers in the matching routers.
7. Run `npm run build` in `/frontend` to produce JS bundles.
8. Run `runext` (or `docker compose up`) to register and start your extension.

The `mpt-extension-example` and `github.mextmock` repositories are working references — read their `meta.yaml` and browse their frontend modules and backend routers to see every pattern in action.
