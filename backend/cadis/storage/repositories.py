"""All database queries (ARCHITECTURE_V2 §4).

Rule (ADR-015): every function that reads document content takes
``allowed_collection_ids`` and has no "all collections" default. An empty
list means "nothing is visible", never "everything".
"""

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from cadis.storage.tables import (Chunk, Collection, Document, DocumentStatus, DocumentText,
                                  Job, JobStatus, Membership, Section, Tenant, utcnow)


def new_id() -> str:
    return str(uuid.uuid4())


def _ids(allowed_collection_ids: Iterable[str]) -> list[str]:
    if allowed_collection_ids is None:   # defensive: the rule is "no default"
        raise ValueError("allowed_collection_ids is required")
    return list(allowed_collection_ids)


# ── Tenants and collections ────────────────────────────────────────────────────

def ensure_tenant(session: Session, tenant_id: str, name: str | None = None) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=name or tenant_id)
        session.add(tenant)
        session.flush()
    return tenant


def allowed_collection_ids(session: Session, tenant_id: str, user_id: str | None) -> list[str]:
    """Collections the caller may read: owned by their tenant, or shared with
    them through a membership. Computed on the server only (ADR-015)."""
    owned = select(Collection.id).where(Collection.tenant_id == tenant_id)
    ids = set(session.scalars(owned))
    if user_id:
        ids.update(session.scalars(select(Membership.collection_id)
                                   .where(Membership.user_id == user_id)))
    return sorted(ids)


def create_collection(session: Session, tenant_id: str, name: str) -> Collection:
    col = Collection(id=new_id(), tenant_id=tenant_id, name=name)
    session.add(col)
    session.flush()
    return col


def get_collection(session: Session, collection_id: str,
                   allowed_collection_ids: Iterable[str]) -> Collection | None:
    if collection_id not in _ids(allowed_collection_ids):
        return None
    return session.get(Collection, collection_id)


def list_collections(session: Session, allowed_collection_ids: Iterable[str]):
    """[(collection, document_count)] newest first."""
    ids = _ids(allowed_collection_ids)
    if not ids:
        return []
    counts = (select(Document.collection_id, func.count(Document.id).label("n"))
              .group_by(Document.collection_id).subquery())
    rows = session.execute(
        select(Collection, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.collection_id == Collection.id)
        .where(Collection.id.in_(ids))
        .order_by(Collection.created_at.desc()))
    return [(c, n) for c, n in rows]


# ── Documents ─────────────────────────────────────────────────────────────────

def find_document_by_sha(session: Session, collection_id: str, sha256: str) -> Document | None:
    return session.scalars(select(Document).where(
        Document.collection_id == collection_id, Document.sha256 == sha256)).first()


def create_document(session: Session, collection_id: str, filename: str, sha256: str,
                    size_bytes: int) -> Document:
    doc = Document(id=new_id(), collection_id=collection_id, filename=filename,
                   sha256=sha256, size_bytes=size_bytes, status=DocumentStatus.PENDING)
    session.add(doc)
    session.flush()
    return doc


def get_document(session: Session, document_id: str,
                 allowed_collection_ids: Iterable[str]) -> Document | None:
    ids = _ids(allowed_collection_ids)
    doc = session.get(Document, document_id)
    if doc is None or doc.collection_id not in ids:
        return None
    return doc


def list_documents(session: Session, collection_id: str,
                   allowed_collection_ids: Iterable[str]) -> list[Document]:
    if collection_id not in _ids(allowed_collection_ids):
        return []
    return list(session.scalars(select(Document)
                                .where(Document.collection_id == collection_id)
                                .order_by(Document.created_at)))


def other_documents_with_sha(session: Session, sha256: str, exclude_id: str) -> int:
    return session.scalar(select(func.count(Document.id)).where(
        Document.sha256 == sha256, Document.id != exclude_id)) or 0


# ── Document versions: text, sections, chunks ────────────────────────────────

def _upsert(session: Session, table, rows: Sequence[dict], key: Sequence[str]) -> None:
    """INSERT … ON CONFLICT DO UPDATE (ADR-014). Never INSERT OR REPLACE: it
    would bypass the FTS5 delete trigger."""
    if not rows:
        return
    if session.get_bind().dialect.name != "sqlite":   # pragma: no cover - Postgres later
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(table)
    else:
        stmt = sqlite_insert(table)
    cols = [c.name for c in table.__table__.columns if c.name not in key]
    # SQLite limits bound parameters per statement; write in slices.
    per_row = len(table.__table__.columns)
    step = max(1, 30000 // per_row)
    for i in range(0, len(rows), step):
        batch = stmt.values(list(rows[i:i + step]))
        batch = batch.on_conflict_do_update(
            index_elements=list(key), set_={c: getattr(batch.excluded, c) for c in cols})
        session.execute(batch)


def delete_version(session: Session, document_id: str, version: int) -> list[str]:
    """Remove one version's chunks, sections and text. Returns the chunk IDs
    removed (so the caller can delete their vectors)."""
    chunk_ids = list(session.scalars(select(Chunk.id).where(
        Chunk.document_id == document_id, Chunk.version == version)))
    session.execute(delete(Chunk).where(Chunk.document_id == document_id,
                                        Chunk.version == version))
    # Children before parents: the self-referencing FK cascades either way,
    # but deleting deepest-first avoids relying on that order.
    session.execute(delete(Section).where(Section.document_id == document_id,
                                          Section.version == version))
    session.execute(delete(DocumentText).where(DocumentText.document_id == document_id,
                                               DocumentText.version == version))
    return chunk_ids


def write_version(session: Session, document_id: str, version: int, text_: str,
                  sections: Sequence[dict], chunks: Sequence[dict]) -> None:
    """Write one version's text, sections and chunks with upserts. FTS5 rows
    follow through triggers, in the same transaction."""
    _upsert(session, DocumentText,
            [{"document_id": document_id, "version": version, "text": text_}],
            ["document_id", "version"])
    _upsert(session, Section, sections, ["id"])
    _upsert(session, Chunk, chunks, ["id"])


def versions_of(session: Session, document_id: str) -> list[int]:
    rows = session.scalars(select(Chunk.version).where(Chunk.document_id == document_id)
                           .distinct())
    texts = session.scalars(select(DocumentText.version)
                            .where(DocumentText.document_id == document_id))
    return sorted(set(rows) | set(texts))


def chunk_ids_of_version(session: Session, document_id: str, version: int) -> list[str]:
    return list(session.scalars(select(Chunk.id).where(
        Chunk.document_id == document_id, Chunk.version == version).order_by(Chunk.ordinal)))


def current_chunks(session: Session, chunk_ids: Sequence[str],
                   allowed_collection_ids: Iterable[str]) -> dict[str, Chunk]:
    """Chunks by ID, keeping only those that are visible to the caller *and*
    belong to their document's current version. Search results from the
    vector store pass through here, so stale vectors (old versions, deleted
    documents) and other tenants' chunks are dropped."""
    ids = _ids(allowed_collection_ids)
    if not chunk_ids or not ids:
        return {}
    rows = session.scalars(
        select(Chunk).join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_(list(chunk_ids)), Chunk.collection_id.in_(ids),
               Document.collection_id.in_(ids),
               Chunk.version == Document.current_version))
    return {c.id: c for c in rows}


def keyword_search(session: Session, match: str, allowed_collection_ids: Iterable[str],
                   k: int, document_ids: Sequence[str] | None = None,
                   section_ids: Sequence[str] | None = None) -> list[tuple[Chunk, float]]:
    """BM25 over the FTS5 index, current versions only. Returns
    [(chunk, score)] with **higher = better** (FTS5's bm25() is lower = better)."""
    ids = _ids(allowed_collection_ids)
    if not ids or not match:
        return []
    params = {"match": match, "k": k}
    coll = ", ".join(f":c{i}" for i in range(len(ids)))
    params.update({f"c{i}": cid for i, cid in enumerate(ids)})
    doc_filter = ""
    if document_ids:
        doc_filter = " AND c.document_id IN (" + ", ".join(
            f":d{i}" for i in range(len(document_ids))) + ")"
        params.update({f"d{i}": did for i, did in enumerate(document_ids)})
    if section_ids:
        doc_filter += " AND c.section_id IN (" + ", ".join(
            f":s{i}" for i in range(len(section_ids))) + ")"
        params.update({f"s{i}": sid for i, sid in enumerate(section_ids)})
    sql = text(
        "SELECT c.id AS id, -bm25(chunk_fts) AS score FROM chunk_fts "
        "JOIN chunk c ON c.rowid = chunk_fts.rowid "
        "JOIN document d ON d.id = c.document_id "
        f"WHERE chunk_fts MATCH :match AND c.collection_id IN ({coll}) "
        f"AND d.collection_id IN ({coll}) AND c.version = d.current_version{doc_filter} "
        "ORDER BY bm25(chunk_fts) LIMIT :k")
    hits = session.execute(sql, params).all()
    chunks = {c.id: c for c in session.scalars(select(Chunk).where(
        Chunk.id.in_([h.id for h in hits])))}
    return [(chunks[h.id], float(h.score)) for h in hits if h.id in chunks]


def section_tree(session: Session, document_id: str, version: int) -> list[Section]:
    return list(session.scalars(select(Section).where(
        Section.document_id == document_id, Section.version == version)
        .order_by(Section.ordinal)))


def counts(session: Session) -> dict[str, int]:
    """Row counts used by the consistency check and tests."""
    return {
        "chunks": session.scalar(select(func.count(Chunk.id))) or 0,
        "fts": session.scalar(text("SELECT count(*) FROM chunk_fts_docsize")) or 0,   # index rows, not content
        "sections": session.scalar(select(func.count(Section.id))) or 0,
    }


# ── Jobs (state changes live in cadis.jobs.queue) ─────────────────────────────

def create_job(session: Session, type_: str, document_id: str | None, max_attempts: int,
               payload: dict | None = None) -> Job:
    job = Job(id=new_id(), type=type_, document_id=document_id, status=JobStatus.PENDING,
              max_attempts=max_attempts, payload=payload)
    session.add(job)
    session.flush()
    return job


def get_job(session: Session, job_id: str, allowed_collection_ids: Iterable[str]) -> Job | None:
    ids = _ids(allowed_collection_ids)
    job = session.get(Job, job_id)
    if job is None or job.document_id is None:
        return None
    doc = session.get(Document, job.document_id)
    if doc is None or doc.collection_id not in ids:
        return None
    return job


def latest_job_for(session: Session, document_id: str) -> Job | None:
    return session.scalars(select(Job).where(Job.document_id == document_id)
                           .order_by(Job.created_at.desc())).first()


def active_job_for(session: Session, document_id: str) -> Job | None:
    return session.scalars(select(Job).where(
        Job.document_id == document_id,
        Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]))).first()


def set_document_fields(session: Session, document_id: str, **fields) -> int:
    fields.setdefault("updated_at", utcnow())
    return session.execute(update(Document).where(Document.id == document_id)
                           .values(**fields)).rowcount

