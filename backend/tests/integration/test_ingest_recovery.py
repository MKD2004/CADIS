"""Crash and restart during ingestion leaves no duplicates (ADR-013, ADR-014).

Real SQLite + real ChromaDB in a temp dir. A "crash" is a BaseException
raised inside the job: like a killed process, it skips the worker's error
handling and leaves the job PROCESSING with a lease. Recovery then has to
finish the job from scratch.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select, update

from cadis.ingest import consistency, pipeline
from cadis.ingest.pipeline import HANDLERS
from cadis.ingest.service import delete_document, upload
from cadis.jobs.worker import Worker
from cadis.retrieval import search
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.files import FileStore
from cadis.storage.tables import Chunk, Document, Job, utcnow
from conftest import EVAL_DOCS


class Crash(BaseException):
    """Simulates the process being killed."""


@pytest.fixture
def setup(v2_chroma, monkeypatch):
    monkeypatch.setenv("CADIS_EMBED_BATCH_SIZE", "4")      # several embedding batches
    from cadis.config import get_settings
    get_settings.cache_clear()
    with session_scope() as s:
        col = repositories.create_collection(s, "default", "C")
        r = upload(s, col.id, "energy.txt", (EVAL_DOCS / "energy.txt").read_bytes())
    return v2_chroma, col.id, r.document_id, r.job_id


def state(store, doc_id):
    with session_scope() as s:
        doc = s.get(Document, doc_id)
        chunk_ids = set(s.scalars(select(Chunk.id).where(Chunk.document_id == doc_id)))
        counts = repositories.counts(s)
    return {"version": doc.current_version, "status": doc.status, "chunks": chunk_ids,
            "vectors": store.ids_for_document(doc_id), "fts": counts["fts"],
            "sqlite": counts["chunks"]}


def crash_at(monkeypatch, stage, after_calls=1):
    """Crash the first time the job reports `stage` for the n-th time."""
    real = pipeline.JobContext.report
    seen = {"n": 0, "armed": True}

    def report(self, st, progress):
        if seen["armed"] and st == stage:
            seen["n"] += 1
            if seen["n"] >= after_calls:
                seen["armed"] = False
                raise Crash()
        return real(self, st, progress)

    monkeypatch.setattr(pipeline.JobContext, "report", report)


def restart_and_finish():
    """A new worker after a restart: the dead worker's lease runs out, the
    job is recovered and run again."""
    with session_scope() as s:
        s.execute(update(Job).where(Job.status == "PROCESSING")
                  .values(locked_until=utcnow() - timedelta(seconds=1)))
    worker = Worker(HANDLERS, "worker-after-restart")
    worker.recover()
    worker.drain()


def assert_consistent(st):
    assert st["chunks"] == st["vectors"] and st["chunks"]
    assert st["fts"] == st["sqlite"]
    assert consistency.check().ok


@pytest.mark.parametrize("stage, calls", [("storing", 1), ("embedding", 2), ("indexing", 1)])
def test_crash_mid_ingestion_then_restart(setup, monkeypatch, stage, calls):
    store, _, doc_id, job_id = setup
    crash_at(monkeypatch, stage, calls)
    with pytest.raises(Crash):
        Worker(HANDLERS, "doomed-worker").drain()
    with session_scope() as s:
        assert s.get(Job, job_id).status == "PROCESSING"            # stuck, as after a kill
        assert s.get(Document, doc_id).current_version == 0          # nothing visible yet
    assert search.keyword_search("Harlow Ridge battery", [setup[1]]) == []

    restart_and_finish()
    st = state(store, doc_id)
    with session_scope() as s:
        job = s.get(Job, job_id)
        assert job.status == "COMPLETED" and job.attempts == 2
    assert st["version"] == 1 and st["status"] == "READY"
    assert_consistent(st)


def test_running_a_job_twice_gives_the_same_state(setup):
    store, _, doc_id, job_id = setup
    Worker(HANDLERS, "w").drain()
    first = state(store, doc_id)
    # Pretend the COMPLETED write was lost and the job ran again.
    with session_scope() as s:
        s.execute(update(Job).where(Job.id == job_id).values(status="PENDING"))
        s.execute(update(Document).where(Document.id == doc_id).values(current_version=0))
    Worker(HANDLERS, "w").drain()
    second = state(store, doc_id)
    assert first == second
    assert_consistent(second)


def test_live_version_stays_searchable_while_reingest_crashes(setup, monkeypatch):
    store, col_id, doc_id, _ = setup
    Worker(HANDLERS, "w").drain()
    v1 = state(store, doc_id)
    with session_scope() as s:
        doc = s.get(Document, doc_id)
        from cadis.ingest.service import reingest
        reingest(s, doc)
    crash_at(monkeypatch, "indexing")                    # v2 fully written, not yet flipped
    with pytest.raises(Crash):
        Worker(HANDLERS, "doomed").drain()

    hits = search.keyword_search("Harlow Ridge battery", [col_id])
    assert hits and all(h.chunk_id in v1["chunks"] for h in hits)    # only v1 visible
    hits = search.dense_search("Harlow Ridge battery", [col_id])
    assert hits and all(h.chunk_id in v1["chunks"] for h in hits)

    restart_and_finish()
    v2 = state(store, doc_id)
    assert v2["version"] == 2 and not v2["chunks"] & v1["chunks"]
    assert len(v2["chunks"]) == len(v1["chunks"])
    assert_consistent(v2)


def test_delete_removes_chunks_vectors_fts_and_file(setup):
    store, col_id, doc_id, _ = setup
    Worker(HANDLERS, "w").drain()
    with session_scope() as s:
        sha = s.get(Document, doc_id).sha256
    assert delete_document(doc_id, [col_id])
    with session_scope() as s:
        assert repositories.counts(s) == {"chunks": 0, "fts": 0, "sections": 0}
    assert store.count() == 0
    assert not FileStore().exists(sha)
    assert search.keyword_search("Harlow Ridge", [col_id]) == []


def test_consistency_check_repairs_orphans_and_missing_vectors(setup):
    store, _, doc_id, _ = setup
    Worker(HANDLERS, "w").drain()
    before = state(store, doc_id)
    victim = sorted(before["vectors"])[0]
    store.delete_ids([victim])
    from cadis.index.vector_store import VectorRecord
    store.upsert([VectorRecord("orphan-1", [0.1] * 16, doc_id, "x", 1, 1, "s", "")])

    report = consistency.check()
    assert report.orphan_vectors == ["orphan-1"] and report.missing_vectors == [victim]
    assert not report.ok
    consistency.check(repair=True)
    after = state(store, doc_id)
    assert after["vectors"] == before["vectors"]
    assert consistency.check().ok
