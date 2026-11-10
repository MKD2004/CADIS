from cadis.analysis import summary as sm
from fakes import FakeTokenizer, n_tokens

TOK = FakeTokenizer()


def _doc(n_sentences, words_per=12):
    return " ".join(
        " ".join(f"w{i}x{j}" for j in range(words_per - 1)) + "." for i in range(n_sentences)
    )


def test_chunks_cover_every_word_and_fit_the_limit():
    text = _doc(300)
    chunks = sm._sentence_chunks(text, TOK, target=100, limit=150)
    assert " ".join(chunks).split() == text.split()           # nothing dropped, order kept
    assert all(n_tokens(c) <= 150 for c in chunks)


def test_chunks_are_balanced():
    chunks = sm._sentence_chunks(_doc(100), TOK, target=200, limit=400)
    sizes = [n_tokens(c) for c in chunks]
    assert max(sizes) - min(sizes) <= 13                       # within one sentence


def test_unpunctuated_run_is_split_to_fit():
    text = " ".join(f"word{i}" for i in range(3000))           # no sentence boundaries
    chunks = sm._sentence_chunks(text, TOK, target=200, limit=300)
    assert " ".join(chunks).split() == text.split()
    assert all(n_tokens(c) <= 300 for c in chunks)


def test_clean_summary_fixes_spacing_and_trailing_fragment():
    assert sm._clean_summary("Revenue rose .  Costs fell , too. And then") == "Revenue rose. Costs fell, too."


def test_dedupe_drops_paraphrases():
    text = "The court upheld the new privacy laws. The new privacy law was upheld by the court. Prices rose."
    assert sm._dedupe_sentences(text) == "The court upheld the new privacy laws. Prices rose."


def test_long_document_is_mapped_then_reduced(monkeypatch):
    calls = []

    def fake_generate(text, tokenizer, model, max_len, min_len, beams=4):
        calls.append(n_tokens(text))
        return f"Summary sentence {len(calls)} about part {len(calls)} of the document."

    monkeypatch.setattr(sm, "_generate", fake_generate)
    out = sm.summarize_document(_doc(400), TOK, model=None)
    assert out.startswith("Summary sentence")
    assert all(n <= 1022 for n in calls)                       # every model input fits
    assert len(calls) >= 400 * 12 // 512                       # every chunk was summarized


def test_reduce_recurses_until_it_fits(monkeypatch):
    def wordy_generate(text, tokenizer, model, max_len, min_len, beams=4):
        # Very verbose "summaries" force the joined partials past 1024 tokens.
        return " ".join(f"Point {n} {text.split()[0]} unique{n}." for n in range(60))

    monkeypatch.setattr(sm, "_generate", wordy_generate)
    monkeypatch.setattr(sm, "_dedupe_sentences", lambda t, threshold=0.5: t)
    out = sm.summarize_document(_doc(800), TOK, model=None)
    assert out                                                 # terminated with a result
