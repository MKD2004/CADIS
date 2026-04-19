"""
routers/ner.py
==============
GliNER-based zero-shot Named Entity Recognition endpoints.

POST /api/v1/ner/extract
    Single-text extraction with arbitrary entity labels.

POST /api/v1/ner/extract-batch
    Batch extraction over multiple texts (same label set).

GET  /api/v1/ner/label-presets
    Returns built-in label presets for common domains.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from core.logging import get_logger
from models.schemas import NERRequest, NERResponse
from services.gliner_ie import GliNERService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ner", tags=["Named Entity Recognition"])


# ─────────────────────────────────────────────────────────────
#  Domain label presets
# ─────────────────────────────────────────────────────────────

LABEL_PRESETS: dict[str, list[str]] = {
    "cybersecurity": [
        "Cybersecurity Threat",
        "Malware",
        "CVE ID",
        "Attack Vector",
        "Threat Actor",
        "Vulnerability",
        "IP Address",
        "Domain Name",
        "Affected Software",
    ],
    "legal": [
        "Party",
        "Judge",
        "Court",
        "Case Number",
        "Legal Statute",
        "Jurisdiction",
        "Penalty",
        "Contract Clause",
        "Date of Judgment",
    ],
    "finance": [
        "Financial Asset",
        "Company",
        "Stock Ticker",
        "Currency Amount",
        "Financial Instrument",
        "Regulatory Body",
        "Market Index",
        "Fiscal Quarter",
    ],
    "medical": [
        "Disease",
        "Drug",
        "Symptom",
        "Medical Procedure",
        "Dosage",
        "Patient",
        "Physician",
        "Hospital",
        "Lab Value",
    ],
    "general": [
        "Person",
        "Organization",
        "Location",
        "Date",
        "Money",
        "Event",
    ],
}


# ─────────────────────────────────────────────────────────────
#  Dependency
# ─────────────────────────────────────────────────────────────

def get_gliner_service() -> GliNERService:
    svc = GliNERService.get_instance()
    if not svc.is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GliNER model is not ready. Check server logs.",
        )
    return svc


# ─────────────────────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────────────────────

@router.post(
    "/extract",
    response_model  = NERResponse,
    status_code     = status.HTTP_200_OK,
    summary         = "Zero-shot NER with dynamic entity labels",
    description     = (
        "Pass any text and a list of target entity labels — GliNER will "
        "extract matching spans without domain-specific fine-tuning. "
        "Use label presets from GET /label-presets or supply your own."
    ),
)
async def extract_entities(
    request: NERRequest,
    service: GliNERService = Depends(get_gliner_service),
) -> NERResponse:
    logger.info(
        "NER extract request — %d chars, labels: %s",
        len(request.text), request.entity_labels,
    )
    try:
        return service.extract(
            text          = request.text,
            entity_labels = request.entity_labels,
            threshold     = request.threshold,
            flat_ner      = request.flat_ner,
        )
    except Exception as exc:
        logger.exception("GliNER extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NER extraction failed: {exc}",
        ) from exc


@router.post(
    "/extract-batch",
    response_model  = list[NERResponse],
    status_code     = status.HTTP_200_OK,
    summary         = "Batch zero-shot NER across multiple texts",
)
async def extract_entities_batch(
    texts:         list[str],
    entity_labels: list[str],
    threshold:     float       = 0.5,
    service:       GliNERService = Depends(get_gliner_service),
) -> list[NERResponse]:
    if not texts:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="texts list must not be empty.",
        )
    if not entity_labels:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="entity_labels must not be empty.",
        )

    logger.info(
        "NER batch request — %d texts, labels: %s",
        len(texts), entity_labels,
    )
    try:
        return service.extract_batch(
            texts         = texts,
            entity_labels = entity_labels,
            threshold     = threshold,
        )
    except Exception as exc:
        logger.exception("GliNER batch extraction failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch NER extraction failed: {exc}",
        ) from exc


@router.get(
    "/label-presets",
    response_model  = dict[str, list[str]],
    status_code     = status.HTTP_200_OK,
    summary         = "List all built-in domain label presets",
)
async def get_label_presets() -> dict[str, list[str]]:
    """
    Returns pre-configured entity label sets for common domains.
    Pass any of these lists as `entity_labels` in /extract requests.
    """
    return LABEL_PRESETS


@router.get(
    "/label-presets/{domain}",
    response_model  = list[str],
    status_code     = status.HTTP_200_OK,
    summary         = "Get label preset for a specific domain",
)
async def get_domain_preset(domain: str) -> list[str]:
    if domain not in LABEL_PRESETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown domain '{domain}'. Available: {list(LABEL_PRESETS.keys())}",
        )
    return LABEL_PRESETS[domain]
