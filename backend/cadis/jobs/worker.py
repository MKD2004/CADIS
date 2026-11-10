"""In-process job worker (DECISIONS ADR-013).

Loop: recover expired leases → claim a job → run its handler while a
heartbeat thread keeps the lease alive → mark COMPLETED (last) or record the
error. Handlers report progress through ``JobContext.report``; if the worker
has lost the job (lease taken over, job deleted), ``report`` raises
``JobLost`` so the handler stops before writing anything else.

Because state lives in the database, moving execution to RQ/Celery later
changes only this file.
"""

import logging
import threading
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from cadis.config import get_settings
from cadis.jobs import queue
from cadis.jobs.states import JobLost, PermanentJobError

log = logging.getLogger("cadis.jobs")


class JobContext:
    def __init__(self, job: queue.ClaimedJob, worker_id: str):
        self.job = job
        self.worker_id = worker_id
        self.lost = threading.Event()
        self._last_write = 0.0
        self._last_stage: str | None = None

    @property
    def document_id(self) -> str | None:
        return self.job.document_id

    @property
    def payload(self) -> dict:
        return self.job.payload

    def check(self) -> None:
        if self.lost.is_set():
            raise JobLost(self.job.id)

    def report(self, stage: str, progress: float) -> None:
        """Record progress (throttled) and extend the lease."""
        self.check()
        now = time.monotonic()
        if stage == self._last_stage and now - self._last_write < 1.0:
            return
        s = get_settings()
        if not queue.heartbeat(self.job.id, self.worker_id, s.job_lease_seconds,
                               stage=stage, progress=progress):
            self.lost.set()
            raise JobLost(self.job.id)
        self._last_write, self._last_stage = now, stage


@dataclass
class JobHandler:
    run: Callable[[JobContext], None]
    # Called once when a job ends in FAILED (no attempts left, or permanent),
    # e.g. to mark its document as failed.
    on_failed: Callable[[queue.ClaimedJob, str], None] | None = None


class Worker:
    def __init__(self, handlers: dict[str, JobHandler], worker_id: str | None = None):
        self.handlers = handlers
        self.worker_id = worker_id or f"w-{uuid.uuid4().hex[:12]}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_recover = 0.0

    # ── lifecycle ──────────────────────────────────────────────────────────
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self.run_forever, name="cadis-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout)

    def run_forever(self) -> None:
        log.info("worker %s started", self.worker_id)
        while not self._stop.is_set():
            try:
                worked = self.run_once()
            except Exception:                       # never let the loop die
                log.exception("worker loop error")
                worked = False
            if not worked:
                self._stop.wait(get_settings().job_poll_seconds)

    # ── one iteration ──────────────────────────────────────────────────────
    def recover(self) -> int:
        failed = queue.recover_expired()
        for job in failed:
            self._on_failed(job, "lease expired on the last attempt")
        self._last_recover = time.monotonic()
        return len(failed)

    def run_once(self) -> bool:
        s = get_settings()
        if time.monotonic() - self._last_recover >= s.job_recover_seconds:
            self.recover()
        job = queue.claim(self.worker_id, s.job_lease_seconds, list(self.handlers))
        if job is None:
            return False
        self._run(job)
        return True

    def _run(self, job: queue.ClaimedJob) -> None:
        s = get_settings()
        ctx = JobContext(job, self.worker_id)
        done = threading.Event()

        def beat():
            while not done.wait(s.job_heartbeat_seconds):
                if not queue.heartbeat(job.id, self.worker_id, s.job_lease_seconds):
                    ctx.lost.set()
                    return

        hb = threading.Thread(target=beat, name=f"heartbeat-{job.id[:8]}", daemon=True)
        hb.start()
        try:
            self.handlers[job.type].run(ctx)
            ctx.check()
            if not queue.complete(job.id, self.worker_id):
                log.warning("job %s finished but was no longer ours", job.id)
        except JobLost:
            log.warning("job %s lost (lease taken over or deleted); stopped", job.id)
        except PermanentJobError as e:
            if queue.fail(job.id, self.worker_id, str(e), permanent=True) == "FAILED":
                self._on_failed(job, str(e))
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            log.error("job %s attempt %d failed: %s\n%s", job.id, job.attempts, msg,
                      traceback.format_exc())
            if queue.fail(job.id, self.worker_id, msg) == "FAILED":
                self._on_failed(job, msg)
        finally:
            done.set()
            hb.join(1.0)

    def _on_failed(self, job: queue.ClaimedJob, error: str) -> None:
        handler = self.handlers.get(job.type)
        if handler and handler.on_failed:
            try:
                handler.on_failed(job, error)
            except Exception:
                log.exception("on_failed hook for job %s raised", job.id)

    def drain(self, max_jobs: int = 100) -> int:
        """Run jobs until none are left (tests and scripts)."""
        n = 0
        while n < max_jobs and self.run_once():
            n += 1
        return n
