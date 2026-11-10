"""HTTP layer tests with fake models — checks wiring, status codes and shapes."""

import io
import json

import pytest
from fastapi.testclient import TestClient

from cadis.analysis import summary
from cadis.answer import extractive
from cadis.main import create_app
from cadis.models import registry
from fakes import FakeEmbedder, FakeNerPipe, FakeTokenizer, blank_nlp, make_pdf

DOC = ("Apple Inc. announced that it will acquire NeuralBase for $2.5 billion. "
       "The deal was confirmed by Tim Cook in San Francisco. ")


@pytest.fixture
def client(monkeypatch):
    nlp, emb = blank_nlp(), FakeEmbedder()
    ner = FakeNerPipe({"Tim Cook": "PER", "Apple Inc.": "ORG", "San Francisco": "LOC"})
    monkeypatch.setattr(registry, "get_nlp", lambda: nlp)
    monkeypatch.setattr(registry, "get_embedder", lambda: emb)
    monkeypatch.setattr(registry, "get_ner_pipe", lambda: ner)
    monkeypatch.setattr(registry, "get_qa_pipe", lambda: (None, None))
    monkeypatch.setattr(registry, "get_summarizer", lambda: (FakeTokenizer(), None))

    def fake_best_span(question, blocks, tokenizer, model):
        text, base = blocks[0]
        i = text.find("Tim Cook")
        return ((9.0, base + i, base + i + 8), 1.0) if i >= 0 else (None, None)

    monkeypatch.setattr(extractive, "_best_span", fake_best_span)
    monkeypatch.setattr(summary, "_generate", lambda text, *a, **k: "A short summary.")
    return TestClient(create_app())


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "service": "CADIS API v2.1"}


def test_cors_allows_known_origin_only(client):
    ok = client.options("/api/process", headers={"Origin": "http://localhost:3000",
                                                 "Access-Control-Request-Method": "POST"})
    bad = client.options("/api/process", headers={"Origin": "https://evil.example",
                                                  "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert bad.headers.get("access-control-allow-origin") is None


@pytest.mark.parametrize("name, content, status, detail", [
    ("a.txt", b"  hello world ", 200, None),
    ("a.pdf", make_pdf("Hello PDF"), 200, None),
    ("a.exe", b"MZ", 400, "Unsupported file type: a.exe. Use .txt, .pdf, or .docx"),
    ("a.txt", b"   ", 422, "No text could be extracted from the file."),
    ("a.pdf", b"not a pdf", 500, None),
])
def test_extract(client, name, content, status, detail):
    r = client.post("/api/extract", files={"file": (name, content)})
    assert r.status_code == status
    if status == 200:
        body = r.json()
        assert body["chars"] == len(body["text"]) and body["words"] == len(body["text"].split())
    elif detail:
        assert r.json()["detail"] == detail
    else:
        assert r.json()["detail"].startswith("Extraction error:")


def test_process_empty_keeps_v1_shape(client):
    r = client.post("/api/process", json={"text": "   "})
    assert r.status_code == 200 and r.json() == {"error": "Empty document"}


def test_process_returns_all_six_modules(client):
    body = client.post("/api/process", json={"text": "\n " + DOC * 3}).json()
    assert set(body) == {"preprocessing", "embeddings", "ner", "ambiguity", "qa", "summary"}
    assert body["summary"]["executive"] == "A short summary."
    assert [e["text"] for e in body["ner"]["entities"]["PERSON"]] == ["Tim Cook"]
    answered = [q for q in body["qa"]["results"] if q["answer"]]
    assert answered and all(q["answer"] == "Tim Cook" for q in answered)


def test_process_response_stays_small_for_long_documents(client):
    long_doc = " ".join(f"Sentence {i} reports revenue of {i} million in region {i % 9}." for i in range(800))
    r = client.post("/api/process", json={"text": long_doc})
    emb = r.json()["embeddings"]
    assert emb["matrix_size"] == 20 and emb["total_sentences"] == 800
    assert len(r.content) < 3_000_000


def test_qa_ask_offsets_match_the_text_sent(client):
    sent = "\n\n  " + DOC
    r = client.post("/api/qa-ask", json={"text": sent, "question": "Who confirmed the deal?"}).json()
    assert r["answer"] == "Tim Cook" and sent[r["start"]:r["end"]] == "Tim Cook"


def test_qa_ask_reuses_passages_from_process(client):
    emb = registry.get_embedder()
    client.post("/api/process", json={"text": DOC})
    before = emb.calls
    client.post("/api/qa-ask", json={"text": DOC, "question": "Who confirmed the deal?"})
    # Only the question is embedded (or nothing, for a short document) — not the passages.
    assert emb.calls - before <= 1
