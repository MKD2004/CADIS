"""Phase 2 retrieval: RRF, section routing, the retrieve pipeline, small-to-big,
extractive answers over contexts, and the /search and /query endpoints."""

import pytest
from fastapi.testclient import TestClient

from cadis.answer import extractive
from cadis.index.exact import ExactIndex, overlap_at_k
from cadis.index.vector_store import get_vector_store
from cadis.ingest.pipeline import HANDLERS
from cadis.ingest.service import upload
from cadis.jobs.worker import Worker
from cadis.main import create_app
from cadis.models import embedding, registry
from cadis.retrieval import expand as expand_mod
from cadis.retrieval.hybrid import rrf
from cadis.retrieval.retrieve import Retrieval, retrieve
from cadis.retrieval.sections import _Title, _title_stems, find_mentions
from cadis.storage import repositories
from cadis.storage.db import session_scope
from conftest import EVAL_DOCS


# ── fusion ─────────────────────────────────────────────────────────────────────

def test_rrf_rewards_items_found_by_several_lists():
    fused = rrf([["a", "b", "c"], ["c", "d"]], k=60)
    assert fused[0][0] == "c"                              # in both lists
    assert [i for i, _ in fused] == ["c", "a", "b", "d"]
    assert fused[0][1] == pytest.approx(1 / 63 + 1 / 61)


def test_rrf_is_deterministic_on_ties():
    assert [i for i, _ in rrf([["x"], ["y"]])] == ["x", "y"]


# ── section names in questions ─────────────────────────────────────────────────

TITLES = ["3 Methodology", "3.2 Dataset", "4 Experiments", "Customers", "Customers and Partnerships",
          "8. Payment", "Study Design", "Results", "Trial"]


def mentions(question, titles=TITLES):
    ts = [_Title(str(i), "d", t, _title_stems(t)) for i, t in enumerate(titles)]
    return [(phrase, sorted(t.title for t in group)) for phrase, group in find_mentions(question, ts)]


def test_named_sections_are_found_with_cues():
    assert mentions("Find the dataset information from Methodology and the results from Experiments.") == [
        ("Methodology", ["3 Methodology"]), ("Experiments", ["4 Experiments"])]
    assert mentions("What does the Payment clause say?") == [("Payment", ["8. Payment"])]
    assert mentions("from the study design part, how many?") == [("study design", ["Study Design"])]


def test_stems_match_word_variants():
    assert mentions("Summarise the Methods section") == [("Methods", ["3 Methodology"])]


def test_ordinary_words_are_not_section_names():
    assert mentions("What were the results of the trial?") == []
    assert mentions("How many patients were enrolled in the VX-7890 trial?") == []
    assert mentions("Which customers signed in Q1?") == []


def test_longest_match_wins():
    assert mentions("In the Customers and Partnerships section, who paused?") == [
        ("Customers and Partnerships", ["Customers and Partnerships"])]


# ── retrieve / expand / answer over an ingested collection ────────────────────

@pytest.fixture
def col(v2):
    with session_scope() as s:
        c = repositories.create_collection(s, "default", "C")
        ids = {n: upload(s, c.id, n, (EVAL_DOCS / n).read_bytes()).document_id
               for n in ("energy.txt", "supply.txt", "legal.txt", "operations.txt")}
    Worker(HANDLERS, "w").drain()
    return c.id, ids


def test_retrieve_finds_the_right_section(col):
    col_id, _ = col
    r = retrieve("How much energy can the Harlow Ridge battery storage system store?", [col_id])
    assert r.hits and r.hits[0].section_path == "Storage"
    assert len(r.hits) <= 8 and r.timings_ms["total"] >= 0
    assert all(h.score >= r.hits[i + 1].score for i, h in enumerate(r.hits[:-1]))


def test_every_named_section_gets_a_slot(col):
    col_id, _ = col
    q = "Find the battery capacity in the Storage section and the record demand peak in the Extreme Weather section."
    r = retrieve(q, [col_id], k=2)
    assert [t.phrase for t in r.targets] == ["Storage", "Extreme Weather"]
    assert {h.section_path for h in r.hits} == {"Storage", "Extreme Weather"}
    assert {h.target for h in r.hits} == {"Storage", "Extreme Weather"}


def test_section_filter_can_be_switched_off(col):
    col_id, _ = col
    r = retrieve("From the Outlook section, what share of electricity?", [col_id], use_sections=False)
    assert r.targets == [] and all(h.target is None for h in r.hits)


@pytest.mark.parametrize("mode", ["dense", "keyword", "hybrid"])
def test_modes_and_no_reranker(col, mode):
    col_id, _ = col
    r = retrieve("late payment interest", [col_id], mode=mode, use_reranker=False)
    assert r.hits


def test_hits_do_not_largely_overlap(col):
    col_id, _ = col
    hits = retrieve("Meridian payment", [col_id], k=20).hits
    for i, a in enumerate(hits):
        for b in hits[i + 1:]:
            if a.document_id == b.document_id:
                inter = min(a.char_end, b.char_end) - max(a.char_start, b.char_start)
                assert inter <= 0.5 * min(a.char_end - a.char_start, b.char_end - b.char_start)


def test_retrieve_needs_allowed_collections(col):
    assert retrieve("payment", []).hits == []
    assert retrieve("payment", ["someone-else"]).hits == []
    assert retrieve("   ", [col[0]]).hits == []


def test_document_filter(col):
    col_id, ids = col
    hits = retrieve("payment interest", [col_id], document_ids=[ids["legal.txt"]]).hits
    assert hits and {h.document_id for h in hits} == {ids["legal.txt"]}


def test_expand_adds_neighbours_within_the_section_only(col):
    col_id, _ = col
    r = retrieve("Harlow Ridge battery", [col_id], k=1)
    [ctx] = expand_mod.expand(r, neighbours=1)
    hit = r.hits[0]
    assert ctx.char_start <= hit.char_start and hit.char_end <= ctx.char_end
    assert "Extreme Weather" not in ctx.text and "\n\nGeneration" not in ctx.text


def test_expand_merges_spans_and_slices_document_text(col):
    col_id, _ = col
    r = retrieve("Meridian payment late interest", [col_id], k=8)
    contexts = expand_mod.expand(r, neighbours=2)
    with session_scope() as s:
        from cadis.storage.tables import Document, DocumentText
        for c in contexts:
            v = s.get(Document, c.document_id).current_version
            text = s.get(DocumentText, (c.document_id, v)).text
            assert text[c.char_start:c.char_end] == c.text
    by_doc = {}
    for c in contexts:
        for o in by_doc.get(c.document_id, []):
            assert c.char_start > o.char_end + 2 or c.char_end < o.char_start - 2   # merged
        by_doc.setdefault(c.document_id, []).append(c)


def test_answer_contexts_maps_back_to_the_right_context(monkeypatch):
    contexts = ["First context about cats.", "Second one: the fee is $42 per unit."]

    def fake_best_span(question, blocks, tokenizer, model):
        text, base = blocks[1]
        i = text.index("$42")
        return (5.0, base + i, base + i + len("$42 per unit")), 1.0

    monkeypatch.setattr(extractive, "_best_span", fake_best_span)
    r = extractive.answer_contexts("What is the fee?", contexts, None, None)
    assert r["context"] == 1 and contexts[1][r["start"]:r["end"]] == "$42 per unit" == r["answer"]
    assert r["confidence"] > 0.5


def test_answer_contexts_abstains_when_null_wins(monkeypatch):
    monkeypatch.setattr(extractive, "_best_span", lambda *a: ((1.0, 0, 5), 3.0))
    assert extractive.answer_contexts("q?", ["Hello world"], None, None)["answer"] == ""


def test_bge_models_get_a_query_prefix(monkeypatch):
    from cadis.config import get_settings
    monkeypatch.setattr(get_settings(), "emb_model", "BAAI/bge-small-en-v1.5")
    assert embedding.query_prefix().startswith("Represent this sentence")
    monkeypatch.setattr(get_settings(), "emb_model", "all-MiniLM-L6-v2")
    assert embedding.query_prefix() == ""
    monkeypatch.setattr(get_settings(), "emb_query_prefix", "query: ")
    assert embedding.query_prefix() == "query: "


def test_exact_index_matches_the_store(col):
    col_id, _ = col
    store = get_vector_store()
    exact = ExactIndex.from_store(store)
    q = embedding.embed_query("battery storage")
    approx = store.search(q, [col_id], 10)
    truth = exact.search(q, [col_id], 10)
    assert overlap_at_k(approx, truth, 10) == 1.0
    assert exact.search(q, ["nobody"], 10) == []


# ── API ────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(col):
    with TestClient(create_app()) as c:
        yield c


def test_search_endpoint(client, col):
    r = client.post("/search", json={"question": "In the Storage section, what is the battery capacity?"})
    assert r.status_code == 200
    body = r.json()
    assert body["sections"][0]["phrase"] == "Storage"
    assert body["hits"][0]["section_path"] == "Storage"
    assert client.post("/search", json={"question": "x", "collection_ids": ["not-mine"]}).status_code == 404
    assert client.post("/search", json={"question": ""}).status_code == 422


def test_query_endpoint_answers_with_a_citation(client, col, monkeypatch):
    monkeypatch.setattr(registry, "get_qa_pipe", lambda: (None, None))

    def fake_best_span(question, blocks, tokenizer, model):
        for text, base in blocks:
            i = text.find("1,100 megawatt-hours")
            if i >= 0:
                return (6.0, base + i, base + i + len("1,100 megawatt-hours")), 1.0
        return None, None

    monkeypatch.setattr(extractive, "_best_span", fake_best_span)
    body = client.post("/query", json={"question": "How much can the Harlow Ridge battery store?"}).json()
    assert body["status"] == "answered" and body["answer_text"] == "1,100 megawatt-hours"
    cite = body["claims"][0]["citations"][0]
    assert cite["quote"] == "1,100 megawatt-hours" and cite["section_path"] == "Storage"
    with session_scope() as s:
        from cadis.storage.tables import Document, DocumentText
        v = s.get(Document, cite["document_id"]).current_version
        text = s.get(DocumentText, (cite["document_id"], v)).text
    assert text[cite["char_start"]:cite["char_end"]] == cite["quote"]

    monkeypatch.setattr(extractive, "_best_span", lambda *a: (None, None))
    assert client.post("/query", json={"question": "Who won?"}).json()["status"] == "not_in_documents"


def test_targets_are_limited_to_candidate_documents(col):
    from cadis.retrieval.sections import resolve
    col_id, ids = col
    q = "What does the Facilities section say?"
    with session_scope() as s:
        assert [t.phrase for t in resolve(s, q, [col_id])] == ["Facilities"]
        assert resolve(s, q, [col_id], candidate_documents={ids["energy.txt"]}) == []
        [t] = resolve(s, q, [col_id], candidate_documents={ids["operations.txt"]})
        assert t.titles == ["Facilities"]


def test_section_index_cache_sees_new_documents(col):
    from cadis.retrieval.sections import resolve
    col_id, _ = col
    q = "What does the Safety section say?"
    with session_scope() as s:
        assert resolve(s, q, [col_id]) == []                 # trial2 not ingested yet
        upload(s, col_id, "trial2.txt", (EVAL_DOCS / "trial2.txt").read_bytes())
    Worker(HANDLERS, "w").drain()
    with session_scope() as s:
        assert [t.phrase for t in resolve(s, q, [col_id])] == ["Safety"]


def test_large_k_is_not_capped_by_the_rerank_pool(col, monkeypatch):
    from cadis.config import get_settings
    monkeypatch.setattr(get_settings(), "rerank_candidates", 3)
    assert len(retrieve("the", [col[0]], k=12).hits) == 12
