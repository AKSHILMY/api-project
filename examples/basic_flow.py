"""
Basic SDK usage example.

Runs against a local SQLite file so no database setup is required.
Run with: .venv/bin/python examples/basic_flow.py
"""

import asyncio

from apikeys import APIKeyClient, KeyMetadata
from apikeys.db.session import create_tables

DB_URL = "sqlite+aiosqlite:///examples/basic_flow.db"


async def main() -> None:
    await create_tables(DB_URL)
    client = APIKeyClient(DB_URL)

    # --- organisation ---
    org = await client.create_organization("Acme Corp")
    print(f"org       {org.id}  {org.name}")

    # --- projects ---
    backend = await client.create_project(str(org.id), "Backend")
    mobile  = await client.create_project(str(org.id), "Mobile")
    print(f"project   {backend.id}  {backend.name}")
    print(f"project   {mobile.id}   {mobile.name}")

    # --- products ---
    analytics = await client.create_product(str(org.id), "Analytics")
    billing   = await client.create_product(str(org.id), "Billing")
    print(f"product   {analytics.id}  {analytics.name}")
    print(f"product   {billing.id}    {billing.name}")

    # --- link products → projects ---
    await client.add_product_to_project(str(analytics.id), str(backend.id))
    await client.add_product_to_project(str(billing.id),   str(backend.id))
    await client.add_product_to_project(str(analytics.id), str(mobile.id))

    # --- org-wide key (covers all projects and products) ---
    org_key = await client.create_key(str(org.id))
    print(f"\norg-wide key  {org_key.plaintext}")

    # --- project-scoped key (covers all products in Backend) ---
    backend_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        metadata=KeyMetadata(scopes=["read", "write"], rate_limit=1000),
    )
    print(f"\nbackend key  {backend_key.plaintext}")
    print(f"  scopes     {backend_key.key.metadata.scopes}")
    print(f"  rate limit {backend_key.key.metadata.rate_limit} req/min")

    # --- product-scoped key (Analytics only, read-only) ---
    analytics_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        product_id=str(analytics.id),
        metadata=KeyMetadata(scopes=["read"]),
    )
    print(f"\nanalytics key  {analytics_key.plaintext}")
    print(f"  scopes       {analytics_key.key.metadata.scopes}")

    # --- verify a key ---
    verified = await client.verify_key(backend_key.plaintext)
    print(f"\nverified  {verified.id}  active={verified.revoked_at is None}")

    # --- revoke a key ---
    await client.revoke_key(str(backend_key.key.id))
    revoked = await client.get_key(str(backend_key.key.id))
    print(f"revoked   {revoked.id}  revoked_at={revoked.revoked_at}")

    # --- list all keys for Backend project ---
    keys = await client.list_project_keys(str(backend.id))
    print(f"\nBackend project has {len(keys)} key(s)")
    for k in keys:
        status = "revoked" if k.revoked_at else "active"
        print(f"  {k.id}  {status}  scopes={k.metadata.scopes}")


if __name__ == "__main__":
    asyncio.run(main())
