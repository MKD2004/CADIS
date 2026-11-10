"""Cross-encoder re-ranking (DECISIONS ADR-010).

The bi-encoder embeds the question and each chunk separately; the
cross-encoder reads them *together* and scores relevance much more
accurately, but is too slow for every chunk — so it only sees the ~30 fused
candidates. Each candidate is scored with its "Document › Section" header so
"the supply agreement" in a question can match the right contract.
"""

from collections.abc import Sequence

from cadis.models import registry


def rerank(question: str, items: Sequence[tuple[str, str]]) -> dict[str, float]:
    """items: [(id, text)]. Returns {id: score} (higher = more relevant)."""
    if not items:
        return {}
    model = registry.get_reranker()
    scores = model.predict([(question, text) for _, text in items])
    return {item_id: float(score) for (item_id, _), score in zip(items, scores)}
