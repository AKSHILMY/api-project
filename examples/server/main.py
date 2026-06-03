import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apikeys.db.session import create_tables

from .deps import DB_URL, get_client
from .routers import keys, orgs, products, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables(DB_URL)
    yield


app = FastAPI(title="API Keys Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Make the APIKeyClient available on request.state so APIKeyDepends can find it.
@app.middleware("http")
async def attach_apikey_client(request: Request, call_next):
    request.state.apikeys_client = get_client()
    return await call_next(request)


app.include_router(orgs.router)
app.include_router(projects.router)
app.include_router(products.router)
app.include_router(keys.router)

# Serve built UI if present
_ui_dist = Path(__file__).parent / "ui" / "dist"
if _ui_dist.exists():
    app.mount("/", StaticFiles(directory=str(_ui_dist), html=True), name="ui")
