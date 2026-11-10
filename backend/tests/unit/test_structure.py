"""Parsing (V2), cleaning and section detection (ADR-016, ADR-028)."""

import io

import pytest

from cadis.ingest.cleaning import clean_blocks
from cadis.ingest.parsers import Block, looks_like, parse_document
from cadis.ingest.sections import build_structure
from conftest import EVAL_DOCS


def structure_of(name, content, fallback="doc"):
    parsed = parse_document(name, content)
    blocks = clean_blocks(parsed.blocks, parsed.kind, parsed.pages)
    return build_structure(blocks, parsed.kind, fallback)


def paths(structure):
    return [s.path for s in structure.sections[1:]]


# ── parsers ────────────────────────────────────────────────────────────────────

def test_txt_blocks_split_on_blank_lines_and_form_feeds():
    p = parse_document("a.txt", b"Title\n\nline one\nline two\n\fPage two text")
    assert [(b.text, b.page, b.n_lines) for b in p.blocks] == [
        ("Title", 1, 1), ("line one\nline two", 1, 2), ("Page two text", 2, 1)]
    assert p.pages == 2


def test_markdown_headings_become_explicit_levels():
    p = parse_document("a.txt", b"# Report\nIntro text here.\n## Methods\nWe did things.")
    assert [(b.text, b.style_level) for b in p.blocks] == [
        ("Report", 1), ("Intro text here.", None), ("Methods", 2), ("We did things.", None)]


def test_docx_heading_styles_and_table_order():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_heading("Annual Report", 0)
    d.add_heading("Revenue", 1)
    d.add_paragraph("Revenue grew.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Q1", "$14.6M"
    d.add_heading("Costs", 1)
    d.add_paragraph("Costs fell.")
    buf = io.BytesIO()
    d.save(buf)
    p = parse_document("r.docx", buf.getvalue())
    assert [(b.text, b.style_level) for b in p.blocks] == [
        ("Annual Report", 0), ("Revenue", 1), ("Revenue grew.", None), ("Q1 | $14.6M", None),
        ("Costs", 1), ("Costs fell.", None)]
    st = build_structure(p.blocks, "docx", "r")
    assert st.title == "Annual Report" and paths(st) == ["Revenue", "Costs"]
    assert [b.text for b in st.body if st.sections[b.section].title == "Revenue"] == [
        "Revenue grew.", "Q1 | $14.6M"]


def make_pdf(pages):
    """pages: [[(text, size, bold), ...], ...] → PDF bytes with real font sizes."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    for lines in pages:
        page = doc.new_page()
        y = 72
        for text, size, bold in lines:
            page.insert_text((72, y), text, fontsize=size, fontname="hebo" if bold else "helv")
            y += size * 2.2
    return doc.tobytes()


BODY = "This paragraph is ordinary body text with enough words to count as body."


def test_pdf_headings_from_font_sizes_and_numbering():
    pdf = make_pdf([[("A Study of Things", 20, True), (BODY, 10, False),
                     ("3 Methodology", 15, True), (BODY, 10, False),
                     ("3.2 Dataset", 12, True), ("We used 1,000 records.", 10, False)],
                    [("4 Experiments", 15, True), (BODY, 10, False)]])
    st = structure_of("p.pdf", pdf)
    assert st.title == "A Study of Things"
    assert paths(st) == ["3 Methodology", "3 Methodology > 3.2 Dataset", "4 Experiments"]
    dataset = next(s for s in st.sections if s.title == "3.2 Dataset")
    assert dataset.level == 2 and dataset.page == 1
    assert st.sections[-1].page == 2


def test_looks_like_rejects_renamed_files():
    assert looks_like("pdf", b"%PDF-1.7 ...")
    assert not looks_like("pdf", b"hello")
    assert looks_like("docx", b"PK\x03\x04rest")
    assert not looks_like("txt", b"MZ\x00\x00binary")


# ── cleaning ───────────────────────────────────────────────────────────────────

def test_hyphenated_line_breaks_are_joined_and_lines_merged():
    [b] = clean_blocks([Block("The infor-\nmation was\nshared widely.", n_lines=3)], "txt")
    assert b.text == "The information was shared widely."
    assert b.n_lines == 3          # heading detection still sees the original shape


def test_list_items_keep_their_own_lines():
    [b] = clean_blocks([Block("Steps:\n- install\n- run it\n2) check")], "txt")
    assert b.text == "Steps:\n- install\n- run it\n2) check"


def test_pdf_page_numbers_and_running_headers_are_dropped():
    blocks = []
    for page in range(1, 5):
        blocks += [Block("ACME Corp Confidential", page, 9), Block(f"Body of page {page}.", page, 10),
                   Block(f"Page {page} of 4", page, 9)]
    cleaned = clean_blocks(blocks, "pdf", 4)
    assert [b.text for b in cleaned] == [f"Body of page {p}." for p in range(1, 5)]


def test_paragraph_split_by_a_page_break_is_merged():
    blocks = [Block("The contract was signed by both", 1, 10), Block("parties in May.", 2, 10)]
    assert [b.text for b in clean_blocks(blocks, "pdf", 2)] == [
        "The contract was signed by both parties in May."]


def test_txt_years_are_not_mistaken_for_page_numbers():
    assert [b.text for b in clean_blocks([Block("2024"), Block("Revenue rose.")], "txt")] == [
        "2024", "Revenue rose."]


# ── sections ───────────────────────────────────────────────────────────────────

def test_eval_document_headings():
    st = structure_of("energy.txt", (EVAL_DOCS / "energy.txt").read_bytes())
    assert st.title.startswith("Northern Grid Authority")
    assert paths(st) == ["Foreword", "Targets", "Generation", "Storage", "Extreme Weather",
                         "Emissions", "Grid Investment", "Customers", "Outlook"]
    storage = next(s for s in st.sections if s.title == "Storage")
    assert "Harlow Ridge" in st.text[storage.char_start:storage.char_end]
    assert "heatwave" not in st.text[storage.char_start:storage.char_end]


def test_numbered_sections_nest_by_their_numbers():
    text = (b"Paper Title\n\n1 Introduction\n\nWe study things.\n\n3 Methodology\n\nOverview.\n\n"
            b"3.1 Model\n\nA model.\n\n3.2 Dataset\n\nData here.\n\n4 Experiments\n\nResults.")
    st = structure_of("p.txt", text)
    assert paths(st) == ["1 Introduction", "3 Methodology", "3 Methodology > 3.1 Model",
                         "3 Methodology > 3.2 Dataset", "4 Experiments"]
    by_title = {s.title: s for s in st.sections}
    assert by_title["3.2 Dataset"].parent == by_title["3 Methodology"].ordinal
    # The parent's range covers its children, and ends before the next top section.
    meth = by_title["3 Methodology"]
    assert "Data here." in st.text[meth.char_start:meth.char_end]
    assert "Results." not in st.text[meth.char_start:meth.char_end]


def test_every_body_block_belongs_to_the_heading_above_it():
    st = structure_of("p.txt", b"Report\n\nPreamble text.\n\nCosts\n\nCosts fell.\n\nSales\n\nSales rose.")
    owner = {b.text: st.sections[b.section].path for b in st.body}
    assert owner == {"Preamble text.": "", "Costs fell.": "Costs", "Sales rose.": "Sales"}


def test_document_without_headings_is_one_root_section():
    st = structure_of("legal.txt", (EVAL_DOCS / "legal.txt").read_bytes(), "legal")
    assert st.title == "legal" and len(st.sections) == 1
    assert st.sections[0].char_start == 0 and st.sections[0].char_end == len(st.text)


def test_sentences_and_final_lines_are_not_headings():
    st = structure_of("n.txt", b"Notes\n\nShort line.\n\nA real paragraph of text.\n\nThank you")
    assert paths(st) == []          # "Short line." ends with a full stop; "Thank you" is last
    assert st.title == "Notes"


def test_offsets_point_into_the_document_text():
    st = structure_of("energy.txt", (EVAL_DOCS / "energy.txt").read_bytes())
    for b in st.body:
        assert st.text[b.char_start:b.char_end] == b.text
