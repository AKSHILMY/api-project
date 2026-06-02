# apikeys-platform

Async Python SDK for issuing, scoping, and validating API keys — backed by SQLite or PostgreSQL.

Designed for developers who want to add API key management to their own product without building the infrastructure from scratch.

## Installation

```bash
# SQLite (development / small deployments)
pip install "apikeys-platform[sqlite]"

# PostgreSQL (production)
pip install "apikeys-platform[postgresql]"

# Both drivers
pip install "apikeys-platform[all]"
```

Requires Python 3.11+.

## Quickstart

`create_tables` and `APIKeyClient` both accept plain URLs — no need to specify the async driver suffix:

```python
import asyncio
from apikeys import APIKeyClient, KeyMetadata, create_tables

async def main():
    # SQLite for dev:   "sqlite:///myapp.db"
    # PostgreSQL prod:  "postgresql://user:pass@host:5432/dbname"
    db_url = "sqlite:///myapp.db"
    await create_tables(db_url)   # creates tables on first run; safe to call on every restart
    client = APIKeyClient(db_url)

    # One-time setup
    org     = await client.create_organization("Acme Inc")
    product = await client.create_product(str(org.id), "My API")
    project = await client.create_project(str(org.id), "v1")
    await client.add_product_to_project(str(product.id), str(project.id))

    # Issue a key for one of your users
    result = await client.create_key(
        str(org.id),
        project_id=str(project.id),
        product_id=str(product.id),
        metadata=KeyMetadata(
            name="Alice's key",
            scopes=["read", "write"],
            rate_limit=1000,
            custom={"user_id": "u_alice", "plan": "pro"},
        ),
    )
    print(result.plaintext)   # return this once to your user

    # Validate an incoming request
    key = await client.validate_key(
        result.plaintext,
        product_id=str(product.id),
        required_scope="read",
    )
    print(key.metadata.custom["user_id"])   # → u_alice

asyncio.run(main())
```

## Key concepts

| Concept | Description |
|---------|-------------|
| **Organization** | Top-level tenant — maps to one of your customers or your own company |
| **Project** | Groups keys within an org (e.g. `v1`, `v2`, `mobile`) |
| **Product** | A named API surface linked to projects; keys can be scoped to one product |
| **`KeyMetadata.custom`** | Arbitrary JSON attached to a key — store `user_id`, `plan`, `tenant_id`, etc. |

Keys are scoped from broad → narrow: **org-wide → project-scoped → product-scoped**.  
`validate_key()` checks the key is active, matches the expected product, and holds the required scope.

## Exceptions

```python
from apikeys import InvalidKeyError, RevokedKeyError, InsufficientScopeError
```

| Exception | When raised |
|-----------|-------------|
| `InvalidKeyError` | Key not found |
| `RevokedKeyError` | Key exists but has been revoked |
| `InsufficientScopeError` | Key is valid but missing the required scope |

## Full example

See [`examples/acme_integration.py`](examples/acme_integration.py) for a complete end-to-end script showing setup, per-user key creation, request validation, and listing keys by user.

## License

MIT
# api-project
