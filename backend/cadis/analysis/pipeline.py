"""Run all six modules over one text (the V1 /api/process behaviour).

In V2 the modules run as background jobs per stored document (Phase 1/5);
this function remains for the legacy endpoint and the benchmark.
"""

from cadis.analysis.ambiguity import run_ambiguity
from cadis.analysis.embeddings_view import run_embeddings
from cadis.analysis.ner import run_ner
from cadis.analysis.preprocessing import run_preprocessing
from cadis.analysis.summary import run_summary
from cadis.answer.extractive import run_qa
from cadis.models import registry


def load_all_models():
    """Load (or fetch from cache) every model the pipeline needs."""
    return (
        registry.get_nlp(),
        registry.get_embedder(),
        registry.get_ner_pipe(),
        registry.get_qa_pipe(),
        registry.get_summarizer(),
    )


def process_text(text: str) -> dict:
    """`text` must already be stripped and non-empty."""
    nlp, embedder, ner_pipe, qa_pipe, summarizer = load_all_models()

    preprocessing_result, sp_doc = run_preprocessing(text, nlp)
    sentences = preprocessing_result["sentences"]

    return {
        "preprocessing": preprocessing_result,
        "embeddings":    run_embeddings(sentences, embedder),
        "ner":           run_ner(text, sp_doc, ner_pipe),
        "ambiguity":     run_ambiguity(text, sp_doc, embedder),
        "qa":            run_qa(text, qa_pipe, embedder),
        "summary":       run_summary(text, sp_doc, summarizer),
    }
