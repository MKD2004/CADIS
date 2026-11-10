"""Reciprocal Rank Fusion (DECISIONS ADR-009).

Each ranked list gives a chunk ``1 / (k + rank)``; scores add up across
lists. Only ranks are used, so dense cosine scores and BM25 scores never have
to be put on the same scale. A chunk found by several lists — dense *and*
keyword, or the unfiltered *and* a section-filtered search — rises to the top.
"""

from collections import defaultdict
from collections.abc import Sequence


def rrf(lists: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked ID lists. Returns [(id, score)] best first; ties keep the
    order in which IDs were first seen, so the result is deterministic."""
    scores: dict[str, float] = defaultdict(float)
    first_seen: dict[str, int] = {}
    n = 0
    for ranked in lists:
        for rank, item in enumerate(ranked, start=1):
            scores[item] += 1.0 / (k + rank)
            if item not in first_seen:
                first_seen[item] = n
                n += 1
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))
