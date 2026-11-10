"""Turn an uploaded file into text.

Two entry points:
  * ``extract_text`` — V1 behaviour for the legacy ``/api/extract`` endpoint:
    plain text only (.txt UTF-8, .pdf via pypdf, .docx via python-docx).
  * ``parse_document`` — V2 ingestion (Phase 1): a list of ``Block``s (one
    paragraph or heading each) with the page number and the hints needed to
    find headings — font size and bold for PDFs (PyMuPDF, ADR-016), heading
    styles for DOCX, line structure and Markdown ``#`` for TXT.
"""

import io
import re
from dataclasses import dataclass, field

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


# ── V2: structured parsing ──────────────────────────────────────────────────────

@dataclass
class Block:
    """One paragraph-like piece of a document, in reading order."""
    text: str
    page: int = 1                        # 1-based
    font_size: float | None = None       # PDF: dominant span size
    bold: bool = False                   # whole block is bold
    style_level: int | None = None       # explicit heading level (DOCX "Heading N", Markdown "#"); 0 = title
    n_lines: int = 1                     # lines in the source (TXT/PDF), before cleaning joins them


@dataclass
class ParsedDocument:
    kind: str                            # "pdf" | "docx" | "txt"
    blocks: list[Block] = field(default_factory=list)
    pages: int | None = None


def file_kind(filename: str) -> str:
    name = (filename or "").lower()
    for ext in SUPPORTED:
        if name.endswith(ext):
            return ext[1:]
    raise UnsupportedFileType(name)


def looks_like(kind: str, content: bytes) -> bool:
    """Cheap content check so a renamed file is rejected before ingestion."""
    if kind == "pdf":
        return content[:1024].lstrip().startswith(b"%PDF")
    if kind == "docx":
        return content[:4] == b"PK\x03\x04"
    if kind == "txt":
        return b"\x00" not in content[:4096]
    return False


def parse_document(filename: str, content: bytes) -> ParsedDocument:
    kind = file_kind(filename)
    if kind == "txt":
        return _parse_txt(content.decode("utf-8", errors="replace"))
    if kind == "docx":
        return _parse_docx(content)
    return _parse_pdf(content)


_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def _parse_txt(text: str) -> ParsedDocument:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    pages = text.split("\f")                       # form feed = page break
    blocks: list[Block] = []
    for page_no, page in enumerate(pages, start=1):
        for raw in re.split(r"\n\s*\n", page):
            lines = [ln.rstrip() for ln in raw.strip("\n").split("\n") if ln.strip()]
            # A Markdown heading line is its own block even without a blank line after it.
            buf: list[str] = []
            for ln in lines:
                m = _MD_HEADING.match(ln.strip())
                if m:
                    if buf:
                        blocks.append(Block("\n".join(buf), page_no, n_lines=len(buf)))
                        buf = []
                    blocks.append(Block(m.group(2), page_no, style_level=len(m.group(1))))
                else:
                    buf.append(ln)
            if buf:
                blocks.append(Block("\n".join(buf), page_no, n_lines=len(buf)))
    return ParsedDocument("txt", blocks, len(pages) if len(pages) > 1 else None)


_DOCX_HEADING = re.compile(r"^heading\s*(\d)$", re.I)


def _parse_docx(content: bytes) -> ParsedDocument:
    try:
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
    except ImportError:
        raise MissingParser("python-docx not installed. Run: pip install python-docx")
    d = docx.Document(io.BytesIO(content))
    blocks: list[Block] = []
    # Walk the body in order so tables stay where they are in the document.
    for el in d.element.body.iterchildren():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(el, d)
            text = p.text.strip()
            if not text:
                continue
            style = ((p.style.name if p.style is not None else "") or "").strip()
            level = None
            m = _DOCX_HEADING.match(style)
            if m:
                level = int(m.group(1))
            elif style.lower() == "title":
                level = 0
            runs = [r for r in p.runs if r.text.strip()]
            bold = bool(runs) and all(r.bold for r in runs)
            blocks.append(Block(text, 1, bold=bold, style_level=level))
        elif tag == "tbl":
            for row in Table(el, d).rows:
                cells: list[str] = []
                for cell in row.cells:
                    t = " ".join(cell.text.split())
                    if t and (not cells or cells[-1] != t):   # merged cells repeat
                        cells.append(t)
                if cells:
                    blocks.append(Block(" | ".join(cells), 1))
    return ParsedDocument("docx", blocks, None)


def _parse_pdf(content: bytes) -> ParsedDocument:
    try:
        import pymupdf
    except ImportError:
        raise MissingParser("PyMuPDF not installed. Run: pip install pymupdf")
    blocks: list[Block] = []
    with pymupdf.open(stream=content, filetype="pdf") as pdf:
        n_pages = pdf.page_count
        for page_no, page in enumerate(pdf, start=1):
            data = page.get_text("dict", sort=True)
            for b in data.get("blocks", []):
                if b.get("type") != 0:          # images
                    continue
                lines = []
                for ln in b.get("lines", []):
                    spans = [sp for sp in ln.get("spans", []) if sp.get("text", "").strip()]
                    if not spans:
                        continue
                    text = "".join(sp["text"] for sp in ln["spans"]).strip()
                    chars = sum(len(sp["text"]) for sp in spans)
                    size = sum(sp["size"] * len(sp["text"]) for sp in spans) / max(1, chars)
                    bold = all((sp.get("flags", 0) & 16) or "bold" in sp.get("font", "").lower()
                               for sp in spans)
                    lines.append((text, round(size, 1), bool(bold)))
                # Split a block where the font changes: a heading line glued to
                # the paragraph under it is common in PDF layouts.
                group: list[tuple[str, float, bool]] = []
                for line in lines:
                    if group and (abs(line[1] - group[-1][1]) > 0.5 or line[2] != group[-1][2]):
                        blocks.append(_pdf_block(group, page_no))
                        group = []
                    group.append(line)
                if group:
                    blocks.append(_pdf_block(group, page_no))
    return ParsedDocument("pdf", blocks, n_pages)


def _pdf_block(lines, page_no) -> Block:
    text = "\n".join(t for t, _, _ in lines)
    chars = sum(len(t) for t, _, _ in lines) or 1
    size = sum(s * len(t) for t, s, _ in lines) / chars
    return Block(text, page_no, font_size=round(size, 1), bold=all(b for _, _, b in lines),
                 n_lines=len(lines))
