"""
models/schemas.py
=================
All Pydantic v2 request and response schemas for CADIS API.
Centralising models here keeps routers thin and ensures
a single source of truth for the API contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────
#  Shared primitives
# ─────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    OK      = "ok"
    DEGRADED = "degraded"
    DOWN    = "down"


class HealthResponse(BaseModel):
    status:  HealthStatus = HealthStatus.OK
    version: str          = "1.0.0"
    services: dict[str, HealthStatus] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
#  PDF / Document processing
# ─────────────────────────────────────────────────────────────

class TextBlock(BaseModel):
    """A single parsed text block from an Unstructured element."""
    block_id:   str
    element_type: str                          # Title, NarrativeText, Table, etc.
    text:       str
    page_number: int | None = None
    metadata:   dict[str, Any] = Field(default_factory=dict)


class ImageBlock(BaseModel):
    """Metadata for an extracted image/diagram element."""
    image_id:    str
    page_number: int | None = None
    base64_data: str | None = None             # populated when extract_images=True
    vlm_description: str | None = None         # populated after VLM pass


class ParsedDocument(BaseModel):
    """Full structured output of the /process-pdf endpoint."""
    document_id:   str
    filename:      str
    total_pages:   int | None = None
    text_blocks:   list[TextBlock]  = Field(default_factory=list)
    image_blocks:  list[ImageBlock] = Field(default_factory=list)
    enriched_text: str              = ""       # flat text after VLM descriptions appended
    metadata:      dict[str, Any]  = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
#  GliNER / NER
# ─────────────────────────────────────────────────────────────

class NERRequest(BaseModel):
    text:          str              = Field(..., min_length=1, max_length=50_000)
    entity_labels: list[str]       = Field(..., min_length=1, max_length=50)
    threshold:     float           = Field(default=0.5, ge=0.0, le=1.0)
    flat_ner:      bool            = Field(
        default=True,
        description="When True, overlapping spans are resolved greedily."
    )

    @field_validator("entity_labels")
    @classmethod
    def labels_must_be_non_empty(cls, v: list[str]) -> list[str]:
        cleaned = [lbl.strip() for lbl in v if lbl.strip()]
        if not cleaned:
            raise ValueError("entity_labels must contain at least one non-empty string.")
        return cleaned


class EntitySpan(BaseModel):
    text:   str
    label:  str
    start:  int
    end:    int
    score:  float = Field(ge=0.0, le=1.0)


class NERResponse(BaseModel):
    entity_labels: list[str]
    entities:      list[EntitySpan]
    entity_count:  int
    grouped:       dict[str, list[EntitySpan]] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────
#  Vector store / ChromaDB
# ─────────────────────────────────────────────────────────────

class UpsertRequest(BaseModel):
    collection_name: str  = Field(default="cadis_documents")
    document_id:     str
    chunks:          list[str] = Field(..., min_length=1)
    metadata:        dict[str, Any] = Field(default_factory=dict)


class UpsertResponse(BaseModel):
    collection_name: str
    document_id:     str
    chunks_stored:   int


class SearchRequest(BaseModel):
    collection_name: str   = Field(default="cadis_documents")
    query:           str   = Field(..., min_length=1)
    top_k:           int   = Field(default=5, ge=1, le=50)
    where:           dict[str, Any] | None = None   # ChromaDB metadata filter


class SearchResult(BaseModel):
    chunk_id:  str
    text:      str
    score:     float
    metadata:  dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query:   str
    results: list[SearchResult]


class CollectionStatsResponse(BaseModel):
    collection_name: str
    document_count:  int
    collections:     list[str]
