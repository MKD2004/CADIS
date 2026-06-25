"""
services/summarizer.py
======================
DistilBART summarization service (singleton).

Loaded once at startup via get_instance() — never inside a request handler.
"""

from __future__ import annotations

import threading
import time
from typing import ClassVar

from core.logging import get_logger

logger = get_logger(__name__)


class SummarizerService:
    _instance: ClassVar[SummarizerService | None] = None
    _lock:     ClassVar[threading.Lock]            = threading.Lock()

    MODEL_ID = "sshleifer/distilbart-cnn-12-6"

    def __init__(self) -> None:
        self.tokenizer = None
        self.model = None

    @classmethod
    def get_instance(cls) -> SummarizerService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._load_model()
                    cls._instance = instance
        return cls._instance

    def _load_model(self) -> None:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # type: ignore
        t0 = time.perf_counter()
        logger.info("Loading DistilBART summarizer (%s)…", self.MODEL_ID)
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_ID)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.MODEL_ID)
        elapsed = time.perf_counter() - t0
        logger.info("DistilBART summarizer loaded in %.2fs.", elapsed)

    @property
    def is_ready(self) -> bool:
        return self.model is not None and self.tokenizer is not None

    def summarize(self, text: str) -> dict:
        if not self.is_ready:
            raise RuntimeError("DistilBART model is not loaded.")

        from core.metrics import timed_inference

        with timed_inference("distilbart") as timer:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=1024,
                truncation=True,
            )
            outputs = self.model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_length=100,
                min_length=20,
                num_beams=4,
                length_penalty=2.0,
                do_sample=False,
            )
            result = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        return {"text": result, "inference_ms": timer.duration_ms}
