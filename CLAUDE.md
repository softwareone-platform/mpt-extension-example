# CLAUDE.md — SoftwareOne Marketplace Platform Extension

Reference document for Claude Code agents working in this repository.

---

## Mandatory Development Checklist

- [ ] Follow Python 3.12 type annotations for Python code changes.
- [ ] Build frontend changes before finishing: `cd frontend && npm run build`.
- [ ] Lint relevant changes before finishing: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- [ ] Run tests before finishing.

---

## Architecture

- `backend/app/` is the stable core of the extension: `config.py` loads settings, `auth.py` and `client.py` provide request-scoped dependencies, `schema.py` defines request and response models, `extension.py` mounts the FastAPI app, and `routers/` contains one module per endpoint category.
- Each router module owns a distinct endpoint category:
  - `routers/events.py` (prefix `/events`) — platform event handlers
  - `routers/webhooks.py` (prefix `/webhooks`) — validation webhooks
  - `routers/deferreds.py` (prefix `/deferreds`) — deferred background tasks
  - `routers/schedules.py` (prefix `/schedules`) — scheduled cron jobs
  - `routers/api.py` (prefix `/api/v1`) — authenticated REST endpoints
  - `routers/bypass.py` (prefix `/bypass`) — unauthenticated / internal endpoints
- `meta.yaml` and the matching router file must stay aligned. The `path` in `meta.yaml` must equal the router prefix plus the route decorator path. Always update both in the same change.
- `frontend/` is the source area for UI code, and `static/` is generated build output. Do not hand-edit `static/`.

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
| Adding webhook handlers | `docs/adding-webhook-handlers.md` |
| Adding deferred handlers | `docs/adding-deferred-handlers.md` |
| Adding scheduled handlers | `docs/adding-scheduled-handlers.md` |
| Adding authenticated REST endpoints | `docs/adding-api-endpoints.md` |
| Adding unauthenticated endpoints | `docs/adding-unauthenticated-endpoints.md` |
