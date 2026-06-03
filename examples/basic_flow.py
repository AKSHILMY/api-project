"""
Basic SDK usage example — covers all v0.2 features.

Runs against a local SQLite file; no database setup required.
Run with:  .venv/bin/python examples/basic_flow.py
"""

import asyncio
from datetime import datetime, timedelta, timezone

from apikeys import (
    APIKeyClient,
    KeyMetadata,
    KeyStatus,
    RateLimit,
    RateLimitWindow,
)
from apikeys.db.session import create_tables
from apikeys.exceptions import ExpiredKeyError, QuotaError, RevokedKeyError

DB_URL = "sqlite+aiosqlite:///examples/basic_flow.db"

# signing_secret is required — use a long random value in production (e.g. secrets.token_hex(32))
SECRET = "dev-secret-change-me-in-production"


async def main() -> None:
    await create_tables(DB_URL)

    client = APIKeyClient(
        DB_URL,
        signing_secret=SECRET,
        key_prefix="acme",      # keys will look like acme_live_<token>
        environment="live",
    )

    # ── Idempotent org/project/product setup ─────────────────────────────────
    # get_or_create_* is safe to call on every deploy — no duplicates.
    org, org_created = await client.get_or_create_organization("Acme Corp")
    print(f"org       {org.id}  {'created' if org_created else 'existing'}")

    backend, _ = await client.get_or_create_project(str(org.id), "Backend")
    mobile, _  = await client.get_or_create_project(str(org.id), "Mobile")

    analytics, _ = await client.get_or_create_product(str(org.id), "Analytics")
    billing, _   = await client.get_or_create_product(str(org.id), "Billing")

    await client.add_product_to_project(str(analytics.id), str(backend.id))
    await client.add_product_to_project(str(billing.id),   str(backend.id))
    await client.add_product_to_project(str(analytics.id), str(mobile.id))

    print(f"project   {backend.id}  {backend.name}")
    print(f"project   {mobile.id}   {mobile.name}")

    # ── Create keys with different scopes ────────────────────────────────────
    org_key = await client.create_key(str(org.id))
    print(f"\norg-wide key  {org_key.plaintext}")

    # Rate-limited project key: 100 requests per minute
    backend_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        metadata=KeyMetadata(
            name="Backend service key",
            scopes=["read", "write"],
            rate_limit=RateLimit(requests=100, window=RateLimitWindow.minute),
        ),
    )
    print(f"\nbackend key     {backend_key.plaintext}")
    print(f"  scopes        {backend_key.key.metadata.scopes}")
    print(f"  rate limit    {backend_key.key.metadata.rate_limit.requests} req/{backend_key.key.metadata.rate_limit.window.value}")

    # Short-lived analytics key — expires in 1 hour
    analytics_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        product_id=str(analytics.id),
        metadata=KeyMetadata(
            name="Temp analytics key",
            scopes=["read"],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        ),
    )
    print(f"\nanalytics key   {analytics_key.plaintext}")
    print(f"  expires       {analytics_key.key.metadata.expires_at}")

    # ── Verify a key (track_usage=True by default) ───────────────────────────
    verified = await client.verify_key(backend_key.plaintext)
    print(f"\nverify        ok  use_count={verified.use_count}")

    verified2 = await client.verify_key(backend_key.plaintext)
    print(f"verify again  ok  use_count={verified2.use_count}")

    # ── Rate limit demonstration ──────────────────────────────────────────────
    small_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        metadata=KeyMetadata(
            rate_limit=RateLimit(requests=2, window=RateLimitWindow.minute)
        ),
    )
    print(f"\nrate-limit demo (limit=2/min)")
    for i in range(3):
        try:
            await client.validate_key(small_key.plaintext, track_usage=False)
            print(f"  call {i+1}: ok")
        except QuotaError as e:
            print(f"  call {i+1}: QuotaError — retry after {e.retry_after_seconds}s")

    # ── Expiry: ExpiredKeyError is distinct from InvalidKeyError ─────────────
    expired_key = await client.create_key(
        str(org.id),
        project_id=str(backend.id),
        metadata=KeyMetadata(
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
        ),
    )
    try:
        await client.verify_key(expired_key.plaintext)
    except ExpiredKeyError as e:
        print(f"\nExpiredKeyError  expired_at={e.expired_at}")

    # ── Update key metadata in-place ─────────────────────────────────────────
    updated = await client.update_key(
        str(analytics_key.key.id),
        metadata=KeyMetadata(name="Renewed analytics key", scopes=["read", "write"]),
    )
    print(f"\nupdated key  name={updated.metadata.name}  scopes={updated.metadata.scopes}")

    # ── Revoke vs delete ──────────────────────────────────────────────────────
    # revoke_key: soft-delete; record kept for audit; future verify raises RevokedKeyError
    revoked = await client.revoke_key(str(backend_key.key.id))
    print(f"\nrevoked  {revoked.id}  revoked_at={revoked.revoked_at}")

    try:
        await client.verify_key(backend_key.plaintext)
    except RevokedKeyError:
        print("verify revoked key → RevokedKeyError ✓")

    # delete_key: permanent erasure (GDPR, test cleanup)
    await client.delete_key(str(small_key.key.id))
    print("deleted small_key permanently")

    # ── List with KeyStatus filter ────────────────────────────────────────────
    all_keys     = await client.list_project_keys(str(backend.id))
    active_keys  = await client.list_project_keys(str(backend.id), status=KeyStatus.active)
    revoked_keys = await client.list_project_keys(str(backend.id), status=KeyStatus.revoked)

    print(f"\nBackend project keys: {len(all_keys)} total  "
          f"{len(active_keys)} active  {len(revoked_keys)} revoked")
    for k in all_keys:
        flag = "revoked" if k.revoked_at else "active"
        print(f"  [{flag}]  {k.metadata.name or '(unnamed)'}  "
              f"use_count={k.use_count}  last_used={k.last_used_at}")


if __name__ == "__main__":
    asyncio.run(main())
