"""
Coachello integration example.

Shows how a developer embeds the apikeys SDK in their own backend
to issue and validate API keys for their own end-users.

Run:
    python examples/coachello_integration.py
"""
import asyncio

from apikeys import APIKeyClient, KeyMetadata
from apikeys.db.session import create_tables


async def main() -> None:
    DB_URL = "sqlite+aiosqlite:///examples/coachello_demo.db"
    await create_tables(DB_URL)
    client = APIKeyClient(DB_URL)

    # ── One-time setup (run once at deploy / seed time) ──────────────────────
    print("=== Setup ===")
    org = await client.create_organization("Coachello Inc")
    print(f"org_id:     {org.id}")

    product = await client.create_product(str(org.id), "Coachello")
    print(f"product_id: {product.id}")

    project = await client.create_project(str(org.id), "Coachello API v1")
    print(f"project_id: {project.id}")

    await client.add_product_to_project(str(product.id), str(project.id))
    print("Product linked to project ✓")

    # Store org.id / product.id / project.id in env vars — done once.
    ORG_ID = str(org.id)
    PRODUCT_ID = str(product.id)
    PROJECT_ID = str(project.id)

    # ── Per-user key creation (coachello-back: POST /user/apikeys) ───────────
    print("\n=== User Alice creates a key ===")
    alice = {"user_id": "u_alice", "email": "alice@example.com", "plan": "pro"}

    result = await client.create_key(
        ORG_ID,
        project_id=PROJECT_ID,
        product_id=PRODUCT_ID,
        metadata=KeyMetadata(
            name="Alice's production key",
            scopes=["coaching:read", "coaching:write"],
            rate_limit=1000,
            custom=alice,
        ),
    )
    print(f"key_id:    {result.key.id}")
    print(f"plaintext: {result.plaintext}  ← return this ONCE to the user")

    # ── Incoming request validation (coachello-back middleware) ──────────────
    print("\n=== Incoming request with Alice's key ===")
    key = await client.validate_key(
        result.plaintext,
        product_id=PRODUCT_ID,
        required_scope="coaching:read",
    )
    user_id = key.metadata.custom["user_id"]
    plan = key.metadata.custom["plan"]
    print(f"Authenticated as: {user_id}  (plan={plan})")
    print(f"Key name:         {key.metadata.name}")

    # ── List a user's own keys (filter client-side by custom.user_id) ────────
    print("\n=== Alice's keys ===")
    all_keys = await client.list_project_keys(PROJECT_ID)
    alice_keys = [k for k in all_keys if k.metadata.custom.get("user_id") == "u_alice"]
    for k in alice_keys:
        print(f"  {k.metadata.name}  [{k.id}]  revoked={k.revoked_at is not None}")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
