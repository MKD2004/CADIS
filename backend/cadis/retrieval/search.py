"""Tenant-scoped search over stored chunks (Phase 1 baseline).

Phase 1 provides the two searches separately, with the access rule built in:
``allowed_collection_ids`` is required and every hit is re-checked against
SQLite (visible collection, current document version). Phase 2 adds hybrid
fusion (RRF), re-ranking and the section soft filter on top of these.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from cadis.index.keyword_store import SqliteKeywordStore
from cadis.index.vector_store import get_vector_store
from cadis.models import registry
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.tables import Chunk


@dataclass
class SearchHit:
    chunk_id: str
    document_id: str
    section_path: str
    page: int | None
    char_start: int
    char_end: int
    text: str
    score: float
    source: str           # "dense" | "keyword"

    @classmethod
    def of(cls, chunk: Chunk, score: float, source: str) -> "SearchHit":
        return cls(chunk.id, chunk.document_id, chunk.section_path, chunk.page,
                   chunk.char_start, chunk.char_end, chunk.text, score, source)


def dense_search(question: str, allowed_collection_ids: Sequence[str], k: int = 8,
                 document_ids: Sequence[str] | None = None) -> list[SearchHit]:
    allowed = list(allowed_collection_ids)
    if not allowed or not question.strip():
        return []
    vector = registry.get_embedder().encode([question])[0]
    # Over-fetch: some candidates may be stale (old versions) and get dropped.
    hits = get_vector_store().search(vector, allowed, k * 3, document_ids)
    with session_scope() as db:
        live = repositories.current_chunks(db, [h.id for h in hits], allowed)
        out = [SearchHit.of(live[h.id], h.score, "dense") for h in hits if h.id in live]
    return out[:k]


def keyword_search(question: str, allowed_collection_ids: Sequence[str], k: int = 8,
                   document_ids: Sequence[str] | None = None) -> list[SearchHit]:
    allowed = list(allowed_collection_ids)
    if not allowed:
        return []
    with session_scope() as db:
        hits = SqliteKeywordStore().search(db, question, allowed, k, document_ids)
        live = repositories.current_chunks(db, [h.id for h in hits], allowed)
        return [SearchHit.of(live[h.id], h.score, "keyword") for h in hits if h.id in live]
