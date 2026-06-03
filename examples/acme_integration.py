"""
Acme Corp integration example.

Shows how a developer embeds the apikeys SDK in their own backend
to issue and validate API keys for their end-users.

Run:
    python examples/acme_integration.py
"""
import asyncio

from apikeys import (
    APIKeyClient,
    KeyMetadata,
    KeyStatus,
    RateLimit,
    RateLimitWindow,
)
from apikeys.db.session import create_tables
from apikeys.exceptions import (
    AlreadyExistsError,
    ExpiredKeyError,
    InsufficientScopeError,
    QuotaError,
    RevokedKeyError,
)


async def main() -> None:
    DB_URL = "sqlite+aiosqlite:///examples/acme_demo.db"
    await create_tables(DB_URL)

    client = APIKeyClient(
        DB_URL,
        signing_secret="acme-signing-secret-change-in-prod",
        key_prefix="acme",
        environment="live",
    )

    # ── One-time setup — idempotent, safe to re-run on every deploy ──────────
    print("=== Setup ===")
    org, org_created = await client.get_or_create_organization("Acme Corp")
    print(f"org_id:     {org.id}  ({'created' if org_created else 'already existed'})")

    product, _ = await client.get_or_create_product(str(org.id), "Acme App")
    print(f"product_id: {product.id}")

    project, _ = await client.get_or_create_project(str(org.id), "Acme API v1")
    print(f"project_id: {project.id}")

    await client.add_product_to_project(str(product.id), str(project.id))
    print("Product linked to project ✓")

    ORG_ID     = str(org.id)
    PRODUCT_ID = str(product.id)
    PROJECT_ID = str(project.id)

    # Demonstrate that a duplicate org name raises AlreadyExistsError
    try:
        await client.create_organization("Acme Corp")
    except AlreadyExistsError as e:
        print(f"Duplicate org blocked → existing_id={e.existing_id} ✓")

    # ── Per-user key creation (your backend: POST /user/apikeys) ─────────────
    print("\n=== User Alice creates a key ===")
    alice = {"user_id": "u_alice", "email": "alice@example.com", "plan": "pro"}

    result = await client.create_key(
        ORG_ID,
        project_id=PROJECT_ID,
        product_id=PRODUCT_ID,
        metadata=KeyMetadata(
            name="Alice's production key",
            scopes=["read", "write"],
            rate_limit=RateLimit(requests=1000, window=RateLimitWindow.minute),
            custom=alice,
        ),
    )
    print(f"key_id:    {result.key.id}")
    print(f"plaintext: {result.plaintext}  ← return this ONCE to the user")

    # ── Incoming request validation (your backend middleware) ─────────────────
    print("\n=== Incoming request with Alice's key ===")
    key = await client.validate_key(
        result.plaintext,
        product_id=PRODUCT_ID,
        required_scopes=["read"],          # list — check all required scopes at once
    )
    user_id = key.metadata.custom["user_id"]
    plan    = key.metadata.custom["plan"]
    print(f"Authenticated as: {user_id}  (plan={plan})")
    print(f"Key name:         {key.metadata.name}")
    print(f"Use count:        {key.use_count}")
    print(f"Last used at:     {key.last_used_at}")

    # Missing scope → InsufficientScopeError
    try:
        await client.validate_key(result.plaintext, required_scopes=["admin"])
    except InsufficientScopeError as e:
        print(f"\nMissing scope → {e} ✓")

    # ── Update key scopes in-place (no revoke + re-issue needed) ─────────────
    print("\n=== Upgrade Alice to admin ===")
    updated = await client.update_key(
        str(result.key.id),
        metadata=KeyMetadata(
            name="Alice's production key",
            scopes=["read", "write", "admin"],
            rate_limit=RateLimit(requests=1000, window=RateLimitWindow.minute),
            custom=alice,
        ),
    )
    print(f"New scopes: {updated.metadata.scopes}")

    # ── List active keys — revoked keys excluded ──────────────────────────────
    print("\n=== Alice's active keys ===")
    active_keys = await client.list_project_keys(PROJECT_ID, status=KeyStatus.active)
    alice_keys  = [k for k in active_keys if k.metadata.custom.get("user_id") == "u_alice"]
    for k in alice_keys:
        print(f"  {k.metadata.name}  [{k.id}]  use_count={k.use_count}")

    # ── Revoke (soft-delete, keeps audit trail) ───────────────────────────────
    print("\n=== Alice revokes her key ===")
    await client.revoke_key(str(result.key.id))

    try:
        await client.validate_key(result.plaintext)
    except RevokedKeyError:
        print("Key is revoked — RevokedKeyError raised ✓")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
