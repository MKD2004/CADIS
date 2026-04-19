"""
services/multimodal.py
======================
Multimodal RAG foundation — Vision-Language Model (VLM) integration.

Current state: PLACEHOLDER
─────────────────────────
The interface is fully defined and wired into the PDF pipeline.
Actual model inference is gated behind `Settings.vlm_enabled`.

When vlm_enabled=True and a GPU is available:
  • Qwen-VL-Chat is loaded via transformers AutoModelForCausalLM.
  • Each ImageBlock's base64 PNG is passed through the model.
  • The returned caption is stored in ImageBlock.vlm_description.
  • All captions are appended to the enriched_text context so that
    downstream RAG and QA modules can reason over diagram content.

Swap strategy
─────────────
Replace _describe_image_qwen() with any VLM:
  - LLaVA-1.6  (llava-hf/llava-v1.6-mistral-7b-hf)
  - InternVL2  (OpenGVLab/InternVL2-8B)
  - GPT-4o     (via openai client — set vlm_model_id="gpt-4o")
The public method describe_images() never changes.
"""

from __future__ import annotations

import base64
import io
import threading
from typing import ClassVar

from core.config import get_settings
from core.logging import get_logger
from models.schemas import ImageBlock

logger = get_logger(__name__)

_PLACEHOLDER_CAPTION = (
    "[VLM DISABLED] Set vlm_enabled=true in .env and ensure a GPU "
    "is available to activate Qwen-VL image descriptions."
)


class MultimodalService:
    """
    Singleton VLM service.

    Public API
    ──────────
    describe_images(image_blocks) → list[ImageBlock]
        Accepts a list of ImageBlock objects, runs each through the VLM,
        and returns the same list with .vlm_description populated.
    """

    _instance: ClassVar[MultimodalService | None] = None
    _lock:     ClassVar[threading.Lock]            = threading.Lock()

    def __init__(self) -> None:
        self._settings  = get_settings()
        self._model     = None
        self._tokenizer = None
        self._loaded    = False

    # ── Singleton ─────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> MultimodalService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    if instance._settings.vlm_enabled:
                        instance._load_model()
                    cls._instance = instance
        return cls._instance

    # ── Model lifecycle ───────────────────────────────────────

    def _load_model(self) -> None:
        """
        Load Qwen-VL-Chat.
        Requires: pip install transformers accelerate auto-gptq optimum
        Requires: CUDA GPU with ≥16 GB VRAM (or use 4-bit quantisation).
        """
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "transformers / torch not installed. Run: pip install transformers torch"
            ) from exc

        model_id = self._settings.vlm_model_id
        logger.info("Loading VLM: %s — this may take several minutes.", model_id)

        self._tokenizer = AutoTokenizer.from_pretrained(
            model_id, trust_remote_code=True
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map = "auto",          # multi-GPU aware
            trust_remote_code = True,
        ).eval()

        self._loaded = True
        logger.info("VLM loaded successfully.")

    # ── Public: describe images ───────────────────────────────

    def describe_images(self, image_blocks: list[ImageBlock]) -> list[ImageBlock]:
        """
        Iterate over image_blocks, call the VLM for each, and return
        the same list with .vlm_description populated.

        If vlm_enabled=False, a placeholder description is stored
        so the rest of the pipeline can continue uninterrupted.
        """
        if not image_blocks:
            return image_blocks

        if not self._settings.vlm_enabled or not self._loaded:
            logger.info(
                "VLM disabled — storing placeholder descriptions for %d image(s).",
                len(image_blocks),
            )
            for block in image_blocks:
                block.vlm_description = _PLACEHOLDER_CAPTION
            return image_blocks

        logger.info("Running VLM inference on %d image(s).", len(image_blocks))
        for block in image_blocks:
            try:
                block.vlm_description = self._describe_image_qwen(block)
            except Exception as exc:
                logger.error(
                    "VLM failed for image_id=%s: %s", block.image_id, exc
                )
                block.vlm_description = f"[VLM ERROR: {exc}]"

        return image_blocks

    # ── Private: Qwen-VL inference ────────────────────────────

    def _describe_image_qwen(self, block: ImageBlock) -> str:
        """
        Send a single ImageBlock to Qwen-VL-Chat and return its caption.

        Qwen-VL expects the image as a base64-encoded PNG passed inside
        a special <img> tag in the conversation template.
        """
        if not block.base64_data:
            return "[No image data available for VLM]"

        # Qwen-VL conversation format
        query = self._tokenizer.from_list_format([
            {"image": f"data:image/png;base64,{block.base64_data}"},
            {"text": (
                "Describe this image or diagram from a research document in detail. "
                "If it is a chart or graph, extract all axis labels, data trends, and key values. "
                "If it is a diagram, describe the components and their relationships. "
                "Be precise and technical."
            )},
        ])

        inputs = self._tokenizer(query, return_tensors="pt").to(self._model.device)

        with __import__("torch").no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens = 256,
                do_sample      = False,
            )

        # Decode only the newly generated tokens
        caption: str = self._tokenizer.decode(
            output_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        ).strip()

        logger.debug("VLM caption for %s: %r", block.image_id, caption[:80])
        return caption

    # ── Utility: build enriched text ──────────────────────────

    @staticmethod
    def build_enriched_text(
        raw_text: str,
        image_blocks: list[ImageBlock],
    ) -> str:
        """
        Append VLM descriptions back into the document text.
        This enriched string is what gets chunked and stored in ChromaDB.

        Output format:
            <original text>

            --- Figure 1 (page 3) ---
            <VLM description>

            --- Figure 2 (page 5) ---
            <VLM description>
        """
        parts = [raw_text.strip()]

        for i, block in enumerate(image_blocks, start=1):
            if block.vlm_description:
                page_info = f"page {block.page_number}" if block.page_number else "unknown page"
                parts.append(
                    f"\n\n--- Figure {i} ({page_info}) ---\n"
                    f"{block.vlm_description}"
                )

        return "\n".join(parts)

    @property
    def is_ready(self) -> bool:
        return not self._settings.vlm_enabled or self._loaded
