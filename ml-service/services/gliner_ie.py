"""
services/gliner_ie.py
=====================
GliNER-based zero-shot Named Entity Recognition service.

Key design decisions
────────────────────
• GliNER accepts *arbitrary* entity labels at inference time —
  no retraining needed for new domains (Cybersecurity, Medical, Legal, etc.)
• Model is loaded once and held in a module-level singleton via
  GliNERService, preventing repeated cold-start overhead across requests.
• All public methods are typed and return Pydantic models so the
  router layer never touches raw GliNER output.

Usage
─────
    svc = GliNERService.get_instance()
    result = svc.extract(text, ["Malware", "CVE", "Financial Asset"])
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import ClassVar

from core.config import get_settings
from core.logging import get_logger
from models.schemas import EntitySpan, NERResponse

logger = get_logger(__name__)


class GliNERService:
    """
    Singleton wrapper around the GliNER model.

    Thread-safe lazy initialisation — the model is only loaded
    on the first call to get_instance(), not at import time.
    """

    _instance: ClassVar[GliNERService | None] = None
    _lock:     ClassVar[threading.Lock]        = threading.Lock()

    # ── Constructor ───────────────────────────────────────────

    def __init__(self) -> None:
        self._settings  = get_settings()
        self._model     = None          # loaded lazily
        self._model_id  = self._settings.gliner_model_id

    # ── Singleton accessor ────────────────────────────────────

    @classmethod
    def get_instance(cls) -> GliNERService:
        """Return the singleton, creating it on the first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:          # double-checked locking
                    instance = cls()
                    instance._load_model()
                    cls._instance = instance
        return cls._instance

    # ── Model lifecycle ───────────────────────────────────────

    def _load_model(self) -> None:
        """
        Load the GliNER model from HuggingFace Hub.
        Called exactly once during the application lifespan.
        """
        try:
            from gliner import GLiNER  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "GliNER is not installed. Run: pip install gliner"
            ) from exc

        logger.info("Loading GliNER model: %s", self._model_id)
        self._model = GLiNER.from_pretrained(self._model_id)
        logger.info("GliNER model loaded successfully.")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    # ── Core extraction ───────────────────────────────────────

    def extract(
        self,
        text:          str,
        entity_labels: list[str],
        threshold:     float = 0.5,
        flat_ner:      bool  = True,
    ) -> NERResponse:
        """
        Run zero-shot NER over `text` for the given `entity_labels`.

        Parameters
        ----------
        text          : The raw input text (up to ~50 k chars).
        entity_labels : Arbitrary label strings, e.g. ["Malware", "CVE ID"].
        threshold     : Minimum confidence score to include a span.
        flat_ner      : Resolve overlapping spans when True.

        Returns
        -------
        NERResponse   : Structured response with spans + grouped dict.
        """
        if not self.is_ready:
            raise RuntimeError("GliNER model is not loaded.")

        logger.debug(
            "Running GliNER on %d chars with labels: %s",
            len(text), entity_labels,
        )

        # GliNER predict_entities returns a list of dicts:
        # [{"text": str, "label": str, "start": int, "end": int, "score": float}]
        raw: list[dict] = self._model.predict_entities(
            text,
            entity_labels,
            threshold=threshold,
            flat_ner=flat_ner,
        )

        spans = [
            EntitySpan(
                text  = hit["text"],
                label = hit["label"],
                start = hit["start"],
                end   = hit["end"],
                score = round(float(hit["score"]), 4),
            )
            for hit in raw
        ]

        # Group by label for convenient downstream consumption
        grouped: dict[str, list[EntitySpan]] = defaultdict(list)
        for span in spans:
            grouped[span.label].append(span)

        logger.info(
            "GliNER extracted %d entities across %d label types.",
            len(spans), len(grouped),
        )

        return NERResponse(
            entity_labels = entity_labels,
            entities      = spans,
            entity_count  = len(spans),
            grouped       = dict(grouped),
        )

    # ── Batch extraction ──────────────────────────────────────

    def extract_batch(
        self,
        texts:         list[str],
        entity_labels: list[str],
        threshold:     float = 0.5,
    ) -> list[NERResponse]:
        """
        Process a list of texts in a single GliNER batch call.
        More efficient than calling extract() in a loop for large corpora.
        """
        if not self.is_ready:
            raise RuntimeError("GliNER model is not loaded.")

        logger.debug("Running GliNER batch on %d texts.", len(texts))

        raw_batch: list[list[dict]] = self._model.batch_predict_entities(
            texts,
            entity_labels,
            threshold=threshold,
        )

        results: list[NERResponse] = []
        for raw in raw_batch:
            spans = [
                EntitySpan(
                    text  = hit["text"],
                    label = hit["label"],
                    start = hit["start"],
                    end   = hit["end"],
                    score = round(float(hit["score"]), 4),
                )
                for hit in raw
            ]
            grouped: dict[str, list[EntitySpan]] = defaultdict(list)
            for span in spans:
                grouped[span.label].append(span)

            results.append(NERResponse(
                entity_labels = entity_labels,
                entities      = spans,
                entity_count  = len(spans),
                grouped       = dict(grouped),
            ))

        return results
