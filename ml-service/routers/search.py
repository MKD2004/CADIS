"""
routers/search.py
=================
ChromaDB semantic search and collection management endpoints.

POST /api/v1/search/query       — semantic similarity search + RoBERTa QA
POST /api/v1/search/upsert      — manually store text chunks
GET  /api/v1/search/stats       — collection stats
DELETE /api/v1/search/{doc_id}  — remove a document's chunks
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional

from core.logging import get_logger
from models.schemas import (
    CollectionStatsResponse,
    SearchRequest,
    SearchResponse,
    UpsertRequest,
    UpsertResponse,
)
from services.vector_store import VectorStoreService

from services.qa import QAService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["Vector Search"])


# ─────────────────────────────────────────────────────────────
#  Dependency
# ─────────────────────────────────────────────────────────────

def get_vector_store() -> VectorStoreService:
    svc = VectorStoreService.get_instance()
    if not svc.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not ready. Check server logs.",
        )
    return svc


# ─────────────────────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────────────────────

@router.post(
    "/query",
    # response_model  = SearchResponse, # Commented out so FastAPI allows our new "answer" field
    status_code     = status.HTTP_200_OK,
    summary         = "Semantic similarity search + Neural QA Extraction",
    description     = (
        "Embeds `query` with all-MiniLM-L6-v2, retrieves the top-k "
        "most similar chunks from ChromaDB, and passes them to RoBERTa "
        "to extract a precise, exact answer."
    ),
)
async def semantic_search(
    request:      SearchRequest,
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    logger.info(
        "Search query in '%s': %r (top_k=%d)",
        request.collection_name, request.query, request.top_k,
    )
    try:
        # 1. Get the raw semantic chunks from ChromaDB
        search_results = vector_store.semantic_search(
            query           = request.query,
            top_k           = request.top_k,
            collection_name = request.collection_name,
            where           = request.where,
        )

        # Safely handle the results whether they are a Pydantic object or a dict
        raw_results = search_results.results if hasattr(search_results, 'results') else search_results

        if not raw_results:
            return {
                "answer": "I could not find a definitive answer in the document.",
                "context_used": "",
                "results": [],
                "latency_ms": {"minilm": 0, "roberta": 0},
            }

        context_texts = []
        for item in raw_results:
            if isinstance(item, dict) and 'text' in item:
                context_texts.append(item['text'])
            elif hasattr(item, 'text'):
                context_texts.append(item.text)
            else:
                context_texts.append(str(item))

        context_text = " ".join(context_texts)

        qa_result = QAService.get_instance().answer_question(
            question=request.query, context=context_text,
        )

        return {
            "answer": qa_result["answer"],
            "context_used": context_text,
            "results": raw_results,
            "latency_ms": {
                "minilm": search_results.inference_ms,
                "roberta": qa_result["inference_ms"],
            },
        }

    except Exception as exc:
        logger.exception("Semantic search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc


@router.get(
    "/samples",
    status_code     = status.HTTP_200_OK,
    summary         = "List pre-loaded sample documents",
)
async def list_samples(
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    coll = vector_store._get_or_create_collection(
        vector_store._settings.chroma_default_collection
    )
    results = coll.get(where={"source": {"$eq": "sample"}}, include=["metadatas"])

    seen: dict[str, dict] = {}
    for meta in results["metadatas"]:
        doc_id = meta.get("document_id", "")
        if doc_id and doc_id not in seen:
            seen[doc_id] = {
                "document_id": doc_id,
                "title": meta.get("title", ""),
                "type": meta.get("type", ""),
                "source": "sample",
            }
    return list(seen.values())


@router.post(
    "/upsert",
    response_model  = UpsertResponse,
    status_code     = status.HTTP_201_CREATED,
    summary         = "Manually upsert text chunks into a ChromaDB collection",
    description     = (
        "Use this endpoint to store arbitrary text chunks without going "
        "through the /process-pdf pipeline. Useful for plain-text documents."
    ),
)
async def upsert_chunks(
    request:      UpsertRequest,
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> UpsertResponse:
    logger.info(
        "Upsert request: doc='%s', %d chunks → '%s'",
        request.document_id, len(request.chunks), request.collection_name,
    )
    try:
        return vector_store.upsert_document(
            document_id     = request.document_id,
            chunks          = request.chunks,
            collection_name = request.collection_name,
            extra_metadata  = request.metadata,
        )
    except Exception as exc:
        logger.exception("Upsert failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upsert failed: {exc}",
        ) from exc


@router.get(
    "/stats",
    response_model  = CollectionStatsResponse,
    status_code     = status.HTTP_200_OK,
    summary         = "Get ChromaDB collection statistics",
)
async def collection_stats(
    collection_name: str               = "cadis_documents",
    vector_store:    VectorStoreService = Depends(get_vector_store),
) -> CollectionStatsResponse:
    return vector_store.collection_stats(collection_name)


@router.delete(
    "/documents/{document_id}",
    status_code = status.HTTP_200_OK,
    summary     = "Delete all vector chunks for a document",
)
async def delete_document_vectors(
    document_id:     str,
    collection_name: str               = "cadis_documents",
    vector_store:    VectorStoreService = Depends(get_vector_store),
) -> dict:
    deleted = vector_store.delete_document(document_id, collection_name)
    return {"document_id": document_id, "chunks_deleted": deleted}