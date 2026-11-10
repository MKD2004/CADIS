"""/documents/{id} — document info, its section tree, re-ingest and delete."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cadis.api.deps import get_allowed_collections, get_db
from cadis.api.schemas import DocumentOut, JobOut, ReingestOut, SectionOut
from cadis.ingest import service
from cadis.storage import repositories
from cadis.storage.tables import Chunk, Document

router = APIRouter(prefix="/documents", tags=["documents"])


def document_out(db: Session, doc: Document) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    job = repositories.latest_job_for(db, doc.id)
    out.latest_job = JobOut.model_validate(job) if job else None
    return out


def _document_or_404(db, document_id, allowed) -> Document:
    doc = repositories.get_document(db, document_id, allowed)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db),
                 allowed: list[str] = Depends(get_allowed_collections)):
    return document_out(db, _document_or_404(db, document_id, allowed))


@router.get("/{document_id}/sections", response_model=list[SectionOut])
def get_sections(document_id: str, db: Session = Depends(get_db),
                 allowed: list[str] = Depends(get_allowed_collections)):
    """The section tree of the current version, in reading order (parents
    before children). Empty until the first ingest has finished."""
    doc = _document_or_404(db, document_id, allowed)
    counts = dict(db.execute(
        select(Chunk.section_id, func.count(Chunk.id))
        .where(Chunk.document_id == doc.id, Chunk.version == doc.current_version)
        .group_by(Chunk.section_id)).all())
    out = []
    for sec in repositories.section_tree(db, doc.id, doc.current_version):
        item = SectionOut.model_validate(sec)
        item.chunk_count = counts.get(sec.id, 0)
        out.append(item)
    return out


@router.post("/{document_id}/reingest", response_model=ReingestOut, status_code=202)
def reingest(document_id: str, db: Session = Depends(get_db),
             allowed: list[str] = Depends(get_allowed_collections)):
    doc = _document_or_404(db, document_id, allowed)
    job_id = service.reingest(db, doc)
    db.commit()
    return ReingestOut(document_id=doc.id, job_id=job_id)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, allowed: list[str] = Depends(get_allowed_collections)):
    if not service.delete_document(document_id, allowed):
        raise HTTPException(404, "Document not found")
    return Response(status_code=204)
