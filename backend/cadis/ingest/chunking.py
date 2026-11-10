"""Cut a structured document into chunks (CADIS V2 Phase 1, ADR-028).

  * Sizes are counted in the **embedding model's tokens**, using the
    tokenizer's offset mapping, so a chunk always fits the model.
  * Chunks are built **inside one section** and never cross a heading —
    overlap included. A short section becomes one small chunk.
  * Text is cut at sentence ends; when a chunk is full, a paragraph end is
    preferred if it leaves the chunk at least 60% full. A sentence longer than
    a whole chunk is cut at word boundaries.
  * Consecutive chunks in a section overlap by up to ``overlap`` tokens of
    whole sentences, so a fact split across a cut is still found whole.

Chunk text is a slice of the document text (``text[char_start:char_end]``),
so citations and highlights can point at exact positions.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass

from cadis.ingest.sections import BodyBlock, Structure

# (text) -> [(start, end)] token character spans, no special tokens.
TokenSpans = Callable[[str], list[tuple[int, int]]]

_ABBREV = {"mr", "mrs", "ms", "dr", "prof", "inc", "ltd", "co", "corp", "st", "vs", "no",
           "fig", "al", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
           "oct", "nov", "dec", "e.g", "i.e", "etc", "approx", "dept", "est", "u.s"}
_SENT_END = re.compile(r"[.!?][\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])")
_PARA_FILL = 0.6


@dataclass
class ChunkSpec:
    section: int          # SectionNode.ordinal
    char_start: int
    char_end: int
    tokens: int
    page: int
    page_end: int


@dataclass
class _Unit:
    start: int            # absolute offsets into the document text
    end: int
    tokens: int
    para: int             # index of the body block it came from
    page: int


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for m in _SENT_END.finditer(text):
        word = re.search(r"([\w.]+)[.!?][\"'”’)\]]*\s+$", text[start:m.end()])
        if word and word.group(1).lower().rstrip(".") in _ABBREV:
            continue
        if re.search(r"\b[A-Z]\.$", text[:m.start() + 1]):      # initials: "J. Smith"
            continue
        end = m.start() + 1
        spans.append((start, end))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text.rstrip())))
    return [(a, b) for a, b in spans if b > a]


def _units_for_block(block: BodyBlock, para: int, token_spans: TokenSpans,
                     budget: int) -> list[_Unit]:
    toks = token_spans(block.text)
    units: list[_Unit] = []
    for a, b in _sentence_spans(block.text):
        inside = [(s, e) for s, e in toks if s >= a and e <= b and e > s]
        if len(inside) <= budget:
            units.append(_Unit(block.char_start + a, block.char_start + b, len(inside),
                               para, block.page))
            continue
        # Over-long sentence: windows of `budget` tokens, snapped to whole words.
        i = 0
        while i < len(inside):
            window = inside[i:i + budget]
            s, e = window[0][0], window[-1][1]
            if i + budget < len(inside):
                cut = block.text.rfind(" ", s, e + 1)
                if cut > s:
                    e = cut
                    window = [t for t in window if t[1] <= e]
            units.append(_Unit(block.char_start + s, block.char_start + e, len(window),
                               para, block.page))
            i += max(1, len(window))
    return units


def chunk_section(units: list[_Unit], section: int, budget: int,
                  overlap: int) -> list[ChunkSpec]:
    chunks: list[ChunkSpec] = []
    cur: list[_Unit] = []

    def total(us):
        return sum(u.tokens for u in us)

    def emit(us):
        chunks.append(ChunkSpec(section, us[0].start, us[-1].end, total(us),
                                us[0].page, us[-1].page))

    for u in units:
        while cur and total(cur) + u.tokens > budget:
            # Prefer a paragraph boundary if it leaves the chunk well filled.
            cut = len(cur)
            for i in range(len(cur) - 1, 0, -1):
                if cur[i].para != cur[i - 1].para and total(cur[:i]) >= _PARA_FILL * budget:
                    cut = i
                    break
            done, rest = cur[:cut], cur[cut:]
            emit(done)
            carry: list[_Unit] = []
            for prev in reversed(done[1:] if len(done) > 1 else []):
                if total(carry) + prev.tokens > overlap:
                    break
                carry.insert(0, prev)
            cur = carry + rest
            if cur and total(cur) + u.tokens > budget and carry:
                cur = rest                       # overlap would not fit; drop it
            if cur and total(cur) + u.tokens > budget and cur == rest and rest:
                emit(rest)                       # the tail alone plus u is too big
                cur = []
        cur.append(u)
    if cur:
        emit(cur)
    return chunks


def chunk_structure(structure: Structure, token_spans: TokenSpans,
                    budget_for: Callable[[int], int], overlap: int) -> list[ChunkSpec]:
    """All chunks of a document, in reading order. ``budget_for(section)``
    gives the token budget for that section (it depends on the length of its
    contextual header)."""
    by_section: dict[int, list[tuple[int, BodyBlock]]] = {}
    order: list[int] = []
    for para, block in enumerate(structure.body):
        if block.section not in by_section:
            by_section[block.section] = []
            order.append(block.section)
        by_section[block.section].append((para, block))

    # Keep reading order: a section's blocks are contiguous because headings
    # only move forward, so chunking section by section preserves order.
    chunks: list[ChunkSpec] = []
    for sec in order:
        budget = max(8, budget_for(sec))
        units: list[_Unit] = []
        for para, block in by_section[sec]:
            units.extend(_units_for_block(block, para, token_spans, budget))
        chunks.extend(chunk_section(units, sec, budget, min(overlap, budget // 3)))
    chunks.sort(key=lambda c: (c.char_start, c.char_end))
    return chunks
