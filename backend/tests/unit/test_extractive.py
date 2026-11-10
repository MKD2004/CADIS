import pytest

from cadis.answer import extractive as ex
from fakes import FakeEmbedder, n_tokens

WORDS = " ".join(f"word{i}" for i in range(1000))


def test_passage_limit_respects_embedder_capacity():
    assert ex.passage_token_limit(FakeEmbedder(max_seq_length=256)) == 220   # setting is lower
    assert ex.passage_token_limit(FakeEmbedder(max_seq_length=128)) == 128 - 2


def test_passages_cover_every_word_and_offsets_are_exact():
    emb = FakeEmbedder()
    passages = ex._split_passages(WORDS, emb)
    assert len(passages) > 1
    covered = set()
    for text, base in passages:
        assert WORDS[base:base + len(text)] == text
        covered.update(range(base, base + len(text)))
    assert all(i in covered for i, ch in enumerate(WORDS) if not ch.isspace())


def test_passages_never_exceed_embedder_limit():
    emb = FakeEmbedder(max_seq_length=64)
    text = "Revenue was 4,200,000.50 in FY2024-Q3 (see §12.4/b). " * 200   # many tokens per word
    for p, _ in ex._split_passages(text, emb):
        assert n_tokens(p) + 2 <= emb.max_seq_length


def test_passages_do_not_cut_words():
    emb = FakeEmbedder(max_seq_length=40)
    text = "alpha-beta gamma.delta " * 100
    for p, base in ex._split_passages(text, emb):
        assert base == 0 or text[base - 1].isspace()
        end = base + len(p)
        assert end == len(text) or text[end].isspace()


def test_long_unbroken_word_does_not_blow_the_limit():
    emb = FakeEmbedder(max_seq_length=40)
    text = "start " + "x." * 400 + " end"          # one 800-char "word", ~800 tokens
    passages = ex._split_passages(text, emb)
    for p, _ in passages:
        assert n_tokens(p) + 2 <= emb.max_seq_length
    assert "".join(p for p, _ in passages).count("x") >= 400   # still covered (as cut pieces)


def test_empty_text_gives_no_passages():
    assert ex._split_passages("   ", FakeEmbedder()) == []


def test_merge_joins_adjacent_and_overlapping_only():
    doc = "a" * 100
    merged = ex._merge_passages(doc, [(doc[0:10], 0), (doc[5:20], 5), (doc[20:30], 20), (doc[50:60], 50)])
    assert [(b, len(t)) for t, b in merged] == [(0, 30), (50, 10)]


@pytest.mark.parametrize("raw, expected", [
    (" , Tim Cook. ", "Tim Cook."),
    ("(Berlin)", "(Berlin)"),              # balanced brackets are kept
    (") Berlin (", "Berlin"),              # dangling ones are dropped
    ("$2.5 billion,", "$2.5 billion"),
])
def test_trim_span(raw, expected):
    s, e = ex._trim_span(raw, 0, len(raw))
    assert raw[s:e] == expected


def test_passage_cache_reuses_embeddings_and_evicts(monkeypatch):
    monkeypatch.setenv("CADIS_PASSAGE_CACHE_SIZE", "2")
    emb = FakeEmbedder()
    ex.passage_cache.get("doc one text", emb)
    ex.passage_cache.get("doc one text", emb)
    assert emb.calls == 1                       # second call was a cache hit
    ex.passage_cache.get("doc two", emb)
    ex.passage_cache.get("doc three", emb)
    assert len(ex.passage_cache) == 2           # oldest evicted
    ex.passage_cache.get("doc one text", emb)
    assert emb.calls == 4                       # had to recompute doc one


def _fake_best_span(answer_text):
    """A _best_span stand-in that 'finds' answer_text inside the first block."""
    def fake(question, blocks, tokenizer, model):
        text, base = blocks[0]
        i = text.index(answer_text)
        return (10.0, base + i, base + i + len(answer_text)), 2.0
    return fake


def test_answer_offsets_are_relative_to_text_as_sent(monkeypatch):
    monkeypatch.setattr(ex, "_best_span", _fake_best_span("Tim Cook"))
    sent = "\n\n   The deal was confirmed by Tim Cook in San Francisco."
    r = ex.answer_question("Who?", sent, None, None, FakeEmbedder())
    assert r["answer"] == "Tim Cook"
    assert sent[r["start"]:r["end"]] == "Tim Cook"
    assert 0.99 < r["confidence"] <= 1.0          # sigmoid(10 - 2)


def test_no_answer_when_null_score_wins(monkeypatch):
    monkeypatch.setattr(ex, "_best_span", lambda q, b, t, m: ((1.0, 0, 3), 5.0))
    r = ex.answer_question("Who?", "Tim Cook spoke.", None, None, FakeEmbedder())
    assert r == {"question": "Who?", "answer": "", "confidence": 0.0, "start": 0, "end": 0}


@pytest.mark.parametrize("question, text", [("", "Some text."), ("Who?", "   ")])
def test_empty_inputs_give_empty_answer(question, text):
    r = ex.answer_question(question, text, None, None, FakeEmbedder())
    assert r["answer"] == "" and r["start"] == r["end"] == 0
