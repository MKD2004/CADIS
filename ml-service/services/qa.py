"""
services/qa.py
==============
RoBERTa-based extractive QA service (singleton).

Loaded once at startup via get_instance() — never inside a request handler.
"""

from __future__ import annotations

import threading
import time
from typing import ClassVar

from core.logging import get_logger

logger = get_logger(__name__)


class QAService:
    _instance: ClassVar[QAService | None] = None
    _lock:     ClassVar[threading.Lock]    = threading.Lock()

    def __init__(self) -> None:
        self.qa_pipeline = None

    @classmethod
    def get_instance(cls) -> QAService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._load_model()
                    cls._instance = instance
        return cls._instance

    def _load_model(self) -> None:
        from transformers import pipeline  # type: ignore
        t0 = time.perf_counter()
        logger.info("Loading RoBERTa QA model (deepset/roberta-base-squad2)…")
        self.qa_pipeline = pipeline(
            "question-answering",
            model="deepset/roberta-base-squad2",
        )
        elapsed = time.perf_counter() - t0
        logger.info("RoBERTa QA model loaded in %.2fs.", elapsed)

    @property
    def is_ready(self) -> bool:
        return self.qa_pipeline is not None

    def answer_question(self, question: str, context: str) -> dict:
        if not self.is_ready:
            raise RuntimeError("RoBERTa QA model is not loaded.")

        if not context or not context.strip():
            return {"answer": "No context provided to find the answer.", "inference_ms": 0}

        try:
            from core.metrics import timed_inference
            with timed_inference("roberta") as timer:
                result = self.qa_pipeline(
                    question=question,
                    context=context[:2500],
                )
            return {"answer": result["answer"], "inference_ms": timer.duration_ms}
        except Exception as e:
            logger.error("QA extraction failed: %s", e)
            return {"answer": "I could not extract a definitive answer.", "inference_ms": 0}
