"""Job state machine, queue and worker (DECISIONS ADR-013)."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from cadis.jobs import queue, states
from cadis.jobs.worker import JobHandler, Worker
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.tables import Job, utcnow


@pytest.fixture
def doc(v2):
    with session_scope() as s:
        col = repositories.create_collection(s, "default", "C")
        d = repositories.create_document(s, col.id, "a.txt", "a" * 64, 1)
        return d.id


def new_job(doc_id, max_attempts=3, type_="test"):
    with session_scope() as s:
        return repositories.create_job(s, type_, doc_id, max_attempts).id


def job(job_id) -> Job:
    with session_scope() as s:
        return s.get(Job, job_id)


def expire(job_id):
    with session_scope() as s:
        s.execute(update(Job).where(Job.id == job_id)
                  .values(locked_until=utcnow() - timedelta(seconds=1)))


def test_allowed_moves():
    assert states.can_move("PENDING", "PROCESSING")
    assert states.can_move("PROCESSING", "PENDING")
    assert states.can_move("FAILED", "PENDING")
    assert not states.can_move("COMPLETED", "PENDING")
    assert not states.can_move("PENDING", "COMPLETED")


def test_a_job_is_claimed_only_once(doc):
    j = new_job(doc)
    first = queue.claim("w1", 60)
    assert first.id == j and first.attempts == 1
    assert queue.claim("w2", 60) is None
    row = job(j)
    assert row.status == "PROCESSING" and row.locked_by == "w1" and row.locked_until > utcnow()


def test_oldest_job_first(doc):
    a, b = new_job(doc), new_job(doc)
    assert [queue.claim("w", 60).id, queue.claim("w", 60).id] == [a, b]


def test_updates_are_fenced_by_owner(doc):
    j = new_job(doc)
    queue.claim("w1", 60)
    assert not queue.heartbeat(j, "w2", 60, progress=0.5)
    assert not queue.complete(j, "w2")
    assert queue.fail(j, "w2", "boom") is None
    assert queue.heartbeat(j, "w1", 60, stage="embedding", progress=0.5)
    assert job(j).stage == "embedding" and job(j).progress == 0.5
    assert queue.complete(j, "w1")
    assert job(j).status == "COMPLETED" and job(j).progress == 1.0


def test_errors_retry_until_attempts_run_out(doc):
    j = new_job(doc, max_attempts=2)
    queue.claim("w", 60)
    assert queue.fail(j, "w", "boom 1") == "PENDING"
    queue.claim("w", 60)
    assert queue.fail(j, "w", "boom 2") == "FAILED"
    row = job(j)
    assert row.status == "FAILED" and row.attempts == 2 and row.error == "boom 2"


def test_permanent_error_fails_at_once(doc):
    j = new_job(doc)
    queue.claim("w", 60)
    assert queue.fail(j, "w", "bad file", permanent=True) == "FAILED"


def test_expired_lease_returns_job_to_pending(doc):
    j = new_job(doc)
    queue.claim("dead-worker", 60)
    assert queue.recover_expired() == []             # lease still valid
    expire(j)
    assert queue.recover_expired() == []             # attempts left → PENDING, not failed
    assert job(j).status == "PENDING" and job(j).locked_by is None
    assert queue.claim("w2", 60).attempts == 2
    assert not queue.complete(j, "dead-worker")      # the old owner cannot finish it


def test_expired_lease_on_last_attempt_fails(doc):
    j = new_job(doc, max_attempts=1)
    queue.claim("dead-worker", 60)
    expire(j)
    [failed] = queue.recover_expired()
    assert failed.id == j and job(j).status == "FAILED"
    assert "lease expired" in job(j).error


def test_manual_retry_resets_attempts(doc):
    j = new_job(doc, max_attempts=1)
    queue.claim("w", 60)
    queue.fail(j, "w", "boom")
    assert queue.retry(j)
    row = job(j)
    assert row.status == "PENDING" and row.attempts == 0 and row.error is None
    assert not queue.retry(j)                        # only FAILED jobs


def test_worker_runs_handler_and_completes_last(doc):
    seen = []

    def run(ctx):
        ctx.report("working", 0.5)
        seen.append((ctx.document_id, job(ctx.job.id).status, job(ctx.job.id).stage))

    j = new_job(doc)
    assert Worker({"test": JobHandler(run)}, "w").drain() == 1
    assert seen == [(doc, "PROCESSING", "working")]
    assert job(j).status == "COMPLETED"


def test_worker_records_failures_and_calls_on_failed(doc):
    failed = []

    def run(ctx):
        raise states.PermanentJobError("no text found")

    j = new_job(doc)
    Worker({"test": JobHandler(run, lambda jb, err: failed.append((jb.id, err)))}, "w").drain()
    assert job(j).status == "FAILED" and failed == [(j, "no text found")]


def test_worker_retries_transient_errors(doc):
    calls = []

    def run(ctx):
        calls.append(ctx.job.attempts)
        if len(calls) < 3:
            raise RuntimeError("flaky")

    j = new_job(doc, max_attempts=3)
    Worker({"test": JobHandler(run)}, "w").drain()
    assert calls == [1, 2, 3] and job(j).status == "COMPLETED"


def test_handler_stops_when_job_is_lost(doc):
    def run(ctx):
        expire(ctx.job.id)
        queue.recover_expired()
        queue.claim("other-worker", 60)              # someone else owns it now
        ctx.report("embedding", 0.5)                 # must raise JobLost
        raise AssertionError("handler kept running")

    j = new_job(doc)
    Worker({"test": JobHandler(run)}, "w").drain(max_jobs=1)
    row = job(j)
    assert row.status == "PROCESSING" and row.locked_by == "other-worker"
