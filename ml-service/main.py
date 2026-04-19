"""
main.py
=======
CADIS FastAPI Application
=========================
Entry point for the Context-Aware Document Intelligence System microservice.

Startup sequence
────────────────
1. configure_logging()         — structured log format
2. lifespan context manager    — warm all ML models before accepting traffic
   a. GliNERService            — GliNER zero-shot NER
   b. VectorStoreService       — ChromaDB + MiniLM embedder
   c. MultimodalService        — Qwen-VL (if vlm_enabled=True)
3. Routers registered          — document, ner, search, summary

Run locally
───────────
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

With Gunicorn (production)
──────────────────────────
    gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    (Use w=1 — models are singletons and not fork-safe)
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging import configure_logging, get_logger
from models.schemas import HealthResponse, HealthStatus
from routers import document, ner, search, summary
from services.gliner_ie import GliNERService
from services.multimodal import MultimodalService
from services.vector_store import VectorStoreService

# ─────────────────────────────────────────────────────────────
#  Bootstrap logging before anything else
# ─────────────────────────────────────────────────────────────
configure_logging()
logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
#  Lifespan — model warm-up and teardown
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager.
    Everything before `yield` runs at startup; after `yield` at shutdown.
    Models are loaded here so they are ready before the first request hits.
    """
    settings = get_settings()
    logger.info("═" * 60)
    logger.info("  CADIS API  —  starting up")
    logger.info("  Version : %s", settings.app_version)
    logger.info("  Debug   : %s", settings.debug)
    logger.info("═" * 60)

    t0 = time.perf_counter()

    # ── 1. GliNER ─────────────────────────────────────────────
    logger.info("[1/3] Loading GliNER (%s)…", settings.gliner_model_id)
    try:
        GliNERService.get_instance()
        logger.info("      GliNER ✓")
    except Exception as exc:
        logger.error("      GliNER FAILED: %s", exc)

    # ── 2. ChromaDB + Embedder ────────────────────────────────
    logger.info("[2/3] Loading ChromaDB + embedder (%s)…", settings.embedder_model_id)
    try:
        VectorStoreService.get_instance()
        logger.info("      VectorStore ✓")
    except Exception as exc:
        logger.error("      VectorStore FAILED: %s", exc)

    # ── 3. VLM (conditional) ──────────────────────────────────
    if settings.vlm_enabled:
        logger.info("[3/3] Loading VLM (%s)…", settings.vlm_model_id)
        try:
            MultimodalService.get_instance()
            logger.info("      VLM ✓")
        except Exception as exc:
            logger.error("      VLM FAILED: %s — continuing without VLM.", exc)
    else:
        logger.info("[3/3] VLM disabled (set VLM_ENABLED=true to activate).")

    elapsed = time.perf_counter() - t0
    logger.info("All services ready in %.2fs. Accepting traffic.", elapsed)
    logger.info("─" * 60)

    yield  # ← server is live here

    # ── Shutdown ──────────────────────────────────────────────
    logger.info("CADIS API shutting down.")


# ─────────────────────────────────────────────────────────────
#  Application factory
# ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title        = settings.app_title,
        description  = settings.app_description,
        version      = settings.app_version,
        lifespan     = lifespan,
        docs_url     = "/docs",
        redoc_url    = "/redoc",
        openapi_url  = "/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins     = ["*"],    # tighten in production
        allow_credentials = True,
        allow_methods     = ["*"],
        allow_headers     = ["*"],
    )

    # ── Request timing middleware ──────────────────────────────
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        t0       = time.perf_counter()
        response = await call_next(request)
        elapsed  = time.perf_counter() - t0
        response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
        return response

    # ── Global exception handler ──────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s: %s", request.method, request.url, exc)
        return JSONResponse(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            content     = {"detail": "An unexpected error occurred. Check server logs."},
        )

    # ── Routers ───────────────────────────────────────────────
    app.include_router(document.router)
    app.include_router(ner.router)
    app.include_router(search.router)
    
    # 🟢 WE ADDED THIS SINGLE LINE RIGHT HERE! 🟢
    app.include_router(summary.router, prefix="/api/v1/summary", tags=["Summarization"])

    # ── Health endpoints ──────────────────────────────────────
    @app.get(
        "/health",
        response_model = HealthResponse,
        tags           = ["Health"],
        summary        = "Full service health check",
    )
    async def health_check() -> HealthResponse:
        gliner_svc = GliNERService._instance
        vs_svc     = VectorStoreService._instance
        vlm_svc    = MultimodalService._instance

        services = {
            "gliner":       HealthStatus.OK   if (gliner_svc and gliner_svc.is_ready) else HealthStatus.DOWN,
            "vector_store": HealthStatus.OK   if (vs_svc     and vs_svc.is_ready)     else HealthStatus.DOWN,
            "vlm":          HealthStatus.OK   if (vlm_svc    and vlm_svc.is_ready)    else HealthStatus.DEGRADED,
        }

        overall = (
            HealthStatus.OK
            if all(s in (HealthStatus.OK, HealthStatus.DEGRADED) for s in services.values())
            else HealthStatus.DOWN
        )

        return HealthResponse(
            status   = overall,
            version  = get_settings().app_version,
            services = services,
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {
            "name":    "CADIS API",
            "version": get_settings().app_version,
            "docs":    "/docs",
            "health":  "/health",
        }

    return app


# ─────────────────────────────────────────────────────────────
#  Module-level app instance (used by uvicorn)
# ─────────────────────────────────────────────────────────────
app = create_app()