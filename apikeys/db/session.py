from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .base import Base

# Maps bare scheme → async-driver scheme so callers don't have to know the driver suffix.
_ASYNC_SCHEMES: dict[str, str] = {
    "postgresql": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
    "sqlite": "sqlite+aiosqlite",
    "mysql": "mysql+aiomysql",
    "mariadb": "mariadb+aiomysql",
}


def _normalize_url(db_url: str) -> str:
    scheme = db_url.split("://")[0]
    if scheme in _ASYNC_SCHEMES:
        return db_url.replace(scheme + "://", _ASYNC_SCHEMES[scheme] + "://", 1)
    return db_url


def make_session_factory(db_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(_normalize_url(db_url), future=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_tables(db_url: str) -> None:
    """Create all SDK tables if they don't already exist.

    Call this once at application startup before using APIKeyClient.
    Safe to call on every restart — existing tables are left untouched.
    When upgrading to a new SDK version, re-run this to pick up any new tables.
    """
    engine = create_async_engine(_normalize_url(db_url), future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
