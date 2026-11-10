"""/jobs/{id} — job state, a Server-Sent Events progress stream, manual retry."""

import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from cadis.api.deps import get_allowed_collections, get_db
from cadis.api.schemas import JobOut
from cadis.jobs import queue
from cadis.jobs.states import TERMINAL
from cadis.storage import repositories
from cadis.storage.db import session_scope

router = APIRouter(prefix="/jobs", tags=["jobs"])

SSE_POLL_SECONDS = 0.5
SSE_KEEPALIVE_SECONDS = 15
SSE_MAX_SECONDS = 3600


def _job_or_404(db, job_id, allowed):
    job = repositories.get_job(db, job_id, allowed)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db),
            allowed: list[str] = Depends(get_allowed_collections)):
    return JobOut.model_validate(_job_or_404(db, job_id, allowed))


@router.post("/{job_id}/retry", response_model=JobOut, status_code=202)
def retry_job(job_id: str, db: Session = Depends(get_db),
              allowed: list[str] = Depends(get_allowed_collections)):
    job = _job_or_404(db, job_id, allowed)
    if not queue.retry(job.id):
        raise HTTPException(409, f"Only FAILED jobs can be retried (this one is {job.status})")
    db.expire_all()
    return JobOut.model_validate(repositories.get_job(db, job_id, allowed))


@router.get("/{job_id}/events")
def job_events(job_id: str, db: Session = Depends(get_db),
               allowed: list[str] = Depends(get_allowed_collections)):
    """SSE stream: one ``data:`` event each time the job's status, stage or
    progress changes; the stream ends when the job is COMPLETED or FAILED."""
    _job_or_404(db, job_id, allowed)
    allowed = list(allowed)

    def stream():
        last, last_sent, started = None, time.monotonic(), time.monotonic()
        yield "retry: 2000\n\n"
        while time.monotonic() - started < SSE_MAX_SECONDS:
            with session_scope() as s:
                job = repositories.get_job(s, job_id, allowed)
                data = JobOut.model_validate(job).model_dump(mode="json") if job else None
            if data is None:
                yield "event: gone\ndata: {}\n\n"
                return
            state = (data["status"], data["stage"], round(data["progress"], 3))
            if state != last:
                yield f"data: {json.dumps(data)}\n\n"
                last, last_sent = state, time.monotonic()
                if data["status"] in TERMINAL:
                    return
            elif time.monotonic() - last_sent > SSE_KEEPALIVE_SECONDS:
                yield ": keep-alive\n\n"
                last_sent = time.monotonic()
            time.sleep(SSE_POLL_SECONDS)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
