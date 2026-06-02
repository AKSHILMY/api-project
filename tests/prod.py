import asyncio

from alembic import command
from alembic.config import Config

from apikeys import APIKeyClient

DB_URL = "postgresql+asyncpg://akshilmy-m4-pro@localhost/apikeys_prod"


def run_migrations() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DB_URL.replace("+asyncpg", ""))
    command.upgrade(cfg, "head")


def drop_tables() -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", DB_URL.replace("+asyncpg", ""))
    command.downgrade(cfg, "base")


async def main() -> None:
    run_migrations()

    client = APIKeyClient(DB_URL)

    org = await client.create_organization("Acme Corp")
    same_org = await client.use_organization(str(org.id))
    assert same_org == org

    backend = await client.create_project(str(org.id), "Backend")
    mobile = await client.create_project(str(org.id), "Mobile")

    analytics = await client.create_product(str(org.id), "Analytics")
    billing = await client.create_product(str(org.id), "Billing")

    await client.add_product_to_project(str(analytics.id), str(backend.id))
    await client.add_product_to_project(str(billing.id), str(backend.id))
    await client.add_product_to_project(str(analytics.id), str(mobile.id))

    # drop_tables()


if __name__ == "__main__":
    asyncio.run(main())
