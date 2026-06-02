from datetime import datetime, timedelta, timezone


import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apikeys import APIKeyClient, APIKeyCreated, KeyMetadata
from apikeys.db.base import Base
from apikeys.exceptions import APIKeyError, InvalidKeyError, RevokedKeyError


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
    return APIKeyClient(_sessions=sessions)


@pytest_asyncio.fixture
async def project(client):
    org = await client.create_organization("Acme")
    return await client.create_project(str(org.id), "Backend")


@pytest_asyncio.fixture
async def project_and_product(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    product = await client.create_product(str(org.id), "Analytics")
    await client.add_product_to_project(str(product.id), str(project.id))
    return project, product


@pytest.mark.asyncio
async def test_create_project_scoped_key(client, project):
    created = await client.create_key(str(project.id))
    assert isinstance(created, APIKeyCreated)
    assert created.plaintext.startswith("sk_")
    assert created.key.product_id is None
    assert created.key.project_id == project.id


@pytest.mark.asyncio
async def test_create_product_scoped_key(client, project_and_product):
    project, product = project_and_product
    created = await client.create_key(str(project.id), product_id=str(product.id))
    assert created.key.product_id == product.id


@pytest.mark.asyncio
async def test_create_key_with_metadata(client, project):
    meta = KeyMetadata(scopes=["read", "write"], rate_limit=500)
    created = await client.create_key(str(project.id), metadata=meta)
    assert created.key.metadata.scopes == ["read", "write"]
    assert created.key.metadata.rate_limit == 500


@pytest.mark.asyncio
async def test_verify_key(client, project):
    created = await client.create_key(str(project.id))
    verified = await client.verify_key(created.plaintext)
    assert verified.id == created.key.id


@pytest.mark.asyncio
async def test_verify_wrong_key_raises(client, project):
    await client.create_key(str(project.id))
    with pytest.raises(InvalidKeyError):
        await client.verify_key("sk_wrongkeyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")


@pytest.mark.asyncio
async def test_verify_malformed_key_raises(client):
    with pytest.raises(InvalidKeyError):
        await client.verify_key("notakey")


@pytest.mark.asyncio
async def test_verify_revoked_key_raises(client, project):
    created = await client.create_key(str(project.id))
    await client.revoke_key(str(created.key.id))
    with pytest.raises(RevokedKeyError):
        await client.verify_key(created.plaintext)


@pytest.mark.asyncio
async def test_verify_expired_key_raises(client, project):
    meta = KeyMetadata(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
    created = await client.create_key(str(project.id), metadata=meta)
    with pytest.raises(InvalidKeyError, match="expired"):
        await client.verify_key(created.plaintext)


@pytest.mark.asyncio
async def test_revoke_unknown_key_raises(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.revoke_key("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_get_key(client, project):
    created = await client.create_key(str(project.id))
    fetched = await client.get_key(str(created.key.id))
    assert fetched == created.key


@pytest.mark.asyncio
async def test_list_project_keys(client, project):
    await client.create_key(str(project.id))
    await client.create_key(str(project.id))
    keys = await client.list_project_keys(str(project.id))
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_plaintext_not_on_apikey(client, project):
    created = await client.create_key(str(project.id))
    assert not hasattr(created.key, "plaintext")
