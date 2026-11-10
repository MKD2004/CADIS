"""The Phase 2 retrieval pipeline (CADIS V2 §4.9, ARCHITECTURE_V2 §7).

    question
      → dense (HNSW) + BM25, unfiltered, top ``retrieve_k`` each
      → section targets named in the question, kept only in documents that
        search found (soft filter, ADR-028)
        + the same two searches limited to each target's sections
      → Reciprocal Rank Fusion (ADR-009)
      → keep chunks that are visible and current (checked in SQLite)
      → cross-encoder re-rank of the top ``rerank_candidates`` (ADR-010)
      → select ``k``: one slot reserved per section target, near-duplicate
        (overlapping) chunks skipped, optional cap per document

Every step requires ``allowed_collection_ids`` (ADR-015).
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from cadis.config import get_settings
from cadis.index.keyword_store import SqliteKeywordStore
from cadis.index.vector_store import get_vector_store
from cadis.ingest.sections import PATH_SEP
from cadis.models.embedding import embed_query
from cadis.retrieval import sections as section_routing
from cadis.retrieval.hybrid import rrf
from cadis.retrieval.rerank import rerank
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.tables import Document

MODES = ("hybrid", "dense", "keyword")
_FILTERED_K = 20          # per section-filtered list


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    section_id: str
    section_path: str
    page: int | None
    char_start: int
    char_end: int
    tokens: int
    text: str
    score: float                  # rerank score if re-ranked, else RRF score
    rrf_score: float
    target: str | None = None     # section phrase this chunk was reserved for

    @property
    def header(self) -> str:
        parts = [self.document_title] + (self.section_path.split(PATH_SEP) if self.section_path else [])
        return " › ".join(p for p in parts if p)


@dataclass
class Retrieval:
    question: str
    hits: list[RetrievedChunk]
    targets: list[section_routing.SectionTarget] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)


def _overlap(a: RetrievedChunk, b: RetrievedChunk) -> float:
    if a.document_id != b.document_id:
        return 0.0
    inter = min(a.char_end, b.char_end) - max(a.char_start, b.char_start)
    shorter = min(a.char_end - a.char_start, b.char_end - b.char_start) or 1
    return max(0, inter) / shorter


def retrieve(question: str, allowed_collection_ids: Sequence[str], *,
             document_ids: Sequence[str] | None = None, k: int | None = None,
             use_sections: bool | None = None, use_reranker: bool | None = None,
             mode: str = "hybrid") -> Retrieval:
    s = get_settings()
    k = s.rerank_k if k is None else k
    use_sections = s.section_filter if use_sections is None else use_sections
    use_reranker = s.use_reranker if use_reranker is None else use_reranker
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    allowed = list(allowed_collection_ids)
    question = (question or "").strip()
    out = Retrieval(question, [])
    if not allowed or not question or k <= 0:
        return out

    timings, t0 = out.timings_ms, time.perf_counter()

    def lap(name):
        nonlocal t0
        now = time.perf_counter()
        timings[name] = round((now - t0) * 1000, 1)
        t0 = now

    with session_scope() as db:
        store, keywords = get_vector_store(), SqliteKeywordStore()
        vector = embed_query(question) if mode != "keyword" else None
        lap("embed")

        def searches(n, section_ids=None):
            """Ranked ID lists, plus the documents they came from."""
            lists, docs = [], set()
            if mode != "keyword":
                hits = store.search(vector, allowed, n, document_ids, section_ids)
                lists.append([h.id for h in hits])
                docs.update(h.document_id for h in hits)
            if mode != "dense":
                hits = keywords.search(db, question, allowed, n, document_ids, section_ids)
                lists.append([h.id for h in hits])
                docs.update(h.document_id for h in hits)
            return lists, docs

        lists, candidate_docs = searches(s.retrieve_k)
        lap("search")

        # Sections are resolved only within documents the plain search found:
        # a named section narrows a relevant document down (ADR-028).
        if use_sections:
            out.targets = section_routing.resolve(db, question, allowed, document_ids,
                                                  candidate_documents=candidate_docs)
        lap("sections")

        target_lists: list[list[str]] = []
        for t in out.targets:
            filtered, _ = searches(_FILTERED_K, t.section_ids)
            lists.extend(filtered)
            target_lists.append(rrf_ids(filtered, s.rrf_k))
        fused = rrf(lists, s.rrf_k)
        lap("section_search")

        # Visible + current only; vectors left by interrupted jobs drop out here.
        live = repositories.current_chunks(db, [cid for cid, _ in fused], allowed)
        titles = dict(db.execute(select(Document.id, Document.title).where(
            Document.id.in_({c.document_id for c in live.values()}))).all())
        rrf_score = dict(fused)
        pool = [cid for cid, _ in fused if cid in live][:max(s.rerank_candidates, k)]
        for ranked in target_lists:                    # each target's best few always compete
            for cid in [c for c in ranked if c in live][:3]:
                if cid not in pool:
                    pool.append(cid)
        chunks = {cid: RetrievedChunk(
            cid, live[cid].document_id, titles.get(live[cid].document_id) or "", live[cid].section_id,
            live[cid].section_path, live[cid].page, live[cid].char_start, live[cid].char_end,
            live[cid].tokens, live[cid].text, rrf_score[cid], rrf_score[cid]) for cid in pool}
    lap("load")

    if use_reranker and chunks:
        scores = rerank(question, [(cid, f"{c.header}\n{c.text}") for cid, c in chunks.items()])
        for cid, score in scores.items():
            chunks[cid].score = score
        lap("rerank")

    ranked = sorted(chunks.values(), key=lambda c: (-c.score, -c.rrf_score, c.chunk_id))
    out.hits = _select(ranked, out.targets, k, s.max_per_document)
    lap("select")
    timings["total"] = round(sum(v for key, v in timings.items() if key != "total"), 1)
    return out


def rrf_ids(lists, k):
    return [cid for cid, _ in rrf(lists, k)]


def _select(ranked: list[RetrievedChunk], targets, k: int, max_per_doc: int) -> list[RetrievedChunk]:
    chosen: list[RetrievedChunk] = []
    per_doc: dict[str, int] = {}

    def ok(c):
        if c in chosen:
            return False
        if max_per_doc and per_doc.get(c.document_id, 0) >= max_per_doc:
            return False
        return all(_overlap(c, o) <= 0.5 for o in chosen)

    def take(c):
        chosen.append(c)
        per_doc[c.document_id] = per_doc.get(c.document_id, 0) + 1

    # One reserved slot per named section, so "X from A and Y from B" always
    # brings evidence from both A and B.
    for t in targets:
        if len(chosen) >= k:
            break
        ids = set(t.section_ids)
        best = next((c for c in ranked if c.section_id in ids and ok(c)), None)
        if best is not None:
            best.target = t.phrase
            take(best)
    for c in ranked:
        if len(chosen) >= k:
            break
        if ok(c):
            take(c)
    return sorted(chosen, key=lambda c: (-c.score, -c.rrf_score, c.chunk_id))
