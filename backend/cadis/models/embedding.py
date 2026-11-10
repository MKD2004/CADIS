"""Embedding helpers shared by ingestion and retrieval.

Some models expect an instruction on *queries* only — BGE English models are
trained with "Represent this sentence for searching relevant passages: " in
front of the question (ADR-011). Documents are embedded as they are.
"""

from cadis.config import get_settings
from cadis.models import registry

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def query_prefix() -> str:
    s = get_settings()
    if s.emb_query_prefix != "auto":
        return s.emb_query_prefix
    model = s.emb_model.lower()
    return BGE_QUERY_PREFIX if "bge" in model and "-en" in model else ""


def embed_query(question: str):
    return registry.get_embedder().encode([query_prefix() + question])[0]


def embed_documents(texts: list[str]):
    return registry.get_embedder().encode(texts)
