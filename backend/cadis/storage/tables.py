"""ORM tables (ARCHITECTURE_V2 §5).

Rules that matter for correctness:
  * Every row that holds document content carries ``collection_id`` so every
    query can be filtered by what the caller may see (ADR-015).
  * Section and chunk IDs are deterministic (ADR-014): re-running ingestion
    writes the same IDs, so writes overwrite instead of duplicating.
  * Deleting a document cascades to its text, sections, chunks, analysis
    results and jobs (``PRAGMA foreign_keys=ON`` is set in ``db.py``). The FTS5
    index follows the ``chunk`` table through triggers (see the migration).

Schema changes go through Alembic (``backend/migrations``); keep this file and
the migrations in step.
"""

from datetime import datetime, timezone

from sqlalchemy import (JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no time zones)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class DocumentStatus:
    PENDING = "PENDING"        # uploaded, waiting for its first ingest job
    PROCESSING = "PROCESSING"  # first ingest running (no searchable version yet)
    READY = "READY"            # a current version is searchable
    FAILED = "FAILED"          # first ingest failed; no searchable version


class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Collection(Base):
    __tablename__ = "collection"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Membership(Base):
    """Shares a collection with a user outside its tenant (used from Phase 6)."""
    __tablename__ = "membership"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collection.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="reader")


class Document(Base):
    __tablename__ = "document"
    __table_args__ = (UniqueConstraint("collection_id", "sha256", name="uq_document_collection_sha"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        ForeignKey("collection.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=0)   # 0 = nothing searchable yet
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PENDING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DocumentText(Base):
    """The cleaned text of one document version. Chunk and section char
    offsets point into this text (used for highlighting and citations)."""
    __tablename__ = "document_text"
    document_id: Mapped[str] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)


class Section(Base):
    """One heading in a document version's section tree (ADR-028)."""
    __tablename__ = "section"
    __table_args__ = (Index("ix_section_doc_version", "document_id", "version"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))
    collection_id: Mapped[str] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    path: Mapped[str] = mapped_column(String(2000))     # "3 Methodology > 3.2 Dataset"; "" = root
    level: Mapped[int] = mapped_column(Integer)         # 0 = root (whole document)
    ordinal: Mapped[int] = mapped_column(Integer)       # pre-order position
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)


class Chunk(Base):
    __tablename__ = "chunk"
    __table_args__ = (Index("ix_chunk_doc_version", "document_id", "version"),)
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))
    collection_id: Mapped[str] = mapped_column(String(36), index=True)
    version: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_id: Mapped[str] = mapped_column(ForeignKey("section.id", ondelete="CASCADE"), index=True)
    section_path: Mapped[str] = mapped_column(String(2000))
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    tokens: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    prev_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    next_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class AnalysisResult(Base):
    __tablename__ = "analysis_result"
    document_id: Mapped[str] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), primary_key=True)
    module: Mapped[str] = mapped_column(String(40), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    result: Mapped[dict] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class JobStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (Index("ix_job_status_created", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    document_id: Mapped[str | None] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.PENDING)
    stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Entity(Base):
    """Cross-document entity index (filled in Phase 5)."""
    __tablename__ = "entity"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    collection_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(500))
    type: Mapped[str] = mapped_column(String(20))


class Mention(Base):
    __tablename__ = "mention"
    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entity.id", ondelete="CASCADE"), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(
        ForeignKey("chunk.id", ondelete="CASCADE"), primary_key=True)
    char_start: Mapped[int] = mapped_column(Integer, primary_key=True)
    char_end: Mapped[int] = mapped_column(Integer)
