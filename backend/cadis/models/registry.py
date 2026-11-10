"""The only place CADIS loads models (ARCHITECTURE_V2 §4, rule 4).

Each loader is cached with ``lru_cache(maxsize=1)``: weights load once per
process on first use and are reused afterwards. Heavy libraries are imported
inside the loaders so importing CADIS stays fast and tests can run without
them.

Callers must look loaders up through the module (``registry.get_nlp()``), not
``from registry import get_nlp`` — tests replace them with fakes via
``monkeypatch.setattr(registry, "get_nlp", ...)``.
"""

from functools import lru_cache

from cadis.config import get_settings


@lru_cache(maxsize=1)
def get_nlp():
    import spacy
    return spacy.load(get_settings().spacy_model)


@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(get_settings().emb_model)


@lru_cache(maxsize=1)
def get_ner_pipe():
    from transformers import pipeline
    s = get_settings()
    return pipeline("ner", model=s.ner_model, aggregation_strategy=s.ner_aggregation)


@lru_cache(maxsize=1)
def get_qa_pipe():
    """Returns (tokenizer, model) — span decoding is done by hand in answer.extractive."""
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer
    model_id = get_settings().qa_model
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(model_id)
    model.eval()
    return tokenizer, model


@lru_cache(maxsize=1)
def get_summarizer():
    """Returns (tokenizer, model)."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    model_id = get_settings().sum_model
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    model.eval()
    return tokenizer, model


LOADERS = {
    "spacy": get_nlp,
    "embedder": get_embedder,
    "ner": get_ner_pipe,
    "qa": get_qa_pipe,
    "summarizer": get_summarizer,
}


def loaded_models() -> list[str]:
    """Names of models already in memory (does not trigger loading)."""
    return [name for name, fn in LOADERS.items() if fn.cache_info().currsize]
