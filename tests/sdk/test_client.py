import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apikeys import APIKeyClient
from apikeys.db.base import Base
from apikeys.exceptions import AlreadyExistsError, APIKeyError

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


@pytest.mark.asyncio
async def test_create_organization(client):
    org = await client.create_organization("Acme")
    assert org.name == "Acme"
    assert org.id is not None
    assert org.created_at is not None


@pytest.mark.asyncio
async def test_use_organization_returns_same_instance(client):
    org = await client.create_organization("Acme")
    same = await client.use_organization(str(org.id))
    assert same == org


@pytest.mark.asyncio
async def test_use_organization_not_found(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.use_organization("00000000-0000-0000-0000-000000000000")


@pytest.mark.asyncio
async def test_create_project(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    assert project.name == "Backend"
    assert project.org_id == org.id


@pytest.mark.asyncio
async def test_create_project_unknown_org(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.create_project("00000000-0000-0000-0000-000000000000", "Backend")


@pytest.mark.asyncio
async def test_create_product(client):
    org = await client.create_organization("Acme")
    product = await client.create_product(str(org.id), "Analytics")
    assert product.name == "Analytics"
    assert product.org_id == org.id


@pytest.mark.asyncio
async def test_create_product_unknown_org(client):
    with pytest.raises(APIKeyError, match="not found"):
        await client.create_product("00000000-0000-0000-0000-000000000000", "Analytics")


@pytest.mark.asyncio
async def test_add_product_to_project(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    product = await client.create_product(str(org.id), "Analytics")
    await client.add_product_to_project(str(product.id), str(project.id))


@pytest.mark.asyncio
async def test_add_product_to_project_unknown_project(client):
    org = await client.create_organization("Acme")
    product = await client.create_product(str(org.id), "Analytics")
    with pytest.raises(APIKeyError, match="not found"):
        await client.add_product_to_project(
            str(product.id), "00000000-0000-0000-0000-000000000000"
        )


@pytest.mark.asyncio
async def test_add_product_to_project_unknown_product(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    with pytest.raises(APIKeyError, match="not found"):
        await client.add_product_to_project(
            "00000000-0000-0000-0000-000000000000", str(project.id)
        )


@pytest.mark.asyncio
async def test_multiple_products_linked_to_project(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    prod_a = await client.create_product(str(org.id), "Analytics")
    prod_b = await client.create_product(str(org.id), "Billing")
    await client.add_product_to_project(str(prod_a.id), str(project.id))
    await client.add_product_to_project(str(prod_b.id), str(project.id))


# --- Item 6: AlreadyExistsError / get_or_create_* ---

@pytest.mark.asyncio
async def test_create_duplicate_organization_raises(client):
    org = await client.create_organization("Acme")
    with pytest.raises(AlreadyExistsError) as exc_info:
        await client.create_organization("Acme")
    assert exc_info.value.existing_id == str(org.id)


@pytest.mark.asyncio
async def test_get_or_create_organization_creates(client):
    org, created = await client.get_or_create_organization("Acme")
    assert created is True
    assert org.name == "Acme"


@pytest.mark.asyncio
async def test_get_or_create_organization_returns_existing(client):
    org1 = await client.create_organization("Acme")
    org2, created = await client.get_or_create_organization("Acme")
    assert created is False
    assert org1.id == org2.id


@pytest.mark.asyncio
async def test_create_duplicate_project_raises(client):
    org = await client.create_organization("Acme")
    project = await client.create_project(str(org.id), "Backend")
    with pytest.raises(AlreadyExistsError) as exc_info:
        await client.create_project(str(org.id), "Backend")
    assert exc_info.value.existing_id == str(project.id)


@pytest.mark.asyncio
async def test_get_or_create_project_returns_existing(client):
    org = await client.create_organization("Acme")
    p1 = await client.create_project(str(org.id), "Backend")
    p2, created = await client.get_or_create_project(str(org.id), "Backend")
    assert created is False
    assert p1.id == p2.id


@pytest.mark.asyncio
async def test_create_duplicate_product_raises(client):
    org = await client.create_organization("Acme")
    product = await client.create_product(str(org.id), "Analytics")
    with pytest.raises(AlreadyExistsError) as exc_info:
        await client.create_product(str(org.id), "Analytics")
    assert exc_info.value.existing_id == str(product.id)


# --- B3: signing_secret enforcement ---

def test_missing_signing_secret_raises():
    with pytest.raises((ValueError, TypeError)):
        APIKeyClient(db_url="sqlite+aiosqlite:///:memory:", signing_secret="")


# --- Item 5: configurable prefix ---

@pytest.mark.asyncio
async def test_custom_prefix_and_environment():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    c = APIKeyClient(
        _sessions=sessions,
        signing_secret=_SECRET,
        key_prefix="myapp",
        environment="live",
    )
    org = await c.create_organization("TestOrg")
    created = await c.create_key(str(org.id))
    assert created.plaintext.startswith("myapp_live_")
