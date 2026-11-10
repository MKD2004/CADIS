"""CADIS FastAPI application.

Run (from the repository root):
    uvicorn cadis.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

On startup the app upgrades the database schema (Alembic), makes sure the
default tenant exists, and starts the in-process job worker. If storage cannot
be opened, the V1 endpoints keep working and the V2 endpoints answer 503.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cadis.api import collections, documents, health, jobs, legacy
from cadis.config import get_settings

log = logging.getLogger("cadis")


def _start_v2(app: FastAPI) -> None:
    from cadis.ingest.pipeline import HANDLERS
    from cadis.jobs.worker import Worker
    from cadis.storage import repositories
    from cadis.storage.db import init_db, session_scope

    settings = get_settings()
    init_db()
    with session_scope() as s:
        repositories.ensure_tenant(s, settings.default_tenant)
    if settings.run_worker:
        worker = Worker(HANDLERS)
        worker.recover()
        worker.start()
        app.state.worker = worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.v2_error = None
    app.state.worker = None
    try:
        _start_v2(app)
    except Exception as e:                       # keep V1 alive if storage is broken
        log.exception("V2 storage failed to start; V2 endpoints will return 503")
        app.state.v2_error = f"{type(e).__name__}: {e}"
    yield
    if app.state.worker is not None:
        app.state.worker.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.service_name, version=settings.service_version,
                  lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(legacy.router)
    app.include_router(collections.router)
    app.include_router(documents.router)
    app.include_router(jobs.router)
    return app


app = create_app()
