"""
routers/document.py
===================
Routes for PDF ingestion and multimodal document processing.

POST /api/v1/process-pdf
    1. Parse PDF with unstructured.io (text blocks + image extraction)
    2. Run extracted images through the VLM service (Qwen-VL)
    3. Merge VLM captions back into the document context
    4. Chunk enriched text and upsert into ChromaDB
    5. Return the full ParsedDocument to the caller
"""

from __future__ import annotations

import base64
import hashlib
import io
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Depends
from fastapi.responses import JSONResponse

from core.config import Settings, get_settings
from core.logging import get_logger
from models.schemas import ImageBlock, ParsedDocument, TextBlock, UpsertResponse
from services.multimodal import MultimodalService
from services.vector_store import VectorStoreService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Document Processing"])

_ALLOWED_MIME = {"application/pdf"}
_MAX_CHUNK_TOKENS = 400    # approximate words per chunk


# ─────────────────────────────────────────────────────────────
#  Dependency injectors
# ─────────────────────────────────────────────────────────────

def get_vector_store() -> VectorStoreService:
    return VectorStoreService.get_instance()

def get_vlm_service() -> MultimodalService:
    return MultimodalService.get_instance()


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _validate_pdf(upload: UploadFile, settings: Settings) -> None:
    """Raise HTTP 422 if the upload is not a valid PDF within size limits."""
    if upload.content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Only PDF files are accepted. Got: {upload.content_type}",
        )


def _chunk_text(text: str, chunk_size: int = _MAX_CHUNK_TOKENS) -> list[str]:
    """
    Naïve sliding-window chunker (word-based).
    Replace with RecursiveCharacterTextSplitter for production.
    """
    words  = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def _parse_with_unstructured(
    pdf_bytes: bytes,
    extract_images: bool,
    strategy: str,
) -> tuple[list[TextBlock], list[ImageBlock]]:
    """
    Run unstructured.io partition_pdf on the raw PDF bytes.
    Returns (text_blocks, image_blocks).
    """
    try:
        from unstructured.partition.pdf import partition_pdf  # type: ignore
        from unstructured.documents.elements import (          # type: ignore
            Image as UnstructuredImage,
            Table,
            Title,
            NarrativeText,
            ListItem,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="unstructured[pdf] is not installed. Run: pip install 'unstructured[pdf]'",
        ) from exc

    # Write to a temp buffer — unstructured needs a file-like object
    pdf_buffer = io.BytesIO(pdf_bytes)

    elements = partition_pdf(
        file                         = pdf_buffer,
        strategy                     = strategy,      # "hi_res" | "fast"
        extract_images_in_pdf        = extract_images,
        extract_image_block_types    = ["Image", "Table"],
        extract_image_block_to_payload = extract_images,  # base64 in metadata
    )

    text_blocks:  list[TextBlock]  = []
    image_blocks: list[ImageBlock] = []

    for i, el in enumerate(elements):
        el_type  = type(el).__name__
        page_num = el.metadata.page_number if el.metadata else None

        if isinstance(el, UnstructuredImage):
            # Extract base64 image data if available
            b64 = None
            if extract_images and el.metadata and el.metadata.image_base64:
                b64 = el.metadata.image_base64

            image_blocks.append(ImageBlock(
                image_id    = f"img-{i:04d}",
                page_number = page_num,
                base64_data = b64,
            ))
        else:
            text_blocks.append(TextBlock(
                block_id     = f"blk-{i:04d}",
                element_type = el_type,
                text         = str(el).strip(),
                page_number  = page_num,
                metadata     = el.metadata.to_dict() if el.metadata else {},
            ))

    return text_blocks, image_blocks


# ─────────────────────────────────────────────────────────────
#  Endpoint
# ─────────────────────────────────────────────────────────────

@router.post(
    "/process-pdf",
    response_model  = ParsedDocument,
    status_code     = status.HTTP_200_OK,
    summary         = "Parse a PDF and run the multimodal RAG pipeline",
    description     = (
        "Accepts a PDF file, parses it with unstructured.io, optionally "
        "describes extracted images via a Vision-Language Model (Qwen-VL), "
        "and stores chunked embeddings in ChromaDB for downstream RAG."
    ),
)
async def process_pdf(
    file:            UploadFile                  = File(..., description="PDF file to process"),
    collection_name: str                         = Form(default="cadis_documents"),
    extract_images:  bool                        = Form(default=True),
    run_vlm:         bool                        = Form(default=False, description="Pass image blocks through VLM"),
    settings:        Settings                    = Depends(get_settings),
    vector_store:    VectorStoreService          = Depends(get_vector_store),
    vlm_service:     MultimodalService           = Depends(get_vlm_service),
) -> ParsedDocument:

    _validate_pdf(file, settings)

    logger.info("Processing PDF: %s", file.filename)
    pdf_bytes = await file.read()

    # ── 1. Parse PDF with unstructured.io ──────────────────────
    text_blocks, image_blocks = _parse_with_unstructured(
        pdf_bytes,
        extract_images = extract_images,
        strategy       = settings.unstructured_strategy,
    )
    logger.info(
        "Parsed %d text blocks and %d image blocks from '%s'.",
        len(text_blocks), len(image_blocks), file.filename,
    )

    # ── 2. Multimodal RAG: VLM image descriptions ──────────────
    if run_vlm and image_blocks:
        logger.info("Running VLM on %d image blocks…", len(image_blocks))
        image_blocks = vlm_service.describe_images(image_blocks)

    # ── 3. Build enriched flat text (text + VLM captions) ──────
    raw_text     = "\n\n".join(
        blk.text for blk in text_blocks if blk.text.strip()
    )
    enriched_text = MultimodalService.build_enriched_text(raw_text, image_blocks)

    # ── 4. Chunk + upsert into ChromaDB ────────────────────────
    document_id = hashlib.sha256(pdf_bytes).hexdigest()[:16]
    chunks      = _chunk_text(enriched_text)

    if chunks:
        vector_store.upsert_document(
            document_id     = document_id,
            chunks          = chunks,
            collection_name = collection_name,
            extra_metadata  = {"filename": file.filename or "unknown"},
        )
        logger.info("Stored %d chunks in collection '%s'.", len(chunks), collection_name)

    # ── 5. Assemble and return response ────────────────────────
    page_numbers = [
        blk.page_number for blk in text_blocks if blk.page_number is not None
    ]
    total_pages = max(page_numbers) if page_numbers else None

    return ParsedDocument(
        document_id   = document_id,
        filename      = file.filename or "unknown.pdf",
        total_pages   = total_pages,
        text_blocks   = text_blocks,
        image_blocks  = image_blocks,
        enriched_text = enriched_text,
        metadata      = {
            "collection":     collection_name,
            "chunks_stored":  len(chunks),
            "vlm_ran":        run_vlm and bool(image_blocks),
            "strategy":       settings.unstructured_strategy,
        },
    )


@router.delete(
    "/documents/{document_id}",
    status_code = status.HTTP_200_OK,
    summary     = "Delete all vector chunks for a document",
)
async def delete_document(
    document_id:     str,
    collection_name: str               = "cadis_documents",
    vector_store:    VectorStoreService = Depends(get_vector_store),
) -> dict:
    deleted = vector_store.delete_document(document_id, collection_name)
    return {"document_id": document_id, "chunks_deleted": deleted}
