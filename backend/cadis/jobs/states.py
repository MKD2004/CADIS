"""Job states and the moves allowed between them (DECISIONS ADR-013).

    PENDING ──claim──▶ PROCESSING ──done──▶ COMPLETED
       ▲                  │  │
       └── error, attempts left / lease expired
                          │
                          └── error, no attempts left ──▶ FAILED ──manual retry──▶ PENDING
"""

from cadis.storage.tables import JobStatus

PENDING = JobStatus.PENDING
PROCESSING = JobStatus.PROCESSING
COMPLETED = JobStatus.COMPLETED
FAILED = JobStatus.FAILED

TERMINAL = frozenset({COMPLETED, FAILED})

ALLOWED = {
    PENDING: {PROCESSING},
    PROCESSING: {COMPLETED, PENDING, FAILED},
    FAILED: {PENDING},
    COMPLETED: set(),
}


def can_move(src: str, dst: str) -> bool:
    return dst in ALLOWED.get(src, set())


class PermanentJobError(Exception):
    """An error that retrying cannot fix (bad file, no text). The job goes
    straight to FAILED instead of using up its attempts."""


class JobLost(Exception):
    """This worker no longer owns the job (lease expired and another worker
    claimed it, or the job/document was deleted). Stop without writing."""
