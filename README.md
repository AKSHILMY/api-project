# apikeys-platform

Async Python SDK for issuing, scoping, and validating API keys — backed by SQLite, PostgreSQL, or MySQL.

Designed for developers who want to add API key management to their own product without building the infrastructure from scratch.

## Installation

```bash
# SQLite (development / small deployments)
pip install "apikeys-platform[sqlite]"

# PostgreSQL (production)
pip install "apikeys-platform[postgresql]"

# MySQL / MariaDB (production)
pip install "apikeys-platform[mysql]"

# With built-in FastAPI dependency
pip install "apikeys-platform[sqlite,fastapi]"

# Everything
pip install "apikeys-platform[all]"
```

Requires Python 3.11+.

## Quickstart

```python
import asyncio
from apikeys import APIKeyClient, KeyMetadata, RateLimit, RateLimitWindow, create_tables

async def main():
    db_url = "sqlite:///myapp.db"
    await create_tables(db_url)

    client = APIKeyClient(
        db_url,
        signing_secret="your-long-random-secret",  # required; use secrets.token_hex(32)
    )

    # Idempotent setup — safe to call on every deploy
    org, _     = await client.get_or_create_organization("Acme Inc")
    product, _ = await client.get_or_create_product(str(org.id), "My API")
    project, _ = await client.get_or_create_project(str(org.id), "v1")
    await client.add_product_to_project(str(product.id), str(project.id))

    # Issue a key for one of your users
    result = await client.create_key(
        str(org.id),
        project_id=str(project.id),
        product_id=str(product.id),
        metadata=KeyMetadata(
            name="Alice's key",
            scopes=["read", "write"],
            rate_limit=RateLimit(requests=1000, window=RateLimitWindow.minute),
            custom={"user_id": "u_alice", "plan": "pro"},
        ),
    )
    print(result.plaintext)   # return this once to your user — never stored in plaintext

    # Validate an incoming request
    key = await client.validate_key(
        result.plaintext,
        product_id=str(product.id),
        required_scopes=["read"],
    )
    print(key.metadata.custom["user_id"])   # → u_alice
    print(key.use_count)                    # → 1

asyncio.run(main())
```

## Key concepts

| Concept | Description |
|---------|-------------|
| **Organization** | Top-level tenant — your customer or your own company |
| **Project** | Groups keys within an org (e.g. `v1`, `mobile`) |
| **Product** | A named API surface; keys can be scoped to one product |
| **`signing_secret`** | HMAC key used to hash all API keys — required, never optional |
| **`KeyMetadata.custom`** | Arbitrary JSON attached to a key — store `user_id`, `plan`, etc. |

Keys are scoped broad → narrow: **org-wide → project-scoped → product-scoped**.

## Configurable key prefix

Keys are self-describing in logs. Configure `key_prefix` and `environment` at construction time:

```python
client = APIKeyClient(
    db_url,
    signing_secret="...",
    key_prefix="myapp",
    environment="live",   # "live" or "test"
)
# Keys look like: myapp_live_AbCdEfGh...
```

The default is `sk` with no environment segment, producing `sk_AbCdEfGh...`.

## Idempotent setup

`get_or_create_*` methods return `(entity, created: bool)` and are safe to call on every deploy:

```python
org, created = await client.get_or_create_organization("Acme")
project, _   = await client.get_or_create_project(str(org.id), "v1")
product, _   = await client.get_or_create_product(str(org.id), "My API")
```

Calling `create_organization` / `create_project` / `create_product` directly on a duplicate name raises `AlreadyExistsError` with the `existing_id` of the conflicting record:

```python
from apikeys import AlreadyExistsError

try:
    await client.create_organization("Acme")
except AlreadyExistsError as e:
    print(e.existing_id)   # UUID of the existing org
```

## Rate limiting

Attach a `RateLimit` to any key. `validate_key()` enforces it automatically:

```python
from apikeys import RateLimit, RateLimitWindow

meta = KeyMetadata(
    rate_limit=RateLimit(requests=100, window=RateLimitWindow.minute),
)
```

Windows: `second`, `minute`, `hour`, `day`.

When the limit is exceeded, `QuotaError` is raised with a `retry_after_seconds` value:

```python
from apikeys import QuotaError

try:
    await client.validate_key(plaintext)
except QuotaError as e:
    print(f"Retry after {e.retry_after_seconds}s")
```

Pass `check_rate_limit=False` to skip enforcement for high-throughput internal callers:

```python
await client.validate_key(plaintext, check_rate_limit=False)
```

## Expiry and error handling

`verify_key()` raises `ExpiredKeyError` (not `InvalidKeyError`) when a key has passed its `expires_at`. This lets callers show "your key expired — please rotate" instead of a generic invalid-key message:

```python
from apikeys import ExpiredKeyError, InvalidKeyError

try:
    await client.verify_key(plaintext)
except ExpiredKeyError as e:
    print(f"Expired at {e.expired_at}")   # carry exact expiry datetime
except InvalidKeyError:
    print("Key not found or malformed")
```

## Usage tracking

`verify_key()` and `validate_key()` update `last_used_at` and `use_count` on every call by default. Use this to detect abandoned keys that should be rotated:

```python
key = await client.get_key(key_id)
print(key.use_count)     # total successful verifications
print(key.last_used_at)  # last verification timestamp (UTC)
```

Opt out for maximum throughput:

```python
await client.verify_key(plaintext, track_usage=False)
```

## Key lifecycle

### Update metadata in-place

Change scopes, rate limit, or name without revoking and re-issuing:

```python
updated = await client.update_key(
    key_id,
    metadata=KeyMetadata(name="Upgraded key", scopes=["read", "write", "admin"]),
)
```

### Revoke vs delete

```python
# Soft-delete — disables the key; record kept for audit; future verify raises RevokedKeyError
await client.revoke_key(key_id)

# Hard-delete — permanently removes the record; use for GDPR erasure
await client.delete_key(key_id)
```

### Filter by status

```python
from apikeys import KeyStatus

active  = await client.list_project_keys(project_id, status=KeyStatus.active)
revoked = await client.list_project_keys(project_id, status=KeyStatus.revoked)
expired = await client.list_project_keys(project_id, status=KeyStatus.expired)
all_    = await client.list_project_keys(project_id, status=KeyStatus.all)  # default
```

## FastAPI integration

Install the `fastapi` extra, then use the built-in `APIKeyDepends` — no boilerplate needed:

```python
from apikeys import APIKeyDepends, APIKey
from fastapi import Depends, FastAPI, Request

app = FastAPI()

# Mount the client on request.state so APIKeyDepends can find it
@app.middleware("http")
async def attach_client(request: Request, call_next):
    request.state.apikeys_client = my_client
    return await call_next(request)

# Dependency — reads X-API-Key header and maps exceptions to HTTP responses
require_read = APIKeyDepends(required_scopes=["read"])

@app.get("/data")
async def get_data(key: APIKey = Depends(require_read)):
    return {"user": key.metadata.custom.get("user_id")}
```

`APIKeyDepends` maps exceptions automatically:

| Exception | HTTP status |
|-----------|-------------|
| Missing `X-API-Key` header | 401 |
| `InvalidKeyError` | 401 |
| `ExpiredKeyError` | 401 (includes expiry datetime in detail) |
| `RevokedKeyError` | 403 |
| `InsufficientScopeError` | 403 |
| `QuotaError` | 429 + `Retry-After` header |

See [`examples/fastapi_integration.py`](examples/fastapi_integration.py) for a complete runnable example.

## Exception reference

```python
from apikeys import (
    APIKeyError,           # base — catch-all
    InvalidKeyError,       # key not found or malformed
    ExpiredKeyError,       # key found but past expires_at  (.expired_at attribute)
    RevokedKeyError,       # key found but revoked
    InsufficientScopeError,# key valid but missing a required scope
    QuotaError,            # rate limit exceeded             (.retry_after_seconds attribute)
    AlreadyExistsError,    # name collision on create_*      (.existing_id attribute)
)
```

## Database setup

```python
from apikeys.db.session import create_tables

# Call once at startup — creates tables, safe to re-run
await create_tables("sqlite:///myapp.db")
await create_tables("postgresql://user:pass@host/db")
await create_tables("mysql://user:pass@host/db")
```

For existing deployments, run Alembic migrations instead:

```bash
alembic upgrade head
```

## Migrating from v0.1.x

v0.2 includes two breaking changes:

**1. `signing_secret` is now required.**

```python
# Before
client = APIKeyClient(db_url)

# After
client = APIKeyClient(db_url, signing_secret="your-secret")
```

All existing keys are invalidated because hashing changed from SHA-256 to HMAC-SHA256. You must re-issue all keys after upgrading.

**2. `rate_limit` on `KeyMetadata` changed from `int` to `RateLimit`.**

```python
# Before
KeyMetadata(rate_limit=1000)

# After
KeyMetadata(rate_limit=RateLimit(requests=1000, window=RateLimitWindow.minute))
```

## Examples

| File | What it shows |
|------|---------------|
| [`examples/basic_flow.py`](examples/basic_flow.py) | All SDK features end-to-end |
| [`examples/acme_integration.py`](examples/acme_integration.py) | Realistic multi-user integration |
| [`examples/fastapi_integration.py`](examples/fastapi_integration.py) | `APIKeyDepends` in a FastAPI app |
| [`examples/server/`](examples/server/) | Full FastAPI server with routers |

## License

MIT
