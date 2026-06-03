from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apikeys import APIKeyClient, APIKeyCreated, KeyMetadata, KeyStatus, RateLimit, RateLimitWindow
from apikeys.db.base import Base
from apikeys.exceptions import APIKeyError, ExpiredKeyError, InvalidKeyError, QuotaError, RevokedKeyError

_SECRET = "test-signing-secret"


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return APIKeyClient(_sessions=sessions, signing_secret=_SECRET)


@pytest_asyncio.fixture
async def org_and_project(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    return org, project


@pytest_asyncio.fixture
async def org_project_product(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    product = await client.create_product(str(org.id), "Analytics")
    await client.add_product_to_project(str(product.id), str(project.id))
    return org, project, product


@pytest.mark.asyncio
async def test_create_project_scoped_key(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    assert isinstance(created, APIKeyCreated)
    assert created.plaintext.startswith("sk_")
    assert created.key.product_id is None
    assert created.key.project_id == project.id


@pytest.mark.asyncio
async def test_create_product_scoped_key(client, org_project_product):
    org, project, product = org_project_product
    created = await client.create_key(str(org.id), project_id=str(project.id), product_id=str(product.id))
    assert created.key.product_id == product.id


@pytest.mark.asyncio
async def test_create_key_with_metadata(client, org_and_project):
    org, project = org_and_project
    meta = KeyMetadata(scopes=["read", "write"], rate_limit=RateLimit(requests=500))
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)
    assert created.key.metadata.scopes == ["read", "write"]
    assert created.key.metadata.rate_limit == RateLimit(requests=500)


@pytest.mark.asyncio
async def test_verify_key(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    verified = await client.verify_key(created.plaintext)
    assert verified.id == created.key.id


@pytest.mark.asyncio
async def test_verify_wrong_key_raises(client, org_and_project):
    org, project = org_and_project
    await client.create_key(str(org.id), project_id=str(project.id))
    with pytest.raises(InvalidKeyError):
        await client.verify_key("sk_wrongkeyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")


@pytest.mark.asyncio
async def test_verify_malformed_key_raises(client):
    with pytest.raises(InvalidKeyError):
        await client.verify_key("notakey")


@pytest.mark.asyncio
async def test_verify_revoked_key_raises(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    await client.revoke_key(str(created.key.id))
    with pytest.raises(RevokedKeyError):
        await client.verify_key(created.plaintext)


@pytest.mark.asyncio
async def test_verify_expired_key_raises_expired_error(client, org_and_project):
    org, project = org_and_project
    meta = KeyMetadata(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)
    with pytest.raises(ExpiredKeyError) as exc_info:
        await client.verify_key(created.plaintext)
    assert exc_info.value.expired_at is not None


@pytest.mark.asyncio
async def test_revoke_unknown_key_raises(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.revoke_key("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_get_key(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    fetched = await client.get_key(str(created.key.id))
    assert fetched.id == created.key.id


@pytest.mark.asyncio
async def test_list_project_keys(client, org_and_project):
    org, project = org_and_project
    await client.create_key(str(org.id), project_id=str(project.id))
    await client.create_key(str(org.id), project_id=str(project.id))
    keys = await client.list_project_keys(str(project.id))
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_plaintext_not_on_apikey(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    assert not hasattr(created.key, "plaintext")


# --- Item 3: usage tracking ---

@pytest.mark.asyncio
async def test_usage_tracking_increments(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    assert created.key.use_count == 0
    assert created.key.last_used_at is None

    await client.verify_key(created.plaintext)
    key = await client.get_key(str(created.key.id))
    assert key.use_count == 1
    assert key.last_used_at is not None

    await client.verify_key(created.plaintext)
    key = await client.get_key(str(created.key.id))
    assert key.use_count == 2


@pytest.mark.asyncio
async def test_usage_tracking_opt_out(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    await client.verify_key(created.plaintext, track_usage=False)
    key = await client.get_key(str(created.key.id))
    assert key.use_count == 0


# --- Item 2: ExpiredKeyError is distinct from InvalidKeyError ---

@pytest.mark.asyncio
async def test_expired_key_is_not_invalid_key(client, org_and_project):
    org, project = org_and_project
    meta = KeyMetadata(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)
    with pytest.raises(ExpiredKeyError):
        await client.verify_key(created.plaintext)
    # Must NOT be a plain InvalidKeyError
    try:
        await client.verify_key(created.plaintext)
    except ExpiredKeyError as e:
        assert e.expired_at is not None
    except InvalidKeyError:
        pytest.fail("Expected ExpiredKeyError, got plain InvalidKeyError")


# --- Item 7: delete_key + KeyStatus filter ---

@pytest.mark.asyncio
async def test_delete_key_removes_record(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    await client.delete_key(str(created.key.id))
    with pytest.raises(APIKeyError, match="not found"):
        await client.get_key(str(created.key.id))


@pytest.mark.asyncio
async def test_delete_unknown_key_raises(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.delete_key("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_list_project_keys_active_status(client, org_and_project):
    org, project = org_and_project
    active = await client.create_key(str(org.id), project_id=str(project.id))
    revoked = await client.create_key(str(org.id), project_id=str(project.id))
    await client.revoke_key(str(revoked.key.id))

    active_keys = await client.list_project_keys(str(project.id), status=KeyStatus.active)
    assert len(active_keys) == 1
    assert active_keys[0].id == active.key.id


@pytest.mark.asyncio
async def test_list_project_keys_revoked_status(client, org_and_project):
    org, project = org_and_project
    key = await client.create_key(str(org.id), project_id=str(project.id))
    await client.revoke_key(str(key.key.id))

    revoked_keys = await client.list_project_keys(str(project.id), status=KeyStatus.revoked)
    assert len(revoked_keys) == 1


# --- B5: update_key ---

@pytest.mark.asyncio
async def test_update_key_metadata(client, org_and_project):
    org, project = org_and_project
    created = await client.create_key(str(org.id), project_id=str(project.id))
    new_meta = KeyMetadata(name="updated", scopes=["admin"])
    updated = await client.update_key(str(created.key.id), metadata=new_meta)
    assert updated.metadata.name == "updated"
    assert updated.metadata.scopes == ["admin"]


@pytest.mark.asyncio
async def test_update_unknown_key_raises(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.update_key("00000000-0000-0000-0000-000000000000", metadata=KeyMetadata())


# --- B1: required_scopes (list) ---

@pytest.mark.asyncio
async def test_validate_key_required_scopes(client, org_and_project):
    from apikeys.exceptions import InsufficientScopeError
    org, project = org_and_project
    meta = KeyMetadata(scopes=["read"])
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)

    # Single scope passes
    await client.validate_key(created.plaintext, required_scopes=["read"])

    # Missing scope fails
    with pytest.raises(InsufficientScopeError):
        await client.validate_key(created.plaintext, required_scopes=["read", "write"])

    # Deprecated alias still works
    await client.validate_key(created.plaintext, required_scope="read")


# --- Item 1: rate limit enforcement ---

@pytest.mark.asyncio
async def test_rate_limit_enforced(client, org_and_project):
    org, project = org_and_project
    meta = KeyMetadata(rate_limit=RateLimit(requests=2, window=RateLimitWindow.minute))
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)

    await client.validate_key(created.plaintext, track_usage=False)
    await client.validate_key(created.plaintext, track_usage=False)

    with pytest.raises(QuotaError) as exc_info:
        await client.validate_key(created.plaintext, track_usage=False)
    assert exc_info.value.retry_after_seconds is not None


@pytest.mark.asyncio
async def test_rate_limit_opt_out(client, org_and_project):
    org, project = org_and_project
    meta = KeyMetadata(rate_limit=RateLimit(requests=1, window=RateLimitWindow.minute))
    created = await client.create_key(str(org.id), project_id=str(project.id), metadata=meta)

    # Exceeds limit but check_rate_limit=False → no error
    for _ in range(5):
        await client.validate_key(created.plaintext, check_rate_limit=False, track_usage=False)
