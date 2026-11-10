"""The ingest job: parse → clean → sections → chunks → SQLite + FTS5 → vectors.

Idempotency (DECISIONS ADR-014). A job may run more than once (retries,
lease recovery after a crash), so:
  * the version being built is always ``current_version + 1`` — it only
    changes when the job succeeds, so a re-run rebuilds the same version;
  * section and chunk IDs are ``sha1(document_id : version : …)``, so a
    re-run writes the same IDs (upserts overwrite, never duplicate);
  * the target version is cleared before it is written, so leftovers of a
    half-finished attempt cannot survive;
  * write order: text + sections + chunks (+ FTS5 by trigger, one
    transaction) → vectors → flip ``current_version`` → delete old versions
    → job COMPLETED (done by the worker, last).
Searches only see ``current_version``, so a crash at any step never shows
half-written data.
"""

import hashlib
import logging
from pathlib import PurePath

from cadis.config import get_settings
from cadis.index.vector_store import VectorRecord, get_vector_store
from cadis.ingest.chunking import chunk_structure
from cadis.ingest.cleaning import clean_blocks
from cadis.ingest.parsers import MissingParser, UnsupportedFileType, parse_document
from cadis.ingest.sections import Structure, build_structure
from cadis.jobs.states import PermanentJobError
from cadis.jobs.worker import JobContext, JobHandler
from cadis.models import registry
from cadis.storage import repositories
from cadis.storage.db import session_scope
from cadis.storage.files import FileStore
from cadis.storage.tables import Document, DocumentStatus

log = logging.getLogger("cadis.ingest")

HEADER_SEP = " › "
INGEST = "ingest"


def section_id(document_id: str, version: int, ordinal: int) -> str:
    return hashlib.sha1(f"{document_id}:{version}:s:{ordinal}".encode()).hexdigest()


def chunk_id(document_id: str, version: int, ordinal: int) -> str:
    return hashlib.sha1(f"{document_id}:{version}:{ordinal}".encode()).hexdigest()


def token_spans_for(tokenizer):
    def spans(text: str) -> list[tuple[int, int]]:
        enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True,
                        truncation=False, verbose=False)
        return [(a, b) for a, b in enc["offset_mapping"] if b > a]
    return spans


def contextual_header(title: str, titles: list[str], token_spans, max_tokens: int) -> str:
    """"Document › Section › Subsection" — added before embedding so a chunk
    that says "the Client" still carries which document and section it is in.
    Long headers keep the document title and the innermost section."""
    parts = [title] + titles
    header = HEADER_SEP.join(p for p in parts if p)
    if len(token_spans(header)) > max_tokens and len(parts) > 2:
        header = HEADER_SEP.join(p for p in (parts[0], "…", parts[-1]) if p)
    spans = token_spans(header)
    if len(spans) > max_tokens:
        header = header[:spans[max_tokens - 1][1]] + "…"
    return header


def embed_text(header: str, text: str) -> str:
    return f"{header}\n{text}" if header else text


def build_rows(document_id: str, collection_id: str, version: int, structure: Structure,
               token_spans, max_seq_length: int):
    """Sections, chunks and the header used to embed each chunk."""
    s = get_settings()
    headers = {sec.ordinal: contextual_header(structure.title, sec.titles, token_spans,
                                              s.chunk_header_max_tokens)
               for sec in structure.sections}
    header_tokens = {o: len(token_spans(h)) for o, h in headers.items()}

    def budget_for(ordinal: int) -> int:
        # [CLS]/[SEP] + header + newline + a small margin for tokenizer
        # differences at the seams must all fit the embedding model.
        return min(s.chunk_tokens, max_seq_length - 2 - header_tokens[ordinal] - 4)

    if min(budget_for(o) for o in headers) < 32:
        raise PermanentJobError(
            f"CADIS_CHUNK_HEADER_MAX_TOKENS={s.chunk_header_max_tokens} leaves no room for text "
            f"in a {max_seq_length}-token embedding model")

    specs = chunk_structure(structure, token_spans, budget_for, s.chunk_overlap_tokens)

    sections = [{
        "id": section_id(document_id, version, n.ordinal), "document_id": document_id,
        "collection_id": collection_id, "version": version,
        "parent_id": None if n.parent is None else section_id(document_id, version, n.parent),
        "title": n.title[:500], "path": n.path, "level": n.level, "ordinal": n.ordinal,
        "page": n.page, "char_start": n.char_start, "char_end": n.char_end,
    } for n in structure.sections]
    by_ordinal = {n.ordinal: n for n in structure.sections}

    ids = [chunk_id(document_id, version, i) for i in range(len(specs))]
    chunks, embed_texts = [], []
    for i, c in enumerate(specs):
        text = structure.text[c.char_start:c.char_end]
        chunks.append({
            "id": ids[i], "document_id": document_id, "collection_id": collection_id,
            "version": version, "ordinal": i, "page": c.page, "page_end": c.page_end,
            "section_id": section_id(document_id, version, c.section),
            "section_path": by_ordinal[c.section].path,
            "char_start": c.char_start, "char_end": c.char_end, "tokens": c.tokens, "text": text,
            "prev_id": ids[i - 1] if i else None,
            "next_id": ids[i + 1] if i + 1 < len(ids) else None,
        })
        embed_texts.append(embed_text(headers[c.section], text))
    return sections, chunks, embed_texts


def run_ingest(ctx: JobContext) -> None:
    s = get_settings()
    document_id = ctx.document_id
    with session_scope() as db:
        doc = db.get(Document, document_id) if document_id else None
        if doc is None:
            raise PermanentJobError("document no longer exists")
        version = doc.current_version + 1
        filename, sha, collection_id = doc.filename, doc.sha256, doc.collection_id
        if doc.current_version == 0:
            repositories.set_document_fields(db, document_id, status=DocumentStatus.PROCESSING,
                                             error=None)

    ctx.report("parsing", 0.05)
    try:
        content = FileStore().read(sha)
    except FileNotFoundError:
        raise PermanentJobError("the original file is missing from the file store")
    try:
        parsed = parse_document(filename, content)
    except (UnsupportedFileType, MissingParser) as e:
        raise PermanentJobError(str(e)) from e
    except Exception as e:                                  # corrupt or encrypted files
        raise PermanentJobError(f"could not read the file: {e}") from e
    blocks = clean_blocks(parsed.blocks, parsed.kind, parsed.pages)
    if not any(b.text.strip() for b in blocks):
        raise PermanentJobError("no text found in the file (scanned PDFs need OCR, "
                                "which is not supported yet)")
    structure = build_structure(blocks, parsed.kind, PurePath(filename).stem)

    ctx.report("chunking", 0.15)
    embedder = registry.get_embedder()
    spans = token_spans_for(embedder.tokenizer)
    max_seq = int(getattr(embedder, "max_seq_length", 256) or 256)
    sections, chunks, texts = build_rows(document_id, collection_id, version, structure,
                                         spans, max_seq)

    ctx.report("storing", 0.3)
    with session_scope() as db:
        repositories.delete_version(db, document_id, version)   # leftovers of a failed attempt
        repositories.write_version(db, document_id, version, structure.text, sections, chunks)

    store = get_vector_store()
    batch = max(1, s.embed_batch_size)
    for i in range(0, len(chunks), batch):
        ctx.report("embedding", 0.35 + 0.55 * i / max(1, len(chunks)))
        vectors = embedder.encode(texts[i:i + batch])
        store.upsert([VectorRecord(c["id"], v, document_id, collection_id, version,
                                   c["page"] or 0, c["section_id"], c["section_path"])
                      for c, v in zip(chunks[i:i + batch], vectors)])

    ctx.report("indexing", 0.92)
    with session_scope() as db:
        doc = db.get(Document, document_id)
        if doc is None:                                      # deleted while we worked
            store.delete_document(document_id)
            raise PermanentJobError("document was deleted during ingestion")
        repositories.set_document_fields(
            db, document_id, current_version=version, status=DocumentStatus.READY,
            title=structure.title[:500], pages=parsed.pages, error=None)
        for old in repositories.versions_of(db, document_id):
            if old != version:
                repositories.delete_version(db, document_id, old)
    store.delete_document(document_id, keep_version=version)
    ctx.report("done", 0.99)
    log.info("ingested %s v%d: %d sections, %d chunks", document_id, version,
             len(sections), len(chunks))


def ingest_failed(job, error: str) -> None:
    """A document whose first ingest failed is FAILED; one that already has a
    searchable version stays READY and only records the error."""
    if not job.document_id:
        return
    with session_scope() as db:
        doc = db.get(Document, job.document_id)
        if doc is None:
            return
        if doc.current_version == 0:
            repositories.set_document_fields(db, doc.id, status=DocumentStatus.FAILED, error=error)
        else:
            repositories.set_document_fields(db, doc.id, error=f"re-ingest failed: {error}")


HANDLERS = {INGEST: JobHandler(run=run_ingest, on_failed=ingest_failed)}
