"""Section-aware chunking (CADIS V2 Phase 1, ADR-028)."""

import re

from cadis.ingest.chunking import chunk_structure
from cadis.ingest.cleaning import clean_blocks
from cadis.ingest.parsers import parse_document
from cadis.ingest.pipeline import build_rows, contextual_header, token_spans_for
from cadis.ingest.sections import build_structure
from conftest import EVAL_DOCS
from fakes import FakeTokenizer

SPANS = token_spans_for(FakeTokenizer())


def structure_of(text: str, name="doc.txt"):
    p = parse_document(name, text.encode())
    return build_structure(clean_blocks(p.blocks, p.kind, p.pages), p.kind, "doc")


def sentences(n, prefix="Fact"):
    return " ".join(f"{prefix} number {i} is stated here." for i in range(n))


def chunks_of(st, budget=40, overlap=8):
    return chunk_structure(st, SPANS, lambda _: budget, overlap)


def test_chunks_never_cross_a_heading():
    st = structure_of(f"Report\n\nCosts\n\n{sentences(30, 'Cost')}\n\nSales\n\n{sentences(30, 'Sale')}")
    chunks = chunks_of(st)
    for c in chunks:
        sec = st.sections[c.section]
        assert sec.char_start <= c.char_start and c.char_end <= sec.char_end
        text = st.text[c.char_start:c.char_end]
        assert not ("Cost" in text and "Sale" in text)
        assert "\n\nSales" not in text and "\n\nCosts" not in text


def test_every_body_sentence_is_in_some_chunk():
    st = structure_of((EVAL_DOCS / "supply.txt").read_text(encoding="utf-8"), "supply.txt")
    chunks = chunks_of(st, budget=60, overlap=10)
    covered = [(c.char_start, c.char_end) for c in chunks]
    for b in st.body:
        for m in re.finditer(r"\S+", b.text):
            a = b.char_start + m.start()
            assert any(s <= a < e for s, e in covered), f"not covered: {m.group()!r}"


def test_chunks_fit_the_budget():
    st = structure_of((EVAL_DOCS / "energy.txt").read_text(encoding="utf-8"), "energy.txt")
    for budget in (24, 50, 120):
        for c in chunks_of(st, budget=budget, overlap=6):
            assert len(SPANS(st.text[c.char_start:c.char_end])) <= budget


def test_consecutive_chunks_in_a_section_overlap():
    st = structure_of(f"Report\n\nCosts\n\n{sentences(40)}")
    chunks = chunks_of(st, budget=40, overlap=10)
    assert len(chunks) > 2
    for a, b in zip(chunks, chunks[1:]):
        assert b.char_start < a.char_end       # shared sentence(s)


def test_short_section_is_one_small_chunk():
    st = structure_of(f"Report\n\nTiny\n\nOne line here.\n\nBig\n\n{sentences(40)}")
    tiny = [c for c in chunks_of(st) if st.sections[c.section].title == "Tiny"]
    assert len(tiny) == 1 and st.text[tiny[0].char_start:tiny[0].char_end] == "One line here."


def test_overlong_sentence_is_cut_at_words():
    long = "word " * 200 + "end."
    st = structure_of(f"Report\n\nBody\n\n{long}")
    chunks = chunks_of(st, budget=30, overlap=5)
    assert len(chunks) >= 7
    for c in chunks:
        text = st.text[c.char_start:c.char_end]
        assert len(SPANS(text)) <= 30
        assert not text.startswith(" ") and not text.endswith(" ")


def test_abbreviations_do_not_end_sentences():
    st = structure_of("Report\n\nBody\n\nDr. Lucia Romero led it. Halden Therapeutics Inc. paid.")
    chunks = chunks_of(st, budget=7, overlap=0)
    assert any(st.text[c.char_start:c.char_end].startswith("Dr. Lucia") for c in chunks)


def test_rows_are_deterministic_and_linked():
    st = structure_of((EVAL_DOCS / "trial2.txt").read_text(encoding="utf-8"), "trial2.txt")
    a = build_rows("doc-1", "col-1", 1, st, SPANS, 256)
    b = build_rows("doc-1", "col-1", 1, st, SPANS, 256)
    assert a == b
    sections, chunks, texts = a
    assert len({c["id"] for c in chunks}) == len(chunks)
    assert [c["prev_id"] for c in chunks[1:]] == [c["id"] for c in chunks[:-1]]
    assert all(c["text"] == st.text[c["char_start"]:c["char_end"]] for c in chunks)
    # A new version gets new IDs, so it never overwrites the live version.
    _, chunks_v2, _ = build_rows("doc-1", "col-1", 2, st, SPANS, 256)
    assert not {c["id"] for c in chunks} & {c["id"] for c in chunks_v2}
    # Each chunk is embedded with its contextual header, within the model limit.
    safety = next(c for c in chunks if c["section_path"] == "Safety")
    text = texts[chunks.index(safety)]
    assert text.startswith("Oral Drug RX-210") and " › Safety\n" in text
    assert all(len(SPANS(t)) + 2 <= 256 for t in texts)


def test_header_budget_shrinks_chunks_for_small_models():
    st = structure_of((EVAL_DOCS / "energy.txt").read_text(encoding="utf-8"), "energy.txt")
    _, chunks, texts = build_rows("d", "c", 1, st, SPANS, 64)
    assert all(len(SPANS(t)) + 2 <= 64 for t in texts)


def test_long_headers_keep_title_and_innermost_section():
    h = contextual_header("Annual Report", ["Part One", "Chapter Two", "Section Three"], SPANS, 8)
    assert h == "Annual Report › … › Section Three"
