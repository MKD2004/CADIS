import io

import pytest

from cadis.ingest.parsers import UnsupportedFileType, extract_text
from fakes import make_pdf


def test_txt_is_decoded_and_stripped():
    assert extract_text("Notes.TXT", b"  hello world \n") == "hello world"


def test_txt_with_invalid_utf8_does_not_crash():
    assert extract_text("a.txt", b"caf\xe9") == "caf�"


def test_docx_paragraphs_are_joined_with_newlines():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Meridian Corporation signed.")
    d.add_paragraph("Payment is monthly.")
    buf = io.BytesIO()
    d.save(buf)
    assert extract_text("contract.docx", buf.getvalue()) == "Meridian Corporation signed.\nPayment is monthly."


def test_pdf_text_is_extracted():
    assert extract_text("report.pdf", make_pdf("Revenue grew in 2025.")) == "Revenue grew in 2025."


def test_unsupported_type_is_rejected():
    with pytest.raises(UnsupportedFileType, match="Use .txt, .pdf, or .docx"):
        extract_text("virus.exe", b"MZ")


def test_empty_file_gives_empty_text():
    assert extract_text("blank.txt", b"   \n ") == ""
