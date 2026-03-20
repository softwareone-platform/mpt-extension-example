# MPT Client

The `MPTClient` is an authenticated HTTP client that consumes the SoftwareOne Marketplace Platform (MPT) API. It operates in two scopes:

1. **Vendor-scoped** (`ExtensionClient`) — acts on behalf of the extension itself
2. **Installation-scoped** (`InstallationClient`) — acts on behalf of a specific customer installation (account)

## Scopes

### Installation Scope

An **installation** represents a specific account's instance of your extension. When a client or vendor installs your extension in their Marketplace account, a unique installation is created. Each installation has:

- A unique installation ID
- Installation-scoped permissions
- Installation-scoped authentication tokens
- Access to resources owned by or accessible to that account

Use `InstallationClient` when you need to perform actions in the context of a account's installation.

### Vendor Scope

The **vendor scope** represents the extension itself. Use `ExtensionClient` when you need to perform actions that belong to the vendor, such as managing tasks for an extension.

## Purpose

The `MPTClient` provides:

1. **Scoped Authentication**: All API calls are authenticated in the correct scope (vendor or installation)
2. **Automatic Token Management**: Handles token acquisition, caching, and renewal automatically (installation-scoped only)
3. **Convenient API Methods**: Common operations (get, create, delete, iterate) with proper error handling
4. **Resource Lifecycle**: Proper async context management for HTTP connections

## Basic Usage

### Installation-Scoped (Via Dependency Injection)

```python
from app.client import InstallationClient

@router.get("/my-endpoint")
async def my_endpoint(client: InstallationClient):
    # Client is already configured for the current installation
    account = await client.get_account(ctx.account_id)
    return account
```

### Vendor-Scoped (Via Dependency Injection)

```python
from app.client import ExtensionClient

@router.get("/vendor-endpoint")
async def vendor_endpoint(client: ExtensionClient):
    # Client is authenticated as the extension
    user = await client.get_user(user_id)
    return user
```

### Via Utility Function

```python
from app.client import get_installation_client

async def process_data(account_id: str):
    client = get_installation_client(account_id)
    async for order in client.get_orders(query="eq(status,Completed)", select=["-agreement"]):
        # do something with the order
```

## Extending the Client

The `MPTClient` provides base methods that you can compose to build domain-specific functionality for your extension. Add custom methods directly to the `MPTClient` class in [backend/app/client.py](../backend/app/client.py).

### Base Methods Available

- **`get(endpoint, id, select)`** - Fetch a single resource
- **`create(endpoint, payload)`** - Create a new resource
- **`update(endpoint, id, payload)`** - Update an existing resource
- **`delete(endpoint, id)`** - Delete a resource
- **`get_page(endpoint, limit, offset, query, select)`** - Fetch a paginated page
- **`collection_iterator(endpoint, query, select)`** - Iterate over all items in a collection

### Example: Adding Custom Methods

```python
class MPTClient:
    # ... existing base methods ...

    async def update_task(self, task_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update a task with the given changes."""
        return await self.update("system/tasks", task_id, updates)

    def get_orders(
        self, query: str | None = None, select: list[str] | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        return self.collection_iterator("commerce/orders", query=query, select=select)
```

By composing these base methods, you can create a clean, reusable API tailored to your extension's domain without modifying the dependency injection setup.
