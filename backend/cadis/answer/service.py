"""Answer a question over a collection (Phase 2: extractive mode).

retrieve → expand (small-to-big) → extractive span over the contexts. The
response already has the Phase 3 shape (ARCHITECTURE_V2 §9): one claim whose
citation is the exact span in the document, so the frontend can be built
against it now and the generated mode slots in later.
"""

import time
from collections.abc import Sequence

from cadis.answer.extractive import answer_contexts
from cadis.models import registry
from cadis.retrieval.expand import expand
from cadis.retrieval.retrieve import retrieve


def answer(question: str, allowed_collection_ids: Sequence[str],
           document_ids: Sequence[str] | None = None) -> dict:
    t0 = time.perf_counter()
    result = retrieve(question, allowed_collection_ids, document_ids=document_ids)
    contexts = expand(result)
    t1 = time.perf_counter()
    tokenizer, model = registry.get_qa_pipe()
    span = answer_contexts(question, [c.text for c in contexts], tokenizer, model)
    t2 = time.perf_counter()

    timings = dict(result.timings_ms)
    timings["expand"] = round((t1 - t0) * 1000 - result.timings_ms.get("total", 0), 1)
    timings["answer"] = round((t2 - t1) * 1000, 1)
    used = [h.chunk_id for h in result.hits]
    if not span["answer"]:
        return {"status": "not_in_documents", "mode": "extractive", "answer_text": "",
                "claims": [], "used_chunks": used, "timings_ms": timings,
                "sections": [t.phrase for t in result.targets]}

    ctx = contexts[span["context"]]
    start, end = ctx.char_start + span["start"], ctx.char_start + span["end"]
    cited = next((h for h in result.hits if h.document_id == ctx.document_id
                  and h.char_start <= start and end <= h.char_end), None)
    citation = {
        "document_id": ctx.document_id, "document_title": ctx.document_title,
        "chunk_id": cited.chunk_id if cited else (ctx.chunk_ids[0] if ctx.chunk_ids else None),
        "section_path": cited.section_path if cited else None,
        "page": cited.page if cited else ctx.page,
        "quote": span["answer"], "char_start": start, "char_end": end,
    }
    return {
        "status": "answered", "mode": "extractive", "answer_text": span["answer"],
        "claims": [{"text": span["answer"], "citations": [citation],
                    "checks": {"quote_found": True, "confidence": span["confidence"]}}],
        "used_chunks": used, "timings_ms": timings,
        "sections": [t.phrase for t in result.targets],
    }
