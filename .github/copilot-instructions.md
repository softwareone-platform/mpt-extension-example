# Project Guidelines

## Mandatory Development Checklist

[ ] - Follow Python 3.12 type annotations for Python code changes.
[ ] - Build frontend changes before finishing: `cd frontend && npm run build`.
[ ] - Lint relevant changes before finishing.
[ ] - Test relevant changes before finishing.

## Architecture

- `backend/app/` is the stable core of the extension: `config.py` loads settings, `auth.py` and `client.py` provide request-scoped dependencies, `schema.py` defines request and response models, `extension.py` mounts the FastAPI app, and `routers/` contains one module per endpoint category.
- Each router module owns a distinct endpoint category — `routers/events.py` (prefix `/events`) for platform events, `routers/webhooks.py` (prefix `/webhooks`) for validation webhooks, `routers/deferreds.py` (prefix `/deferreds`) for deferred background tasks, `routers/schedules.py` (prefix `/schedules`) for scheduled jobs, `routers/api.py` (prefix `/api/v1`) for authenticated REST endpoints, and `routers/bypass.py` (prefix `/bypass`) for unauthenticated/internal endpoints. Add handlers to the matching router, never mix categories.
- `meta.yaml` and the matching router file must stay aligned. When adding or changing events, webhooks, deferrables, or schedules, update both the manifest path and the matching `@router` decorator in the same change. The `path` in `meta.yaml` must equal the router prefix plus the route decorator path.
- `frontend/` is the source area for UI code, and `static/` is generated build output served by the backend at `/static`. Do not hand-edit `static/` unless the task is explicitly about generated assets.

## Code Style

- Follow `backend/pyproject.toml` for Python quality rules. Keep Python code explicit, typed with Python 3.12 annotations, async where appropriate, and documented with Google-style docstrings for public APIs.
- All runtime configuration must come from `settings.yaml`, `.secrets.yaml`, or `EXT_*` environment variables through `app.config.settings`. Do not hardcode secrets, API URLs, IDs, or environment-specific values.
- Prefer FastAPI dependency injection and the existing abstractions: use `AuthContext`, `InstallationClient`, `ExtensionClient`, and models from `app.schema` instead of ad-hoc auth parsing, direct HTTP clients in route handlers, or loose dict payload handling.

## Build and Test

- Backend setup: `cd backend && uv sync`
- Run the extension: `runext` or `runext -r`
- Lint and format backend code: `cd backend && uv run ruff check --fix . && uv run ruff format .`
- Docker workflow is documented in `README.md`, `Dockerfile`, and `compose.yaml`.
- Frontend commands described in `README.md` assume the frontend scaffold is implemented. Verify `frontend/package.json`, `frontend/tsconfig.json`, and `frontend/esbuild.config.js` before relying on `npm run build` or `npm run start`.

## Conventions

- Treat the docs as the source of truth for extension patterns: see `docs/project-structure.md`, `docs/settings.md`, `docs/platform-context.md`, `docs/injectable-dependencies.md`, `docs/mpt-client.md`, `docs/adding-event-handlers.md`, `docs/adding-webhook-handlers.md`, `docs/adding-deferred-handlers.md`, `docs/adding-scheduled-handlers.md`, `docs/adding-api-endpoints.md`, and `docs/adding-unauthenticated-endpoints.md`.
- Keep route handlers async and use typed Pydantic models from `app.schema`. Extend existing schema patterns before introducing new request or response shapes.
- Generated or local-only files should stay out of source edits unless required by the task: `.secrets.yaml`, `*_identity.json`, and `static/` are not the primary source files.