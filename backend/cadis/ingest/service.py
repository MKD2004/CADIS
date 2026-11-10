"""Document operations used by the API: upload, re-ingest, delete.

Uploads only *queue* work: the file is saved, a DOCUMENT and an ingest JOB
row are written, and the API returns 202 at once. The worker does the rest.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cadis.config import get_settings
from cadis.index.vector_store import get_vector_store
from cadis.ingest.parsers import UnsupportedFileType, file_kind, looks_like
from cadis.ingest.pipeline import INGEST
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.files import FileStore, sha256_of
from cadis.storage.tables import Document

log = logging.getLogger("cadis.ingest")


class UploadRejected(ValueError):
    """The file cannot be accepted (type, size, content). Maps to HTTP 4xx."""

    def __init__(self, message: str, status_code: int = 415):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class UploadResult:
    filename: str
    document_id: str
    job_id: str | None
    duplicate: bool


def validate_upload(filename: str, content: bytes) -> str:
    s = get_settings()
    try:
        kind = file_kind(filename)
    except UnsupportedFileType as e:
        raise UploadRejected(str(e), 415)
    if not content:
        raise UploadRejected(f"{filename} is empty", 422)
    if len(content) > s.max_upload_mb * 1024 * 1024:
        raise UploadRejected(f"{filename} is larger than {s.max_upload_mb} MB", 413)
    if not looks_like(kind, content):
        raise UploadRejected(f"{filename} is not a valid .{kind} file", 415)
    return kind


def upload(session: Session, collection_id: str, filename: str, content: bytes) -> UploadResult:
    """Caller must already have checked that the collection is allowed."""
    validate_upload(filename, content)
    sha = sha256_of(content)
    existing = repositories.find_document_by_sha(session, collection_id, sha)
    if existing is not None:                        # same bytes already in this collection
        job = repositories.latest_job_for(session, existing.id)
        return UploadResult(filename, existing.id, job.id if job else None, True)

    FileStore().save(content)
    try:
        with session.begin_nested():
            doc = repositories.create_document(session, collection_id, filename, sha, len(content))
            job = repositories.create_job(session, INGEST, doc.id, get_settings().job_max_attempts)
    except IntegrityError:                          # a concurrent upload of the same file won
        existing = repositories.find_document_by_sha(session, collection_id, sha)
        job = repositories.latest_job_for(session, existing.id) if existing else None
        return UploadResult(filename, existing.id if existing else "", job.id if job else None, True)
    return UploadResult(filename, doc.id, job.id, False)


def reingest(session: Session, document: Document) -> str:
    """Queue a new version of the document. Returns the job ID (an already
    queued or running job is reused)."""
    active = repositories.active_job_for(session, document.id)
    if active is not None:
        return active.id
    return repositories.create_job(session, INGEST, document.id,
                                   get_settings().job_max_attempts).id


def delete_document(document_id: str, allowed_collection_ids: list[str]) -> bool:
    """Delete a document and everything derived from it.

    SQLite first (source of truth; text, sections, chunks, FTS rows, results
    and jobs go by cascade and trigger), then vectors, then the original file
    if no other document uses the same bytes. If the vector delete fails, the
    leftovers are invisible to search (results are checked against SQLite) and
    ``scripts/check_consistency.py`` removes them.
    """
    with session_scope() as db:
        doc = repositories.get_document(db, document_id, allowed_collection_ids)
        if doc is None:
            return False
        sha = doc.sha256
        db.delete(doc)
        db.flush()
        shared = repositories.other_documents_with_sha(db, sha, document_id)
    try:
        get_vector_store().delete_document(document_id)
    except Exception:
        log.exception("could not delete vectors of %s; run check_consistency.py", document_id)
    if not shared:
        FileStore().delete(sha)
    return True
