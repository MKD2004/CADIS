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
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import get_settings
from core.logging import configure_logging, get_logger
from models.schemas import HealthResponse, ModelStatus
from routers import document, ner, search, summary
from services.gliner_ie import GliNERService
from services.multimodal import MultimodalService
from services.qa import QAService
from services.summarizer import SummarizerService
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

    def _timed_load(step: str, total: int, label: str, loader):
        t = time.perf_counter()
        logger.info("[%s] Loading %s…", step, label)
        try:
            loader()
            logger.info("      %s ✓  (%.2fs)", label, time.perf_counter() - t)
        except Exception as exc:
            logger.error("      %s FAILED (%.2fs): %s", label, time.perf_counter() - t, exc)

    # ── 1. ChromaDB + MiniLM embedder ─────────────────────────
    _timed_load("1/5", 5, f"all-MiniLM-L6-v2 + ChromaDB ({settings.embedder_model_id})",
                VectorStoreService.get_instance)

    # ── 2. GLiNER zero-shot NER ───────────────────────────────
    _timed_load("2/5", 5, f"GLiNER ({settings.gliner_model_id})",
                GliNERService.get_instance)

    # ── 3. RoBERTa QA ─────────────────────────────────────────
    _timed_load("3/5", 5, "RoBERTa QA (deepset/roberta-base-squad2)",
                QAService.get_instance)

    # ── 4. DistilBART summarizer ──────────────────────────────
    _timed_load("4/5", 5, "DistilBART (sshleifer/distilbart-cnn-12-6)",
                SummarizerService.get_instance)

    # ── 5. VLM (conditional) ──────────────────────────────────
    if settings.vlm_enabled:
        _timed_load("5/5", 5, f"VLM ({settings.vlm_model_id})",
                    MultimodalService.get_instance)
    else:
        logger.info("[5/5] VLM disabled (set VLM_ENABLED=true to activate).")

    # ── 6. Seed sample documents ──────────────────────────────
    logger.info("Seeding sample documents into ChromaDB…")
    try:
        from scripts.seed_documents import seed_sample_documents
        seed_sample_documents()
    except Exception as exc:
        logger.error("      Sample seeding FAILED: %s — continuing without samples.", exc)

    elapsed = time.perf_counter() - t0
    logger.info("All models ready. Total startup time: %.2fs", elapsed)
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
        from core.metrics import Metrics
        t0       = time.perf_counter()
        response = await call_next(request)
        elapsed  = time.perf_counter() - t0
        ms = round(elapsed * 1000, 1)
        response.headers["X-Process-Time"] = f"{elapsed:.4f}s"
        logger.info("%s %s %s %.0fms", request.method, request.url.path, response.status_code, ms)
        Metrics.get().inc_requests()
        return response

    # ── Validation error handler (clean 422 responses) ─────────
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = " → ".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        message = first.get("msg", "Validation error")
        return JSONResponse(
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
            content     = {
                "error":   "validation_error",
                "message": message,
                "field":   field or None,
                "details": [
                    {
                        "field":   " → ".join(str(loc) for loc in e.get("loc", []) if loc != "body"),
                        "message": e.get("msg", ""),
                    }
                    for e in errors
                ],
            },
        )

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
    
    app.include_router(summary.router, prefix="/api/v1/summary", tags=["Summarization"])

    # ── Health endpoints ──────────────────────────────────────
    @app.get(
        "/health",
        response_model = HealthResponse,
        tags           = ["Health"],
        summary        = "Full service health check",
    )
    async def health_check() -> HealthResponse:
        from datetime import datetime, timezone

        gliner_svc = GliNERService._instance
        qa_svc     = QAService._instance
        sum_svc    = SummarizerService._instance
        vs_svc     = VectorStoreService._instance

        models = ModelStatus(
            gliner     = bool(gliner_svc and gliner_svc.is_ready),
            roberta    = bool(qa_svc and qa_svc.is_ready),
            distilbart = bool(sum_svc and sum_svc.is_ready),
            minilm     = bool(vs_svc and vs_svc._embed_fn is not None),
        )

        chromadb_ok = bool(vs_svc and vs_svc._client is not None)

        all_core = models.gliner and models.minilm and chromadb_ok
        overall = "ok" if all_core else "degraded"

        return HealthResponse(
            status    = overall,
            models    = models,
            chromadb  = chromadb_ok,
            timestamp = datetime.now(timezone.utc).isoformat(),
        )

    @app.get(
        "/metrics",
        tags    = ["Health"],
        summary = "Model inference latency metrics",
    )
    async def metrics() -> dict:
        from core.metrics import Metrics
        return Metrics.get().snapshot()

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