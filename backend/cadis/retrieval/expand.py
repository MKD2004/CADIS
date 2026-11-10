"""Small-to-big: turn the retrieved chunks into the contexts an answer model reads.

Search works best on small chunks; answering works best with some text around
them. For each retrieved chunk we add up to ``neighbours`` chunks before and
after it **in the same section** (never across a heading), and when a chunk
belongs to a section the question named and that section is small, the whole
section. Overlapping and touching spans of one document are merged, and the
text is cut from the stored document text, so offsets stay exact.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import func, select

from cadis.config import get_settings
from cadis.retrieval.retrieve import Retrieval
from cadis.storage.db import session_scope
from cadis.storage.tables import Chunk, Document, DocumentText


@dataclass
class Context:
    document_id: str
    document_title: str
    char_start: int
    char_end: int
    text: str
    chunk_ids: list[str] = field(default_factory=list)   # retrieved chunks inside it
    page: int | None = None
    best_rank: int = 0                                   # rank of its best retrieved chunk


def expand(result: Retrieval, neighbours: int | None = None,
           whole_section_max_tokens: int | None = None) -> list[Context]:
    s = get_settings()
    neighbours = s.expand_neighbours if neighbours is None else neighbours
    whole_max = s.section_whole_max_tokens if whole_section_max_tokens is None else whole_section_max_tokens
    if not result.hits:
        return []
    targeted = {sid for t in result.targets for sid in t.matched_ids}

    spans: dict[str, list[list]] = defaultdict(list)     # doc -> [[start, end, rank, chunk_ids, page]]
    with session_scope() as db:
        versions = dict(db.execute(select(Document.id, Document.current_version).where(
            Document.id.in_({h.document_id for h in result.hits}))).all())
        for rank, hit in enumerate(result.hits):
            version = versions.get(hit.document_id)
            if version is None:
                continue
            row = db.get(Chunk, hit.chunk_id)
            if row is None:
                continue
            start, end = hit.char_start, hit.char_end
            same_section = (Chunk.document_id == hit.document_id, Chunk.version == version,
                            Chunk.section_id == hit.section_id)
            if hit.section_id in targeted:
                total, lo, hi = db.execute(select(func.sum(Chunk.tokens), func.min(Chunk.char_start),
                                                  func.max(Chunk.char_end)).where(*same_section)).one()
                if total is not None and total <= whole_max:
                    start, end = min(start, lo), max(end, hi)
            if neighbours > 0:
                lo, hi = db.execute(select(func.min(Chunk.char_start), func.max(Chunk.char_end)).where(
                    *same_section, Chunk.ordinal.between(row.ordinal - neighbours,
                                                         row.ordinal + neighbours))).one()
                if lo is not None:
                    start, end = min(start, lo), max(end, hi)
            spans[hit.document_id].append([start, end, rank, [hit.chunk_id], hit.page])

        contexts: list[Context] = []
        for doc_id, items in spans.items():
            text = db.scalar(select(DocumentText.text).where(
                DocumentText.document_id == doc_id, DocumentText.version == versions[doc_id]))
            if text is None:
                continue
            items.sort()
            merged = [items[0]]
            for it in items[1:]:
                cur = merged[-1]
                if it[0] <= cur[1] + 2:                  # overlapping or touching
                    cur[1] = max(cur[1], it[1])
                    cur[2] = min(cur[2], it[2])
                    cur[3] += it[3]
                    cur[4] = cur[4] if cur[4] is not None else it[4]
                else:
                    merged.append(it)
            title = next(h.document_title for h in result.hits if h.document_id == doc_id)
            for start, end, rank, ids, page in merged:
                contexts.append(Context(doc_id, title, start, end, text[start:end], ids, page, rank))
    contexts.sort(key=lambda c: c.best_rank)
    return contexts
