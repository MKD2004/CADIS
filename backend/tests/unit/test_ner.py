from cadis.analysis import ner
from fakes import FakeNerPipe, FakeTokenizer, blank_nlp, n_tokens

FILLER = "The committee reviewed the quarterly figures and discussed the budget. "


def _long_doc():
    return "Alice Johnson opened the meeting. " + FILLER * 120 + "Robert Brown closed the meeting."


def test_windows_fit_limit_and_cover_all_sentences():
    doc = blank_nlp()(_long_doc())
    windows = ner.ner_windows(doc, FakeTokenizer(), limit=40)
    assert all(n_tokens(doc.text[s:e]) <= 40 for s, e in windows)
    covered = "".join(doc.text[s:e] for s, e in windows).replace(" ", "")
    assert covered == doc.text.replace(" ", "")


def test_oversized_sentence_is_split():
    doc = blank_nlp()("word " * 500 + "end.")
    windows = ner.ner_windows(doc, FakeTokenizer(), limit=50)
    assert len(windows) > 1
    assert all(n_tokens(doc.text[s:e]) <= 50 for s, e in windows)


def test_entities_at_the_end_of_a_long_document_are_found(monkeypatch):
    monkeypatch.setenv("CADIS_NER_CHUNK_TOKENS", "45")
    text = _long_doc()
    pipe = FakeNerPipe({"Alice Johnson": "PER", "Robert Brown": "PER"}, max_tokens=50)
    result = ner.run_ner(text, blank_nlp()(text), pipe)
    names = [e["text"] for e in result["entities"]["PERSON"]]
    assert names == ["Alice Johnson", "Robert Brown"]           # V1 would miss Robert Brown
    assert all(isinstance(batch, list) for batch in pipe.inputs)  # windows sent as one batch


def test_entity_text_comes_from_the_document_not_the_tokenizer():
    text = "Report by Aisha Patel. " + FILLER
    pipe = FakeNerPipe({"Aisha Patel": "PER"})       # fake returns "aisha patel" as word
    result = ner.run_ner(text, blank_nlp()(text), pipe)
    assert result["entities"]["PERSON"] == [{"text": "Aisha Patel", "score": 0.99}]


def test_duplicates_are_removed_case_insensitively():
    text = "Robert Brown spoke. " + "Robert Brown left. "
    pipe = FakeNerPipe({"Robert Brown": "PER"})
    result = ner.run_ner(text, blank_nlp()(text), pipe)
    assert len(result["entities"]["PERSON"]) == 1
    assert result["stats"]["total_entities"] == 1
