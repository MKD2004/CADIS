"""Vector store interface + ChromaDB implementation (DECISIONS ADR-007).

Nothing outside this file imports ``chromadb``. Swapping to pgvector or
Qdrant later means writing another ``VectorStore`` here.

Every search requires ``allowed_collection_ids`` (ADR-015). Results are
*candidates*: the caller still checks them against SQLite (current version,
visibility) via ``repositories.current_chunks``, so vectors left behind by an
interrupted job can never leak into answers.
"""

import threading
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from cadis.config import get_settings

COLLECTION_NAME = "chunks"


class EmbeddingModelMismatch(RuntimeError):
    """The index was built with a different embedding model (re-ingest needed)."""


@dataclass
class VectorRecord:
    id: str
    vector: Sequence[float]
    document_id: str
    collection_id: str
    version: int
    page: int
    section_id: str
    section_path: str


@dataclass
class VectorHit:
    id: str
    score: float          # cosine similarity, higher = better
    document_id: str
    section_path: str


class VectorStore(Protocol):
    def upsert(self, records: Sequence[VectorRecord]) -> None: ...
    def search(self, vector: Sequence[float], allowed_collection_ids: Sequence[str], k: int,
               document_ids: Sequence[str] | None = None,
               section_ids: Sequence[str] | None = None) -> list[VectorHit]: ...
    def delete_document(self, document_id: str, keep_version: int | None = None) -> None: ...
    def delete_ids(self, ids: Sequence[str]) -> None: ...
    def ids_for_document(self, document_id: str) -> set[str]: ...
    def all_ids(self) -> set[str]: ...
    def count(self) -> int: ...
    def export(self) -> tuple[list[str], list[list[float]], list[dict]]: ...


class ChromaVectorStore:
    """Embedded ChromaDB (persistent, on disk under ``data_dir/chroma``)."""

    def __init__(self, path: str, embedding_model: str):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=path, settings=ChromaSettings(anonymized_telemetry=False))
        self._col = self._client.get_or_create_collection(
            COLLECTION_NAME, embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"embedding_model": embedding_model})
        stored = (self._col.metadata or {}).get("embedding_model")
        if stored and stored != embedding_model and self._col.count():
            raise EmbeddingModelMismatch(
                f"Vectors were built with {stored!r} but CADIS_EMB_MODEL is {embedding_model!r}. "
                "Re-ingest the documents (or point CADIS_DATA_DIR at a fresh folder).")

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        if not records:
            return
        self._col.upsert(
            ids=[r.id for r in records],
            embeddings=[list(map(float, r.vector)) for r in records],
            metadatas=[{"document_id": r.document_id, "collection_id": r.collection_id,
                        "version": int(r.version), "page": int(r.page or 0),
                        "section_id": r.section_id, "section_path": r.section_path}
                       for r in records])

    def search(self, vector, allowed_collection_ids, k, document_ids=None, section_ids=None):
        allowed = list(allowed_collection_ids)
        if not allowed or k <= 0:
            return []
        clauses = [{"collection_id": {"$in": allowed}}]
        if document_ids:
            clauses.append({"document_id": {"$in": list(document_ids)}})
        if section_ids:
            clauses.append({"section_id": {"$in": list(section_ids)}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        n = min(k, max(1, self._col.count()))
        res = self._col.query(query_embeddings=[list(map(float, vector))], n_results=n,
                              where=where, include=["distances", "metadatas"])
        hits = []
        for cid, dist, meta in zip(res["ids"][0], res["distances"][0], res["metadatas"][0]):
            hits.append(VectorHit(cid, 1.0 - float(dist), meta.get("document_id", ""),
                                  meta.get("section_path", "")))
        return hits

    def delete_document(self, document_id, keep_version=None):
        if keep_version is None:
            self._col.delete(where={"document_id": document_id})
        else:
            self._col.delete(where={"$and": [{"document_id": document_id},
                                             {"version": {"$ne": int(keep_version)}}]})

    def delete_ids(self, ids):
        ids = list(ids)
        for i in range(0, len(ids), 5000):
            self._col.delete(ids=ids[i:i + 5000])

    def ids_for_document(self, document_id):
        return set(self._col.get(where={"document_id": document_id}, include=[])["ids"])

    def all_ids(self):
        out, offset = set(), 0
        while True:
            page = self._col.get(include=[], limit=5000, offset=offset)["ids"]
            out.update(page)
            if len(page) < 5000:
                return out
            offset += 5000

    def count(self):
        return self._col.count()

    def export(self):
        """All (ids, vectors, metadatas) — for the exact-search baseline."""
        ids, vecs, metas, offset = [], [], [], 0
        while True:
            page = self._col.get(include=["embeddings", "metadatas"], limit=5000, offset=offset)
            ids += page["ids"]
            vecs += [list(map(float, v)) for v in page["embeddings"]]
            metas += page["metadatas"]
            if len(page["ids"]) < 5000:
                return ids, vecs, metas
            offset += 5000


_store: VectorStore | None = None
_store_key: tuple | None = None
_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    """The process-wide store for the current settings (tests may replace it
    with ``set_vector_store``)."""
    global _store, _store_key
    s = get_settings()
    key = (str(s.chroma_dir.resolve()), s.emb_model)
    with _lock:
        if _store is None or _store_key != key:
            s.chroma_dir.mkdir(parents=True, exist_ok=True)
            _store, _store_key = ChromaVectorStore(key[0], s.emb_model), key
        return _store


def set_vector_store(store: VectorStore | None) -> None:
    global _store, _store_key
    with _lock:
        _store = store
        s = get_settings()
        _store_key = (str(s.chroma_dir.resolve()), s.emb_model) if store is not None else None
