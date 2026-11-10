"""/search and /query — questions over collections (Phase 2).

The collections searched are the caller's allowed collections, optionally
narrowed by ``collection_ids`` from the request (never widened, ADR-015).
"""

from fastapi import APIRouter, Depends, HTTPException

from cadis.answer import service as answering
from cadis.api.deps import get_allowed_collections
from cadis.api.schemas import QueryRequest, SearchOut, SearchRequest
from cadis.retrieval.retrieve import retrieve

router = APIRouter(tags=["query"])


def _scope(requested: list[str] | None, allowed: list[str]) -> list[str]:
    if requested is None:
        return allowed
    unknown = set(requested) - set(allowed)
    if unknown:
        raise HTTPException(404, "Collection not found")
    return [c for c in allowed if c in set(requested)]


@router.post("/search", response_model=SearchOut)
def search(body: SearchRequest, allowed: list[str] = Depends(get_allowed_collections)):
    """Retrieval only: the chunks an answer would be built from, with scores,
    sections and the section names recognised in the question."""
    result = retrieve(body.question, _scope(body.collection_ids, allowed),
                      document_ids=body.document_ids, k=body.k)
    return {
        "question": result.question,
        "hits": [{"chunk_id": h.chunk_id, "document_id": h.document_id,
                  "document_title": h.document_title, "section_path": h.section_path,
                  "page": h.page, "char_start": h.char_start, "char_end": h.char_end,
                  "text": h.text, "score": round(h.score, 4), "target": h.target}
                 for h in result.hits],
        "sections": [{"phrase": t.phrase, "titles": t.titles, "sections": len(t.matched_ids)}
                     for t in result.targets],
        "timings_ms": result.timings_ms,
    }


@router.post("/query")
def query(body: QueryRequest, allowed: list[str] = Depends(get_allowed_collections)):
    """Answer with a citation (extractive mode: an exact span of a document)."""
    return answering.answer(body.question, _scope(body.collection_ids, allowed),
                            document_ids=body.document_ids)
