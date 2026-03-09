# Injectable Dependencies

This extension provides two key injectable dependencies for use in FastAPI route handlers: `AuthContext` and `InstallationClient`.

## AuthContext

The `AuthContext` dependency provides authentication and authorization information about the incoming request.

### Usage

```python
from app.auth import AuthContext

@router.get("/example")
async def example_endpoint(ctx: AuthContext):
    # Access authentication context
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

## InstallationClient

The `InstallationClient` dependency provides an authenticated HTTP client configured for the current installation's scope.

### Usage

```python
from app.auth import AuthContext
from app.client import InstallationClient

@router.get("/management/whoami")
async def whoami(ctx: AuthContext, client: InstallationClient):
    account = await client.get_account(ctx.account_id)
    user = None if not ctx.user_id else await client.get_user(ctx.user_id)
    token = None if not ctx.token_id else await client.get_token(ctx.token_id)

    return {
        "account": account,
        "token": token,
        "user": user,
    }
```

### How It Works

The `InstallationClient`:

1. Depends on `AuthContext` to get the `installation_id`
2. Creates or retrieves a cached `MPTClient` instance for that installation
3. Automatically handles token acquisition and refresh using the installation scope
4. Authenticates all requests with installation-scoped tokens
5. Provides a clean API for common Marketplace API operations

### Authentication Flow

The client implements automatic token management:

1. On first request, obtains an installation-scoped token from the Marketplace API
2. Caches the token and tracks its expiration
3. Automatically refreshes expired tokens before making requests
4. All API calls are authenticated in the context of the specific installation


## Why Two Dependencies?

- **`AuthContext`**: Provides "who is making the request" information
- **`InstallationClient`**: Provides "how to call the API on behalf of this installation" functionality

They work together: `AuthContext` identifies the caller, and `InstallationClient` uses that identity to create an authenticated API client scoped to the correct account/installation.
