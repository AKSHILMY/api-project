import os
from functools import lru_cache

from apikeys import APIKeyClient

DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///examples/basic_flow.db")


@lru_cache(maxsize=1)
def get_client() -> APIKeyClient:
    return APIKeyClient(DB_URL)
