"""Job queue operations on the ``job`` table (DECISIONS ADR-013).

The database is the source of truth. Every state change is one conditional
UPDATE, and every update a worker makes after claiming is *fenced* by
``locked_by = <worker id> AND status = 'PROCESSING'``: a worker whose lease
expired (and whose job was claimed by someone else) can no longer change it.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update

from cadis.jobs import states
from cadis.storage.db import session_scope
from cadis.storage.tables import Job, utcnow


@dataclass
class ClaimedJob:
    id: str
    type: str
    document_id: str | None
    payload: dict
    attempts: int
    max_attempts: int


def claim(worker_id: str, lease_seconds: int, types: list[str] | None = None) -> ClaimedJob | None:
    """Atomically take the oldest PENDING job. Returns None if there is none.
    If another worker takes the same job first, the update changes 0 rows and
    we try the next one."""
    for _ in range(5):
        with session_scope() as s:
            q = select(Job.id).where(Job.status == states.PENDING)
            if types:
                q = q.where(Job.type.in_(types))
            job_id = s.scalar(q.order_by(Job.created_at, Job.id).limit(1))
            if job_id is None:
                return None
            now = utcnow()
            changed = s.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == states.PENDING)
                .values(status=states.PROCESSING, locked_by=worker_id,
                        locked_until=now + timedelta(seconds=lease_seconds),
                        attempts=Job.attempts + 1, updated_at=now)).rowcount
            if changed == 1:
                job = s.get(Job, job_id)
                s.refresh(job)
                return ClaimedJob(job.id, job.type, job.document_id, dict(job.payload or {}),
                                  job.attempts, job.max_attempts)
    return None


def heartbeat(job_id: str, worker_id: str, lease_seconds: int, *, stage: str | None = None,
              progress: float | None = None) -> bool:
    """Extend the lease (and record progress). False = we no longer own the job."""
    values = {"locked_until": utcnow() + timedelta(seconds=lease_seconds), "updated_at": utcnow()}
    if stage is not None:
        values["stage"] = stage
    if progress is not None:
        values["progress"] = max(0.0, min(1.0, float(progress)))
    with session_scope() as s:
        return s.execute(update(Job).where(
            Job.id == job_id, Job.locked_by == worker_id, Job.status == states.PROCESSING)
            .values(**values)).rowcount == 1


def complete(job_id: str, worker_id: str) -> bool:
    with session_scope() as s:
        return s.execute(update(Job).where(
            Job.id == job_id, Job.locked_by == worker_id, Job.status == states.PROCESSING)
            .values(status=states.COMPLETED, progress=1.0, stage="done", locked_until=None,
                    error=None, updated_at=utcnow())).rowcount == 1


def fail(job_id: str, worker_id: str, error: str, permanent: bool = False) -> str | None:
    """Record an error. Returns the new status (PENDING to retry, FAILED when
    out of attempts or permanent), or None if we no longer own the job."""
    with session_scope() as s:
        job = s.get(Job, job_id)
        if job is None or job.locked_by != worker_id or job.status != states.PROCESSING:
            return None
        status = states.FAILED if permanent or job.attempts >= job.max_attempts else states.PENDING
        changed = s.execute(update(Job).where(
            Job.id == job_id, Job.locked_by == worker_id, Job.status == states.PROCESSING)
            .values(status=status, error=error[:4000], locked_until=None, locked_by=None,
                    updated_at=utcnow())).rowcount
        return status if changed == 1 else None


def recover_expired() -> list[ClaimedJob]:
    """PROCESSING jobs whose lease ran out (the worker crashed or the server
    restarted) go back to PENDING, or to FAILED when out of attempts.
    Returns the jobs that became FAILED so their handlers can clean up."""
    failed: list[ClaimedJob] = []
    now = utcnow()
    with session_scope() as s:
        expired = list(s.scalars(select(Job).where(
            Job.status == states.PROCESSING, Job.locked_until < now)))
        for job in expired:
            out_of_attempts = job.attempts >= job.max_attempts
            status = states.FAILED if out_of_attempts else states.PENDING
            error = job.error
            if out_of_attempts:
                error = (f"{job.error}; " if job.error else "") + "lease expired on the last attempt"
            changed = s.execute(update(Job).where(
                Job.id == job.id, Job.status == states.PROCESSING, Job.locked_until < now)
                .values(status=status, locked_by=None, locked_until=None, updated_at=now,
                        error=error)).rowcount
            if changed and out_of_attempts:
                failed.append(ClaimedJob(job.id, job.type, job.document_id,
                                         dict(job.payload or {}), job.attempts, job.max_attempts))
    return failed


def retry(job_id: str) -> bool:
    """Manual retry of a FAILED job: back to PENDING with fresh attempts."""
    with session_scope() as s:
        return s.execute(update(Job).where(Job.id == job_id, Job.status == states.FAILED)
                         .values(status=states.PENDING, attempts=0, error=None, stage=None,
                                 progress=0.0, updated_at=utcnow())).rowcount == 1
