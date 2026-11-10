"""Checks that need the real models. Skipped by default; run with:

    pytest backend -m slow

First run downloads ~2 GB of weights into ~/.cache/huggingface.
"""

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cadis.analysis.ner import run_ner
from cadis.analysis.summary import _n_tokens, _sentence_chunks, summarize_document
from cadis.answer import extractive as ex
from cadis.main import create_app
from cadis.models import registry

pytestmark = pytest.mark.slow

ROOT = Path(__file__).resolve().parents[3]


def _samples():
    src = (ROOT / "client" / "app" / "launch" / "page.tsx").read_text(encoding="utf-8")
    return re.findall(r"text: `([^`]+)`", src)


def test_ner_reads_the_whole_long_document():
    filler = "The committee reviewed the quarterly figures and discussed the budget in detail. " * 300
    text = "Alice Johnson opened the meeting. " + filler + "Robert Brown closed the meeting."
    result = run_ner(text, registry.get_nlp()(text), registry.get_ner_pipe())
    names = {e["text"] for e in result["entities"]["PERSON"]}
    assert "Alice Johnson" in names
    # The person in the last sentence (past BERT's 512-token limit) must be
    # found at all — V1 found nothing there. After ~400 tokens of this
    # repetitive filler BERT tags "Brown" B-PER, so it comes back as "Robert"
    # + "Brown" rather than one span; in normal text it is one entity.
    assert any("Robert" in n for n in names)


def test_ner_has_no_word_piece_fragments():
    text = " ".join(_samples() * 2)
    result = run_ner(text, registry.get_nlp()(text), registry.get_ner_pipe())
    words = [e["text"] for group in result["entities"].values() for e in group]
    assert not [w for w in words if w.startswith("##")]
    assert "Aisha Patel" in {e["text"] for e in result["entities"]["PERSON"]}


def test_every_qa_passage_fits_the_embedding_model():
    emb = registry.get_embedder()
    text = " ".join(f"Invoice INV-{i:06d} for EUR 4,200,000.50 (FY2024-Q{i % 4 + 1}, §{i}.{i % 7}/b)."
                    for i in range(400))
    passages = ex._split_passages(text, emb)
    worst = max(len(emb.tokenizer(p)["input_ids"]) for p, _ in passages)
    assert worst <= emb.max_seq_length


def test_extractive_answer_on_sample():
    tech = _samples()[0]
    tok, model = registry.get_qa_pipe()
    r = ex.answer_question("Who confirmed the deal?", tech, tok, model, registry.get_embedder())
    assert "Tim Cook" in r["answer"]
    assert tech[r["start"]:r["end"]] == r["answer"]


def test_summary_chunks_fit_distilbart_and_cover_everything():
    tok, _ = registry.get_summarizer()
    text = " ".join(_samples() * 6)
    chunks = _sentence_chunks(text, tok)
    assert " ".join(chunks).split() == text.split()
    assert max(_n_tokens(c, tok) for c in chunks) <= 1022


def test_long_summary_runs():
    tok, model = registry.get_summarizer()
    out = summarize_document(" ".join(_samples() * 2), tok, model)
    assert out and not out.startswith("Summarization error")


def test_process_response_size_for_10k_words():
    text = " ".join(f"Sentence number {i} talks about contract {i} and revenue growth in region {i % 7}."
                    for i in range(800))
    r = TestClient(create_app()).post("/api/process", json={"text": text})
    assert r.status_code == 200
    size_mb = len(r.content) / 1e6
    print(f"\n/api/process for {len(text.split())} words: {size_mb:.2f} MB")
    assert size_mb < 5          # V1: preprocessing + embeddings alone were 14 MB
    assert json.loads(r.content)["embeddings"]["matrix_size"] == 20
