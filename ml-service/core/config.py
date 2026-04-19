"""
core/config.py
==============
Centralised settings (loaded once at startup via pydantic-settings).
Override any value with an environment variable or a .env file.
"""

from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── API ───────────────────────────────────────────────────
    app_title:       str  = "CADIS API"
    app_description: str  = "Context-Aware Document Intelligence System — FastAPI Backend"
    app_version:     str  = "1.0.0"
    debug:           bool = False

    # ── Models ────────────────────────────────────────────────
    gliner_model_id:   str = "urchade/gliner_base"
    embedder_model_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── VLM (placeholder) ────────────────────────────────────
    vlm_model_id:     str  = "Qwen/Qwen-VL-Chat"
    vlm_enabled:      bool = False     # flip to True when GPU available

    # ── ChromaDB ─────────────────────────────────────────────
    chroma_persist_dir:       str = "./chroma_store"
    chroma_default_collection: str = "cadis_documents"

    # ── Unstructured ─────────────────────────────────────────
    unstructured_extract_images: bool = True
    unstructured_strategy:       str  = "hi_res"   # "fast" | "hi_res" | "ocr_only"

    # ── Upload limits ─────────────────────────────────────────
    max_upload_mb: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
