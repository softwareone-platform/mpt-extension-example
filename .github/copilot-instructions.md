# Copilot Instructions — SoftwareOne Marketplace Platform Extension

Reference document for GitHub Copilot when working in this repository.

---

<!-- The block below mirrors LLM.md and is rewritten by `uv run python tools/sync-llm.py`. Edit LLM.md for shared content; edit this file only for the per-tool header above. -->

<!-- CONTENT -->
## Mandatory Development Checklist

- [ ] Follow Python 3.12 type annotations for Python code changes.
- [ ] Build frontend changes before finishing: `cd frontend && npm run build`.
- [ ] Lint relevant changes before finishing: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests before finishing.
- [ ] If you added or moved a plug, verify `meta.yaml` `href` matches an actual output file under `static/`.
- [ ] If you edited `LLM.md`, run `uv run python tools/sync-llm.py` to mirror it into `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md`.

---

## Architecture

- `backend/app/` is the stable core of the extension: `config.py` loads settings, `dependencies.py` provides request-scoped dependencies, `client.py` provides Marketplace API clients, `schema.py` defines request and response models, `extension.py` mounts the FastAPI app, and `routers/` contains one module per endpoint category.
- Each router module owns a distinct endpoint category:
  - `routers/events.py` (prefix `/events`) — platform event handlers
  - `routers/api.py` (prefix `/api/v1`) — authenticated REST endpoints
  - `routers/bypass.py` (prefix `/bypass`) — unauthenticated / internal endpoints
- `meta.yaml` and the matching router file must stay aligned. The `path` in `meta.yaml` must equal the router prefix plus the route decorator path. Always update both in the same change.
- `frontend/` is the source area for UI code, and `static/` is generated build output. Do not hand-edit `static/`. **Frontend-specific rules live in the [Frontend](#frontend) section below** — read it before editing anything under `frontend/`.

---

## Build and Test

```bash
# Backend setup
cd backend && uv sync

# Run the extension
runext
runext -r          # with auto-reload

# Lint and format
cd backend && uv run ruff check --fix . && uv run ruff format .

# Frontend (verify scaffold files exist before relying on these)
cd frontend && npm install && npm run build
cd frontend && npm run start   # watch mode

# Docker
docker compose build && docker compose run --rm bash
docker compose run --rm app

# Debug / traffic spy
mrok agent dev console
mrok agent dev web
```

---

## Code Style

- Python 3.12 type annotations on all functions, methods, and class attributes (except in `tests/`).
- Google-style docstrings for all public functions, methods, and classes.
- No inline comments — rely on clear naming and docstrings.
- All runtime configuration via `settings.yaml`, `.secrets.yaml`, or `EXT_*` environment variables through `app.config.settings`. Never hardcode secrets, API URLs, IDs, or environment-specific values.
- Prefer FastAPI dependency injection: use `AuthContext`, `InstallationClient`, `ExtensionClient`, and models from `app.schema` instead of ad-hoc auth parsing or raw HTTP clients.
- All request/response models must inherit `BaseSchema` from `app.schema`.
- All handlers must be `async def`.

---

## Conventions

- **Always add to the correct router** — never mix endpoint categories across router files.
- **`meta.yaml` + router must change together** — a path declared in the manifest that does not match a route causes silent delivery failure.
- **Do not edit `static/`** — it is overwritten by `npm run build`. Edit source in `frontend/src/`.
- **Do not commit `.secrets.yaml`** — it is git-ignored and must stay local.
- **Return typed response models** — avoid bare `dict` returns; define a `BaseSchema` subclass.
- **Shared agent-instructions content lives in `LLM.md`** — `CLAUDE.md`, `AGENTS.md`, and `.github/copilot-instructions.md` each carry per-tool headers plus a `<!-- CONTENT -->...<!-- /CONTENT -->` block mirrored from `LLM.md` by `uv run python tools/sync-llm.py` (stdlib-only, zero setup — run it after editing `LLM.md`). Touch a target file only for its own per-tool header above the marker; the marker block will be overwritten on the next sync.

---

## Common Failures → Diagnosis

| Symptom | First thing to check |
|---------|----------------------|
| Event / webhook / deferred / schedule handler never fires | `meta.yaml` `path` must equal router `prefix` + route decorator `path`. Mismatch = silent delivery failure. |
| Frontend plug fails to load in platform iframe | The `href` in `meta.yaml` must match an actual file under `static/` after `npm run build`. |
| `add-*` plug renders but shows the wrong socket | Every `add-*` plug needs its own per-socket bundle at `/static/add/{socket}.js`; see [Frontend → The `add` module](#the-add-module-per-socket-bundles). |
| UI looks unstyled, `var(--gray-1)` etc. resolve to nothing | `src/style.scss` is missing `@use '@softwareone-platform/sdk-react-ui-v0/design-tokens/style';`. The `design-tokens` subpath alone is Sass-side only; see [Frontend → Styling and design tokens](#styling-and-design-tokens). |
| Platform API call returns 401 | Use the injected `InstallationClient` / `ExtensionClient`; do not build raw `httpx` clients. |
| Config value is `None` at runtime | Values must come from `settings.yaml` / `.secrets.yaml` / `EXT_*` env vars via `app.config.settings`. Never hardcoded. |

---

## Frontend

Rules for code under `frontend/`. The patterns below assume you've absorbed the root sections above (Architecture, Code Style, Conventions). The frontend ships separately as bundled JS via esbuild; the platform loads each plug into an iframe.

### Mandatory checklist (frontend edits)

- [ ] Build before finishing: `cd frontend && npm run build`.
- [ ] Never hand-edit anything under `static/` — it is regenerated by esbuild.

### Stack

- React 19.2, react-router 7, TypeScript 5.9.
- esbuild (IIFE per module) + `esbuild-sass-plugin`.
- `@mpt-extension/sdk` + `@mpt-extension/sdk-react` for platform I/O.
- `@softwareone-platform/sdk-react-ui-v0` for UI (components + design tokens) — see "Design system MCP" below.

### Module layout

```
frontend/src/modules/
  {name}/index.tsx   →  /static/{name}.js   (auto-discovered by esbuild.config.js)
  add/index.tsx      →  /static/add/{socket}.js  (one bundle per socket; see below)
```

A module `{name}` is picked up automatically if `frontend/src/modules/{name}/index.tsx` exists. No build-config change needed to add a new static plug.

Minimal entry point:

```tsx
import { setup } from '@mpt-extension/sdk'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import App from './App'

setup((element) => {
  const root = createRoot(element)
  root.render(<BrowserRouter><App /></BrowserRouter>)
})
```

### The `add` module (per-socket bundles)

`frontend/src/modules/add` is special: it is reused by every `add-*` plug in `meta.yaml`, but each plug gets its own bundle with a different socket id baked in via the `__SOCKET_ID__` define.

Convention (enforced by `esbuild.config.js`):
- Every `add-*` plug in `meta.yaml` must have `href: /static/add/{socket}.js` where `{socket}` matches its `socket` field exactly.
- `esbuild.config.js` reads `meta.yaml`, picks every plug whose `href` starts with `/static/add/`, and emits one bundle per plug with `__SOCKET_ID__` set to the plug's socket.
- Adding a new `add-*` plug is a one-file change: append to `meta.yaml`. Do **not** touch `esbuild.config.js` for this.

Inside `add/App.tsx`, `__SOCKET_ID__` is a build-time string constant (declared in `frontend/src/globals.d.ts`). Do not reference `__SOCKET_ID__` from any module other than `add`.

### Render variants by socket type

`add/App.tsx` picks a layout based on the baked-in socket. This pattern is worth following in other multi-socket modules:

| Socket shape | Wrapper | Example |
|--------------|---------|---------|
| ends with `.actions` | `<div class="dialog">` with header + content + footer | `portal.commerce.orders.actions` |
| exactly `portal` | `<Card>` from `@softwareone-platform/sdk-react-ui-v0/card` | main navigation card |
| anything else (tabs, details) | plain `<div>` with no chrome | `portal.commerce.orders.order` |

Rule of thumb: `.actions` sockets open in a modal (platform provides the modal frame, the extension fills it with `dialog__*` classes). Detail tabs render inline. `portal` renders as a top-level card in the portal home.

### SDK hooks quick reference

From `@mpt-extension/sdk-react` (React 19):

- `useMPTContext<T>()` — subscribes to `window.__MPT__.context`; re-renders on platform context change. Use for order/account/subscription data pushed by the platform.
- `useMPTEmit()` — returns `(event, data?) => void`. Send events to platform.
- `useMPTListen(event, handler, deps?)` — subscribe to platform events; auto-cleanup on unmount.
- `useMPTModal()` — `{ open(id, { onClose?, context? }), close(data?) }`. `open` emits `$open`, `close` emits `$close`. `id` is the plug id from `meta.yaml`. See [Modal plugs](#modal-plugs) below for the open ↔ close contract and constraints.

From `@mpt-extension/sdk`:
- `setup(initializer)` — required entry wrapper; finds `#root`, throws if missing.
- `http` — preconfigured axios with automatic JWT refresh via `$requesttoken` / `$reporttoken`. Requests are relative to the extension's host. The `/public/v1/...` prefix is reserved: the platform transparently proxies it to the **platform API** (no platform domain in your code, no coupling to a specific platform instance). Any other path hits **this extension's own backend** at whatever routes it exposes — this example happens to use `/api/v1/...` (`backend/app/routers/api.py`), but the path layout is the extension's choice. The same JWT auths both.

Do not call `window.__MPT__` directly — always go through hooks / `http`.

### Modal plugs

Any plug can be opened in a platform-provided modal frame. The mechanism is symmetric:

- The **opener** (any plug) calls `useMPTModal().open(id, { onClose?, context? })` with the target plug id from `meta.yaml`.
- The **modal-side plug** is rendered into the modal frame and uses `useMPTContext()` to read the `context` payload (alongside the auto-filled auth context), and `useMPTModal().close(data?)` to return data to the opener.

Contract and constraints:
- `close(data)` is delivered **only** to the original opener's `onClose` callback — by design, no broadcast.
- A plug does not need a `socket` binding in `meta.yaml` to be modal-openable. A plug *with* a socket binding can still be opened as a modal — the two are independent.
- The platform modal frame has **no router** — `react-router` paths inside a modal-plug are unreliable. Keep modal-plug UIs flat (no nested routes).
- For in-modal layout use the `dialog__*` classes pattern from the [Render variants](#render-variants-by-socket-type) table (the platform supplies the modal frame; the extension fills it with header / content / actions).

### Styling and design tokens

`frontend/src/style.scss` is the shared root stylesheet. Every module entry point imports it (`import '../../style.scss'`); anything added there propagates to all bundles.

The design-system package exposes design tokens at **two** subpaths — you need both:

- `@use '@softwareone-platform/sdk-react-ui-v0/design-tokens' as *;` — Sass side: variables, placeholder selectors (`%regular2`, `%regular6`, …), mixins. Emits no CSS.
- `@use '@softwareone-platform/sdk-react-ui-v0/design-tokens/style';` — CSS side: the `:root { --gray-1: …; --spacing-1: 8px; … }` declarations and base `body`/`a` styles.

Skip the second one and every `var(--gray-1)` reference in the codebase silently resolves to nothing.

`@use` modules have their own scope — a partial that needs a placeholder like `%regular2` must `@use` design-tokens itself; it does not inherit the symbols from the file that includes it. From a nested partial (e.g. `frontend/src/fixes/*.scss`) use the `~`-prefix form: `@use '~@softwareone-platform/sdk-react-ui-v0/design-tokens' as *;`. `esbuild-sass-plugin` resolves bare npm specifiers reliably only from top-level files; the `~`-prefix forces its node-module resolver.

Do not introduce new `@import` rules — Sass `@import` is deprecated. `@use` for partials, side-effect imports for standalone CSS files (e.g. `import '../../fixes/modal-layout.scss'` in a `.tsx` entry).

### Design system MCP

This repo ships `.mcp.json` with the `swo-design-system` MCP server. Use it before touching UI:

1. `mcp__swo-design-system__list-components` — full catalogue of available components. Call first when unsure what exists.
2. `mcp__swo-design-system__get-component-readme` with the component name — API, props, examples. Call before using an unfamiliar component.

Do not guess imports or props for `@softwareone-platform/sdk-react-ui-v0/*`. Imports are always `@softwareone-platform/sdk-react-ui-v0/{component}` (singular, kebab-case).

### Recipe: add a new plug end-to-end

#### Static plug (one bundle, one socket)

1. Create `frontend/src/modules/{name}/index.tsx` (entry) and `frontend/src/modules/{name}/App.tsx` (component). Use the minimal entry-point template above.
2. Add to `meta.yaml`:
   ```yaml
   - id: {name}
     name: Human name
     description: What it does
     socket: portal.some.socket
     href: /static/{name}.js
   ```
3. `npm run build`. Verify `static/{name}.js` exists.

#### `add-*` plug (reuses the add module, per-socket bundle)

1. Append to `meta.yaml` under the existing `add-*` block:
   ```yaml
   - id: add-{slug}
     name: Plug here
     description: Add your extension plug
     socket: portal.some.new.socket
     href: /static/add/portal.some.new.socket.js
   ```
   The `href` must be exactly `/static/add/{socket}.js`.
2. `npm run build`. Verify `static/add/portal.some.new.socket.js` exists.

No changes to `esbuild.config.js` or `frontend/src/modules/add` are needed in either case.

### Frontend anti-patterns

- **Do not hand-edit `static/`** — overwritten by `npm run build`.
- **Do not reference `__SOCKET_ID__`** outside `frontend/src/modules/add`. It is only defined in builds of that module.
- **Do not call `window.__MPT__` directly** from components. Use SDK hooks.
- **Do not mix `dialog__*` classes with non-modal layouts** — `dialog__header/content/actions` assume the platform-provided modal frame.
- **Do not add a new entry to `esbuild.config.js`** for a new `add-*` plug — the config reads `meta.yaml`.
- **Do not hardcode the platform API base URL or JWT handling** — use `http` from `@mpt-extension/sdk`.
- **Do not `@use` design-tokens without also `@use`-ing `design-tokens/style`** — the first subpath is Sass-only; the second emits the `:root` CSS variables. Without it `var(--*)` references are dead.

---

## Docs Index

| Topic | File |
|-------|------|
| Extension overview and runtime model | `docs/platform-context.md` |
| Repository layout | `docs/project-structure.md` |
| Configuration and settings | `docs/settings.md` |
| AuthContext + Clients (Installation & Extension) | `docs/injectable-dependencies.md` |
| MPT Client and extending with custom methods | `docs/mpt-client.md` |
| Adding event handlers | `docs/adding-event-handlers.md` |
| Adding authenticated REST endpoints | `docs/adding-api-endpoints.md` |
| Adding unauthenticated endpoints | `docs/adding-unauthenticated-endpoints.md` |
<!-- /CONTENT -->
