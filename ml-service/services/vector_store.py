"""
services/vector_store.py
========================
ChromaDB-backed vector store service with sentence-transformer embeddings.

Architecture
────────────
• EmbeddingService   — wraps sentence-transformers, produces float32 vectors.
• VectorStoreService — wraps ChromaDB, owns collection lifecycle.
  Both are singletons; the vector store depends on the embedding service.

Design notes
────────────
• ChromaDB is run in *persistent* client mode so embeddings survive
  server restarts (stored on disk at chroma_persist_dir).
• We use a custom ChromaDB EmbeddingFunction adapter so that
  ChromaDB can call our sentence-transformer model internally —
  this means we never have to manually pass vectors to .add()/.query().
• chunk_id format: "{document_id}::{chunk_index}" — deterministic
  so upserting the same document twice is idempotent.
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from typing import ClassVar

import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings

from core.config import get_settings
from core.logging import get_logger
from models.schemas import (
    SearchResult,
    SearchResponse,
    UpsertResponse,
    CollectionStatsResponse,
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────────
#  ChromaDB EmbeddingFunction adapter
# ─────────────────────────────────────────────────────────────

class MiniLMEmbeddingFunction(EmbeddingFunction):
    """
    Adapts sentence-transformers to ChromaDB's EmbeddingFunction protocol.
    ChromaDB calls __call__(documents) → list[list[float]] internally.
    """

    def __init__(self, model_id: str) -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        logger.info("Loading embedding model: %s", model_id)
        self._model = SentenceTransformer(model_id)
        logger.info("Embedding model loaded.")

    def __call__(self, input, **kwargs):
        # Notice the underscore on _model
        return self._model.encode(input).tolist()

    def embed_query(self, input, **kwargs):
        text_to_embed = input[0] if isinstance(input, list) else input
        # We removed the [0] at the end so it returns a nested list [[...]]
        return self._model.encode([text_to_embed]).tolist()
# ─────────────────────────────────────────────────────────────
#  Vector Store Service
# ─────────────────────────────────────────────────────────────

class VectorStoreService:
    """
    Singleton service that owns the ChromaDB client and all collections.

    Public API
    ──────────
    upsert_document(...)   → stores chunked text for one document
    semantic_search(...)   → returns ranked SearchResult list
    collection_stats()     → doc count and collection list for health checks
    delete_document(...)   → removes all chunks belonging to a document_id
    """

    _instance: ClassVar[VectorStoreService | None] = None
    _lock:     ClassVar[threading.Lock]             = threading.Lock()

    # ── Constructor ───────────────────────────────────────────

    def __init__(self) -> None:
        self._settings  = get_settings()
        self._client: chromadb.ClientAPI | None      = None
        self._embed_fn: MiniLMEmbeddingFunction | None = None

    # ── Singleton accessor ────────────────────────────────────

    @classmethod
    def get_instance(cls) -> VectorStoreService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._initialise()
                    cls._instance = instance
        return cls._instance

    # ── Initialisation ────────────────────────────────────────

    def _initialise(self) -> None:
        """Set up the persistent ChromaDB client and the embedding function."""
        logger.info(
            "Initialising ChromaDB at: %s",
            self._settings.chroma_persist_dir,
        )
        self._client = chromadb.PersistentClient(
            path=self._settings.chroma_persist_dir
        )
        self._embed_fn = MiniLMEmbeddingFunction(
            self._settings.embedder_model_id
        )
        logger.info("ChromaDB ready.")

    # ── Collection helpers ────────────────────────────────────

    def _get_or_create_collection(
        self, name: str
    ) -> chromadb.Collection:
        """
        Return an existing collection or create it with our embedding function.
        Collections are namespaced per use-case (e.g. 'cadis_documents', 'cadis_legal').
        """
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},   # cosine distance for semantic search
        )

    # ── Public: upsert ────────────────────────────────────────

    def upsert_document(
        self,
        document_id:     str,
        chunks:          list[str],
        collection_name: str = "",
        extra_metadata:  dict | None = None,
    ) -> UpsertResponse:
        """
        Store chunked text for a document.
        Calling this twice with the same document_id is fully idempotent
        (ChromaDB upsert replaces existing IDs).

        Parameters
        ----------
        document_id     : Stable identifier (e.g. filename hash or UUID).
        chunks          : List of text windows to embed and store.
        collection_name : Target collection (defaults to settings value).
        extra_metadata  : Optional key-value pairs stored alongside each chunk.
        """
        coll_name = collection_name or self._settings.chroma_default_collection
        collection = self._get_or_create_collection(coll_name)

        ids:       list[str]       = []
        metadatas: list[dict]      = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{document_id}::{idx:04d}"
            ids.append(chunk_id)
            meta = {"document_id": document_id, "chunk_index": idx}
            if extra_metadata:
                meta.update(extra_metadata)
            metadatas.append(meta)

        logger.info(
            "Upserting %d chunks for document '%s' → collection '%s'",
            len(chunks), document_id, coll_name,
        )

        # ChromaDB calls our MiniLMEmbeddingFunction automatically
        collection.upsert(
            ids       = ids,
            documents = chunks,
            metadatas = metadatas,
        )

        return UpsertResponse(
            collection_name = coll_name,
            document_id     = document_id,
            chunks_stored   = len(chunks),
        )

    # ── Public: semantic search ───────────────────────────────

    def semantic_search(
        self,
        query:           str,
        top_k:           int = 5,
        collection_name: str = "",
        where:           dict | None = None,
    ) -> SearchResponse:
        """
        Embed `query` and return the top-k most similar chunks.

        Parameters
        ----------
        query           : Natural language query string.
        top_k           : Number of results to return.
        collection_name : Collection to search.
        where           : Optional ChromaDB metadata filter dict,
                          e.g. {"document_id": {"$eq": "doc-123"}}.
        """
        coll_name  = collection_name or self._settings.chroma_default_collection
        collection = self._get_or_create_collection(coll_name)

        doc_count = collection.count()
        if doc_count == 0:
            logger.warning("Collection '%s' is empty.", coll_name)
            return SearchResponse(query=query, results=[])

        k = min(top_k, doc_count)

        logger.debug("Searching '%s' for: %r (top_k=%d)", coll_name, query, k)

        kwargs: dict = dict(
            query_texts    = [query],
            n_results      = k,
            include        = ["documents", "metadatas", "distances"],
        )
        if where:
            kwargs["where"] = where

        raw = collection.query(**kwargs)

        results: list[SearchResult] = []
        for chunk_id, text, meta, dist in zip(
            raw["ids"][0],
            raw["documents"][0],
            raw["metadatas"][0],
            raw["distances"][0],
        ):
            # ChromaDB cosine distance ∈ [0, 2]; convert to similarity ∈ [-1, 1]
            similarity = round(1.0 - dist, 4)
            results.append(SearchResult(
                chunk_id = chunk_id,
                text     = text,
                score    = similarity,
                metadata = meta or {},
            ))

        return SearchResponse(query=query, results=results)

    # ── Public: delete ────────────────────────────────────────

    def delete_document(
        self,
        document_id:     str,
        collection_name: str = "",
    ) -> int:
        """
        Remove all chunks belonging to `document_id`.
        Returns the number of chunks deleted.
        """
        coll_name  = collection_name or self._settings.chroma_default_collection
        collection = self._get_or_create_collection(coll_name)

        existing = collection.get(where={"document_id": {"$eq": document_id}})
        ids_to_delete = existing["ids"]

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                "Deleted %d chunks for document '%s' from '%s'.",
                len(ids_to_delete), document_id, coll_name,
            )

        return len(ids_to_delete)

    # ── Public: stats ─────────────────────────────────────────

    def collection_stats(
        self, collection_name: str = ""
    ) -> CollectionStatsResponse:
        coll_name  = collection_name or self._settings.chroma_default_collection
        collection = self._get_or_create_collection(coll_name)
        all_collections = [c.name for c in self._client.list_collections()]

        return CollectionStatsResponse(
            collection_name = coll_name,
            document_count  = collection.count(),
            collections     = all_collections,
        )

    @property
    def is_ready(self) -> bool:
        return self._client is not None and self._embed_fn is not None
