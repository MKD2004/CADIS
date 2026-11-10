"""Request/response models for the HTTP API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── V1 (legacy) ────────────────────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    text: str


class AskRequest(BaseModel):
    text: str
    question: str


# ── V2 ─────────────────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class CollectionOut(BaseModel):
    id: str
    name: str
    created_at: datetime
    document_count: int = 0


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    document_id: str | None
    status: str
    stage: str | None
    progress: float
    attempts: int
    max_attempts: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    collection_id: str
    filename: str
    title: str | None
    size_bytes: int
    sha256: str
    status: str
    current_version: int
    pages: int | None
    error: str | None
    created_at: datetime
    updated_at: datetime
    latest_job: JobOut | None = None


class UploadOut(BaseModel):
    filename: str
    document_id: str
    job_id: str | None
    duplicate: bool


class ReingestOut(BaseModel):
    document_id: str
    job_id: str


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    parent_id: str | None
    title: str
    path: str
    level: int
    ordinal: int
    page: int | None
    char_start: int
    char_end: int
    chunk_count: int = 0


class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    # Optional narrowing; always intersected with what the caller may read.
    collection_ids: list[str] | None = None
    document_ids: list[str] | None = None
    k: int = Field(8, ge=1, le=50)


class SectionTargetOut(BaseModel):
    phrase: str
    titles: list[str]
    sections: int


class SearchHitOut(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section_path: str
    page: int | None
    char_start: int
    char_end: int
    text: str
    score: float
    target: str | None


class SearchOut(BaseModel):
    question: str
    hits: list[SearchHitOut]
    sections: list[SectionTargetOut]
    timings_ms: dict[str, float]


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    collection_ids: list[str] | None = None
    document_ids: list[str] | None = None
    mode: str = Field("extractive", pattern="^extractive$")   # "generative" arrives in Phase 3
