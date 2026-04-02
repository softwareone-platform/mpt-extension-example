# Injectable Dependencies

This extension provides four key injectable dependencies for use in FastAPI route handlers: `AuthContext`, `ExtensionContext`, `InstallationClient`, and `ExtensionClient`.

## AuthContext

The `AuthContext` dependency provides authentication and authorization information about the incoming request.

### Usage

```python
from app.dependencies import AuthContext

@router.get("/example")
async def example_endpoint(ctx: AuthContext):
    print(ctx.account_id)
    print(ctx.installation_id)
    print(ctx.user_id)
```

### Available Properties

- **`account_id`** (`str`): The ID of the account making the request
- **`account_type`** (`str`): The type of account (e.g., Client, Operations, Vendor)
- **`installation_id`** (`str`): The ID of the extension installation for this account
- **`user_id`** (`str | None`): The ID of the user making the request (if user-based auth)
- **`token_id`** (`str | None`): The ID of the API token (if token-based auth)

### How It Works

The `AuthContext` dependency:

1. Extracts the JWT bearer token from the `Authorization` header
2. Decodes the JWT token claims
3. Extracts custom claims from the SoftwareOne namespace
4. If `installation_id` is not in the token, it resolves it by querying the Marketplace API
5. Returns a structured `AuthContext` object with all authentication details

## ExtensionContext

The `ExtensionContext` dependency provides runtime metadata about the running extension instance.

### Usage

```python
from app.dependencies import ExtensionContext

@router.post("/events/orders")
async def process_order(ext_ctx: ExtensionContext):
    instance_id = ext_ctx.instance_id
    extension_id = ext_ctx.extension_id
    return {"instance_id": instance_id, "extension_id": extension_id}
```

### Available Properties

- **`extension_id`** (`str`): The extension ID
- **`instance_id`** (`str`): The extension instance ID
- **`account_id`** (`str`): The vendor account ID
- **`domain`** (`str`): The platform domain for this runtime

### Common Use Cases

- Supplying `instance_id` when starting platform tasks: `ext_client.start_task(task_id, ext_ctx.instance_id)`
- Reading extension runtime metadata without parsing headers or config manually

## InstallationClient

The `InstallationClient` dependency provides an authenticated HTTP client configured for the current installation's scope. It acts on behalf of a specific customer installation.

### Usage

```python
from app.dependencies import InstallationClient

@router.get("/management/whoami")
async def whoami(client: InstallationClient, ctx: AuthContext):
    account = await client.get_account(ctx.account_id)
    user = None if not ctx.user_id else await client.get_user(ctx.user_id)
    token = None if not ctx.token_id else await client.get_token(ctx.token_id)

    return {
        "account": account,
        "token": token,
        "user": user,
    }
```

See [MPT Client](mpt-client.md) for detailed information on usage, extending the client, and other available methods.

## ExtensionClient

The `ExtensionClient` dependency provides an authenticated HTTP client configured for the vendor scope. It acts on behalf of the extension itself, not a specific installation.

### Usage

```python
from app.dependencies import ExtensionClient

@router.get("/vendor-data")
async def vendor_endpoint(client: ExtensionClient):
    user = await client.get_user(user_id)
    return user
```

See [MPT Client](mpt-client.md) for detailed information on usage, extending the client, and other available methods.

## Why Four Dependencies?

- **`AuthContext`**: Provides "who is making the request" information
- **`ExtensionContext`**: Provides "which extension runtime is executing" information
- **`InstallationClient`**: Provides "how to call the API on behalf of a specific customer installation" functionality
- **`ExtensionClient`**: Provides "how to call the API on behalf of the extension vendor" functionality

They work together: `AuthContext` identifies the caller, `ExtensionContext` identifies the running extension instance, `InstallationClient` uses caller identity to create an authorization-scoped API client, and `ExtensionClient` operates at the vendor level.
