"""Exact (brute-force) vector search — the baseline for the HNSW index (ADR-012).

Loads every vector from a ``VectorStore`` into one NumPy matrix and answers
searches with a full cosine scan, using the same filters as the real store.
Used by tests and by ``scripts/bench_retrieval.py`` to measure how much the
approximate index loses (recall of HNSW against exact results).
"""

from collections.abc import Sequence

import numpy as np

from cadis.index.vector_store import VectorHit, VectorStore


class ExactIndex:
    def __init__(self, ids: list[str], vectors, metadatas: list[dict]):
        self.ids = ids
        m = np.asarray(vectors, dtype=np.float32).reshape(len(ids), -1)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        self.matrix = m / np.where(norms == 0, 1.0, norms)
        self.metas = metadatas
        self._collection = np.array([md.get("collection_id", "") for md in metadatas])
        self._document = np.array([md.get("document_id", "") for md in metadatas])
        self._section = np.array([md.get("section_id", "") for md in metadatas])

    @classmethod
    def from_store(cls, store: VectorStore) -> "ExactIndex":
        return cls(*store.export())

    def search(self, vector, allowed_collection_ids: Sequence[str], k: int,
               document_ids: Sequence[str] | None = None,
               section_ids: Sequence[str] | None = None) -> list[VectorHit]:
        allowed = list(allowed_collection_ids)
        if not allowed or not self.ids or k <= 0:
            return []
        mask = np.isin(self._collection, allowed)
        if document_ids:
            mask &= np.isin(self._document, list(document_ids))
        if section_ids:
            mask &= np.isin(self._section, list(section_ids))
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return []
        q = np.asarray(vector, dtype=np.float32)
        q = q / (np.linalg.norm(q) or 1.0)
        sims = self.matrix[idx] @ q
        top = idx[np.argsort(-sims)[:k]]
        order = {i: s for i, s in zip(idx, sims)}
        return [VectorHit(self.ids[i], float(order[i]), self._document[i],
                          self.metas[i].get("section_path", "")) for i in top]


def overlap_at_k(approx: list[VectorHit], exact: list[VectorHit], k: int) -> float:
    """Share of the exact top-k that the approximate search also returned."""
    truth = {h.id for h in exact[:k]}
    if not truth:
        return 1.0
    return len(truth & {h.id for h in approx[:k]}) / len(truth)
