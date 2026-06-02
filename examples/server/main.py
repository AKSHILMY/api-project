import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from apikeys.db.session import create_tables

from .deps import DB_URL
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

app.include_router(orgs.router)
app.include_router(projects.router)
app.include_router(products.router)
app.include_router(keys.router)

# Serve built UI if present
_ui_dist = Path(__file__).parent / "ui" / "dist"
if _ui_dist.exists():
    app.mount("/", StaticFiles(directory=str(_ui_dist), html=True), name="ui")
