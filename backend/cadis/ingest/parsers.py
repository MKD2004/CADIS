"""Turn an uploaded file into plain text.

V1 behaviour: .txt (UTF-8), .pdf (pypdf, text only) and .docx (python-docx).
Phase 1 replaces the PDF path with PyMuPDF and returns pages + headings
(DECISIONS ADR-016).
"""

import io

SUPPORTED = (".txt", ".pdf", ".docx")


class UnsupportedFileType(ValueError):
    def __init__(self, name: str):
        super().__init__(f"Unsupported file type: {name}. Use .txt, .pdf, or .docx")


class MissingParser(RuntimeError):
    """A parser library is not installed."""


def extract_text(filename: str, content: bytes) -> str:
    """Return the file's text, stripped. May return an empty string."""
    name = (filename or "").lower()

    if name.endswith(".txt"):
        text = content.decode("utf-8", errors="replace")

    elif name.endswith(".pdf"):
        try:
            import pypdf
        except ImportError:
            raise MissingParser("pypdf not installed. Run: pip install pypdf")
        reader = pypdf.PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

    elif name.endswith(".docx"):
        try:
            import docx
        except ImportError:
            raise MissingParser("python-docx not installed. Run: pip install python-docx")
        doc = docx.Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)

    else:
        raise UnsupportedFileType(name)

    return text.strip()
