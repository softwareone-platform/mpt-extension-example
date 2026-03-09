# Settings

This project uses centralized settings loaded with `dynaconf`.

## 1) Access settings in code

Settings are initialized in [backend/app/config.py](../backend/app/config.py) and exposed as `settings`.

```python
from app.config import settings

base_url = settings.base_url
extension_id = settings.extension_id
rows_per_page = settings.rows_per_page
```

The `settings` object is a Dynaconf `LazySettings` instance, so you can access values with attribute syntax (for example `settings.base_url`).

## 2) Settings library (Dynaconf)

- Library: `dynaconf`
- Package reference in project: [backend/pyproject.toml](../backend/pyproject.toml)
- Documentation: https://www.dynaconf.com/

In this project, Dynaconf is configured with:

- `root_path` = repository root
- `settings_files` = `settings.yaml` and `.secrets.yaml`

This means public/non-sensitive values live in `settings.yaml`, while sensitive values (for example `api_key`) should live in `.secrets.yaml`.

## 3) Current app settings

From [settings.yaml](../settings.yaml):

- `env_domain`: `s1.show`
- `base_url`: `https://api.{env_domain}/public/v1` (computed)
- `extension_id`: `EXT-0190-5415`
- `extension_domain`: `ext.{env_domain}` (computed)
- `extension_fqdn`: `{extension_id.lower()}.{extension_domain}` (computed)
- `product_id`: `PRD-1512-9546`
- `rows_per_page`: `50`

Notes:

- `base_url`, `extension_domain`, and `extension_fqdn` are dynamically computed by Dynaconf using `@format` / `@jinja`.
- Additional secret settings (such as `api_key`) are expected in `.secrets.yaml`.

## 4) Override settings via environment variables

Dynaconf supports overriding settings from environment variables.

Use the `EXT_` prefix plus the setting name in uppercase:

```bash
export EXT_ENV_DOMAIN=s1.dev
export EXT_EXTENSION_ID=EXT-0000-0001
export EXT_ROWS_PER_PAGE=100
```

After exporting these variables, `settings.env_domain`, `settings.extension_id`, and `settings.rows_per_page` use the environment values at runtime.

Example (one command run):

```bash
EXT_ROWS_PER_PAGE=200 runext -r
```

For secrets, you can also use env vars instead of `.secrets.yaml`, for example:

```bash
export EXT_API_KEY=<your-extension-secret>
```
