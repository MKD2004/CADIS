"""Compare SQLite (the source of truth) with ChromaDB and the FTS5 index, and
repair differences (DECISIONS ADR-014).

  * orphan vectors — in ChromaDB but not in SQLite (a delete that failed half
    way, or a job that died after upserting) → deleted;
  * missing vectors — current-version chunks without a vector → re-embedded
    with the same contextual header the pipeline uses;
  * FTS5 — ``integrity-check``; on failure the index is rebuilt from ``chunk``.

Documents with a queued or running job are skipped: their state is in flux
and the job itself will finish or retry.
"""

from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError

from cadis.config import get_settings
from cadis.index.vector_store import VectorRecord, get_vector_store
from cadis.ingest.pipeline import contextual_header, embed_text, token_spans_for
from cadis.ingest.sections import PATH_SEP
from cadis.models import registry
from cadis.storage.db import session_scope
from cadis.storage.tables import Chunk, Document, Job, JobStatus


@dataclass
class Report:
    sqlite_chunks: int = 0
    vectors: int = 0
    orphan_vectors: list[str] = field(default_factory=list)
    missing_vectors: list[str] = field(default_factory=list)
    fts_ok: bool = True
    skipped_documents: list[str] = field(default_factory=list)
    repaired: bool = False

    @property
    def ok(self) -> bool:
        return not self.orphan_vectors and not self.missing_vectors and self.fts_ok

    def summary(self) -> str:
        return (f"SQLite chunks: {self.sqlite_chunks} · vectors: {self.vectors} · "
                f"orphan vectors: {len(self.orphan_vectors)} · missing vectors: "
                f"{len(self.missing_vectors)} · FTS5: {'ok' if self.fts_ok else 'BROKEN'} · "
                f"skipped (job running): {len(self.skipped_documents)}"
                + (" · repaired" if self.repaired else ""))


def check(repair: bool = False) -> Report:
    store = get_vector_store()
    report = Report()
    with session_scope() as db:
        busy = set(db.scalars(select(Job.document_id).where(
            Job.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]))))
        report.skipped_documents = sorted(d for d in busy if d)
        all_chunk_ids = set(db.scalars(select(Chunk.id)))
        current = db.execute(
            select(Chunk.id, Chunk.document_id)
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.version == Document.current_version)).all()
        report.sqlite_chunks = len(all_chunk_ids)
        try:
            db.execute(text("INSERT INTO chunk_fts(chunk_fts) VALUES('integrity-check')"))
        except DatabaseError:
            report.fts_ok = False

    vector_ids = store.all_ids()
    report.vectors = len(vector_ids)
    # Vectors whose chunk row is gone. (Vectors of an in-flight version have
    # chunk rows, because chunks are written before vectors.)
    report.orphan_vectors = sorted(vector_ids - all_chunk_ids)
    report.missing_vectors = sorted(cid for cid, doc in current
                                    if cid not in vector_ids and doc not in busy)

    if repair and not report.ok:
        if report.orphan_vectors:
            store.delete_ids(report.orphan_vectors)
        if report.missing_vectors:
            _reembed(report.missing_vectors)
        if not report.fts_ok:
            with session_scope() as db:
                db.execute(text("INSERT INTO chunk_fts(chunk_fts) VALUES('rebuild')"))
        report.repaired = True
    return report


def _reembed(chunk_ids: list[str]) -> None:
    s = get_settings()
    embedder = registry.get_embedder()
    spans = token_spans_for(embedder.tokenizer)
    store = get_vector_store()
    with session_scope() as db:
        rows = db.execute(select(Chunk, Document.title, Document.filename)
                          .join(Document, Document.id == Chunk.document_id)
                          .where(Chunk.id.in_(chunk_ids))).all()
        items = []
        for chunk, title, filename in rows:
            doc_title = title or filename.rsplit(".", 1)[0]
            titles = chunk.section_path.split(PATH_SEP) if chunk.section_path else []
            header = contextual_header(doc_title, titles, spans, s.chunk_header_max_tokens)
            items.append((chunk, embed_text(header, chunk.text)))
    for i in range(0, len(items), s.embed_batch_size):
        batch = items[i:i + s.embed_batch_size]
        vectors = embedder.encode([t for _, t in batch])
        store.upsert([VectorRecord(c.id, v, c.document_id, c.collection_id, c.version,
                                   c.page or 0, c.section_id, c.section_path)
                      for (c, _), v in zip(batch, vectors)])
