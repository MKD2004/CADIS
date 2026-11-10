"""Clean parsed blocks before sections and chunks are built.

  * drop running headers/footers that repeat on many pages (PDF);
  * drop blocks that are only a page number ("12", "Page 3 of 10", "- 4 -"; PDF);
  * join words broken by a hyphen at a line end ("infor-\\nmation");
  * join line breaks inside a paragraph, keeping list items on their own lines;
  * merge a paragraph that a page break split in two (PDF).

Cleaning never reorders blocks and never changes heading hints, so section
detection sees the same structure the parser found.
"""

import re
from collections import Counter
from dataclasses import replace

from cadis.ingest.parsers import Block

_PAGE_NUMBER = re.compile(
    r"^\s*(?:page\s*)?[-–—]?\s*\d{1,4}\s*[-–—]?\s*(?:(?:of|/)\s*\d{1,4})?\s*$", re.I)
_HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-z])")
_LIST_ITEM = re.compile(r"^\s*(?:[-*•▪◦–]|\(?\d{1,3}[.)]|\(?[a-z][.)])\s+")
_SENTENCE_END = re.compile(r"[.!?:;\"'”’)\]]\s*$")


def _normalise(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def _repeated_margins(blocks: list[Block], pages: int) -> set[str]:
    """Normalised texts that appear as the first or last block of many pages."""
    if pages < 3:
        return set()
    by_page: dict[int, list[Block]] = {}
    for b in blocks:
        by_page.setdefault(b.page, []).append(b)
    seen: Counter[str] = Counter()
    for page_blocks in by_page.values():
        edge = {_normalise(page_blocks[0].text), _normalise(page_blocks[-1].text)}
        for n in edge:
            if len(n) <= 120:
                seen[n] += 1
    threshold = max(3, (pages + 1) // 2)
    return {n for n, c in seen.items() if c >= threshold}


def _join_lines(text: str) -> str:
    text = _HYPHEN_BREAK.sub(r"\1", text)
    out: list[str] = []
    for line in text.split("\n"):
        line = " ".join(line.split())
        if not line:
            continue
        if out and not _LIST_ITEM.match(line):
            out[-1] = out[-1] + " " + line
        else:
            out.append(line)
    return "\n".join(out)


def clean_blocks(blocks: list[Block], kind: str, pages: int | None = None) -> list[Block]:
    pages = pages or max((b.page for b in blocks), default=1)
    margins = _repeated_margins(blocks, pages) if kind == "pdf" else set()

    cleaned: list[Block] = []
    for b in blocks:
        if kind == "pdf" and _PAGE_NUMBER.match(b.text):
            continue
        if margins and _normalise(b.text) in margins:
            continue
        text = _join_lines(b.text)
        if not text:
            continue
        cleaned.append(replace(b, text=text))

    if kind == "pdf":
        cleaned = _merge_page_splits(cleaned)
    return cleaned


def _merge_page_splits(blocks: list[Block]) -> list[Block]:
    """A body paragraph that ends without punctuation on one page and continues
    in lower case on the next page is one paragraph."""
    out: list[Block] = []
    for b in blocks:
        prev = out[-1] if out else None
        if (prev is not None and b.page == prev.page + 1
                and prev.style_level is None and b.style_level is None
                and prev.font_size == b.font_size and prev.bold == b.bold
                and not _SENTENCE_END.search(prev.text) and b.text[:1].islower()):
            out[-1] = replace(prev, text=prev.text + " " + b.text, n_lines=prev.n_lines + b.n_lines)
            continue
        out.append(b)
    return out
