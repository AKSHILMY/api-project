"""
FastAPI integration example.

Shows the built-in APIKeyDepends dependency — no boilerplate exception mapping needed.

Install extras:
    pip install "apikeys-platform[sqlite,fastapi]"

Run:
    uvicorn examples.fastapi_integration:app --reload

Then test:
    # No key → 401
    curl http://localhost:8000/data

    # With a valid key (replace with one from /setup)
    curl http://localhost:8000/setup
    curl -H "X-API-Key: <plaintext>" http://localhost:8000/data
    curl -H "X-API-Key: <plaintext>" http://localhost:8000/admin
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request

from apikeys import APIKey, APIKeyClient, APIKeyDepends, KeyMetadata, RateLimit, RateLimitWindow
from apikeys.db.session import create_tables

DB_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///examples/fastapi_demo.db")
SECRET = os.getenv("SIGNING_SECRET", "dev-secret-change-me")

_client: APIKeyClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    await create_tables(DB_URL)
    _client = APIKeyClient(DB_URL, signing_secret=SECRET, key_prefix="demo", environment="dev")
    yield


app = FastAPI(title="APIKeyDepends demo", lifespan=lifespan)


# Mount the client on request.state so APIKeyDepends can find it.
@app.middleware("http")
async def attach_apikey_client(request: Request, call_next):
    request.state.apikeys_client = _client
    return await call_next(request)


# ── Dependencies ──────────────────────────────────────────────────────────────

# Any valid key — just authenticated
authenticated = APIKeyDepends()

# Key must carry the "read:data" scope
read_data = APIKeyDepends(required_scopes=["read:data"])

# Key must carry "admin" scope
admin_only = APIKeyDepends(required_scopes=["admin"])


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/setup", summary="Create a demo org and two keys")
async def setup():
    """One-time setup — creates an org and returns two keys for testing."""
    org, _ = await _client.get_or_create_organization("Demo Org")
    project, _ = await _client.get_or_create_project(str(org.id), "demo-project")

    read_key = await _client.create_key(
        str(org.id),
        project_id=str(project.id),
        metadata=KeyMetadata(
            name="Read-only key",
            scopes=["read:data"],
            rate_limit=RateLimit(requests=10, window=RateLimitWindow.minute),
        ),
    )
    admin_key = await _client.create_key(
        str(org.id),
        project_id=str(project.id),
        metadata=KeyMetadata(name="Admin key", scopes=["read:data", "admin"]),
    )
    return {
        "read_key":  read_key.plaintext,
        "admin_key": admin_key.plaintext,
        "note":      "Pass either as X-API-Key header",
    }


@app.get("/data", summary="Requires read:data scope")
async def get_data(key: APIKey = Depends(read_data)):
    return {"message": "Here is your data", "key_id": str(key.id)}


@app.get("/admin", summary="Requires admin scope")
async def admin_panel(key: APIKey = Depends(admin_only)):
    return {"message": "Welcome to the admin panel", "key_id": str(key.id)}


@app.get("/me", summary="Any authenticated key — returns key details")
async def me(key: APIKey = Depends(authenticated)):
    return {
        "key_id":      str(key.id),
        "scopes":      key.metadata.scopes,
        "use_count":   key.use_count,
        "last_used_at": key.last_used_at,
        "rate_limit":  key.metadata.rate_limit,
    }
