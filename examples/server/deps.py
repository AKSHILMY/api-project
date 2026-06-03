import os
from functools import lru_cache

from apikeys import APIKeyClient

DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///examples/server.db")

# In production: set SIGNING_SECRET to a long random value (e.g. secrets.token_hex(32)).
# All keys issued under one secret are invalidated if the secret changes.
SIGNING_SECRET = os.getenv("SIGNING_SECRET", "dev-secret-change-me-in-production")

KEY_PREFIX   = os.getenv("KEY_PREFIX", "sk")
ENVIRONMENT  = os.getenv("ENVIRONMENT", "")   # e.g. "live" or "test"


@lru_cache(maxsize=1)
def get_client() -> APIKeyClient:
    return APIKeyClient(
        DB_URL,
        signing_secret=SIGNING_SECRET,
        key_prefix=KEY_PREFIX,
        environment=ENVIRONMENT,
    )
