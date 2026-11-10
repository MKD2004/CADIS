"""Find headings and build a document's section tree (DECISIONS ADR-028).

Heading signals, strongest first:
  1. explicit levels — DOCX "Heading N" / "Title" styles, Markdown ``#``;
  2. numbering — ``3.2 Dataset`` is level 2 (any format);
  3. PDF fonts — larger than the body text, or bold at body size;
  4. TXT/DOCX layout — a short single line, without closing punctuation,
     followed by more text.

The first heading-like block of a document becomes its title (the root
section) unless it is numbered. Text before the first heading belongs to the
root. Every non-heading block belongs to exactly one section — the most
recent heading above it — so chunks built per section never mix topics.

Detection is heuristic. A missed heading only makes a section bigger; a false
heading only makes one smaller. Neither loses text, and retrieval treats
sections as a soft filter, so a wrong guess never hides an answer.
"""

import re
from dataclasses import dataclass, field
from statistics import median

from cadis.ingest.parsers import Block

PATH_SEP = " > "
BLOCK_SEP = "\n\n"

_NUMBERED = re.compile(r"^((?:\d{1,3}\.){0,4}\d{1,3})\.?\s+(\S.*)$")
_CLOSING_PUNCT = re.compile(r"[.,;:!?]$")
_MAX_LEVEL = 6


@dataclass
class SectionNode:
    ordinal: int
    title: str
    level: int                    # 0 = root (whole document)
    parent: int | None            # parent's ordinal
    titles: list[str]             # path parts below the root
    page: int | None
    char_start: int
    char_end: int = 0

    @property
    def path(self) -> str:
        return PATH_SEP.join(self.titles)


@dataclass
class BodyBlock:
    text: str
    page: int
    char_start: int
    char_end: int
    section: int                  # SectionNode.ordinal


@dataclass
class Structure:
    text: str                     # cleaned document text; all offsets point here
    title: str
    sections: list[SectionNode] = field(default_factory=list)
    body: list[BodyBlock] = field(default_factory=list)


def _words(text: str) -> int:
    return len(text.split())


def _numbering_level(text: str) -> int | None:
    m = _NUMBERED.match(text)
    if not m:
        return None
    rest = m.group(2)
    if not (rest[:1].isupper() or rest[:1].isdigit()):
        return None
    return min(_MAX_LEVEL, m.group(1).count(".") + 1)


class _Detector:
    def __init__(self, blocks: list[Block], kind: str):
        self.blocks = blocks
        self.kind = kind
        self.body_size = self._body_font_size() if kind == "pdf" else None
        self.size_levels = self._pdf_size_levels() if kind == "pdf" else {}

    def _body_font_size(self) -> float | None:
        sizes = []
        for b in self.blocks:
            if b.font_size and _words(b.text) >= 8:
                sizes.extend([b.font_size] * min(len(b.text), 2000))
        return median(sizes) if sizes else None

    def _short(self, b: Block, max_words: int) -> bool:
        t = b.text.strip()
        return 0 < _words(t) <= max_words and len(t) <= 150 and "\n" not in t

    def _pdf_candidate(self, b: Block) -> bool:
        if not self.body_size or not b.font_size or not self._short(b, 15):
            return False
        if re.search(r"[.,;:]$", b.text.strip()):
            return False
        return b.font_size >= self.body_size * 1.15 or (b.bold and b.font_size >= self.body_size * 0.95)

    def _pdf_size_levels(self) -> dict[float, int]:
        bigger = sorted({b.font_size for b in self.blocks
                         if self._pdf_candidate(b) and b.font_size >= self.body_size * 1.15},
                        reverse=True)
        return {size: i + 1 for i, size in enumerate(bigger[:_MAX_LEVEL - 1])}

    def level(self, i: int) -> int | None:
        """Heading level of block i, or None if it is body text."""
        b = self.blocks[i]
        text = b.text.strip()
        if b.style_level is not None:
            return b.style_level
        numbered = _numbering_level(text)
        if self.kind == "pdf":
            if not self._pdf_candidate(b):
                return None
            if numbered:
                return numbered
            if b.font_size in self.size_levels:
                return self.size_levels[b.font_size]
            return min(_MAX_LEVEL, len(self.size_levels) + 1)     # bold at body size
        # TXT and DOCX: a short single line, no closing punctuation, with text after it.
        if i == len(self.blocks) - 1 or b.n_lines != 1 or not self._short(b, 12):
            return None
        if _CLOSING_PUNCT.search(text):
            return None
        if not (text[:1].isupper() or text[:1].isdigit()):
            return None
        if self.kind == "docx" and not b.bold and numbered is None:
            return None                     # DOCX headings without a style must at least be bold
        return numbered or 1


def build_structure(blocks: list[Block], kind: str, fallback_title: str) -> Structure:
    detector = _Detector(blocks, kind)
    levels = [detector.level(i) for i in range(len(blocks))]

    # Document title: an explicit Title style, or the first block when it is an
    # un-numbered heading (and, for PDFs, uses the largest heading font).
    title_index = None
    for i, lvl in enumerate(levels):
        if lvl == 0:
            title_index = i
            break
    if title_index is None and blocks and levels[0] is not None \
            and _numbering_level(blocks[0].text.strip()) is None:
        if kind != "pdf" or blocks[0].font_size == max(
                (b.font_size or 0) for b, l in zip(blocks, levels) if l is not None):
            title_index = 0
    for i, lvl in enumerate(levels):            # stray "Title" styles become level-1 headings
        if lvl == 0 and i != title_index:
            levels[i] = 1

    title = blocks[title_index].text.strip() if title_index is not None else fallback_title

    # Assemble the text and record every block's offsets.
    parts, offsets, pos = [], [], 0
    for b in blocks:
        if parts:
            pos += len(BLOCK_SEP)
        offsets.append((pos, pos + len(b.text)))
        parts.append(b.text)
        pos += len(b.text)
    text = BLOCK_SEP.join(parts)

    root = SectionNode(0, title, 0, None, [], blocks[0].page if blocks else None, 0, len(text))
    sections = [root]
    stack = [root]
    body: list[BodyBlock] = []

    for i, (b, lvl) in enumerate(zip(blocks, levels)):
        start, end = offsets[i]
        if i == title_index:
            continue
        if lvl is not None and lvl > 0:
            while stack[-1].level >= lvl:
                stack[-1].char_end = _end_before(start)
                stack.pop()
            parent = stack[-1]
            node = SectionNode(len(sections), b.text.strip(), lvl, parent.ordinal,
                               parent.titles + [b.text.strip()], b.page, start)
            sections.append(node)
            stack.append(node)
            continue
        body.append(BodyBlock(b.text, b.page, start, end, stack[-1].ordinal))

    for node in stack[1:]:
        node.char_end = len(text)
    root.char_end = len(text)
    return Structure(text, title, sections, body)


def _end_before(start: int) -> int:
    """A section ends just before the separator that precedes the next heading."""
    return max(0, start - len(BLOCK_SEP))
