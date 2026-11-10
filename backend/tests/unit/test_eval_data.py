"""Guards the evaluation set (data/eval) and the eval metrics — no models needed."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "eval.py"
spec = importlib.util.spec_from_file_location("cadis_eval", SCRIPT)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

TYPES = {"single", "numeric", "cross_passage", "cross_document", "comparison", "unanswerable", "section"}


def test_every_evidence_quote_exists_and_ids_are_unique():
    docs, questions, collection = ev.load_eval()        # raises if a quote is missing
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))
    for q in questions:
        assert q["type"] in TYPES
        assert bool(q["answers"]) == (q["type"] != "unanswerable")
        for s, e in q["spans"]:
            assert collection[s:e] in (ev_["quote"] for ev_ in q["evidence"])


def test_all_question_types_are_covered():
    _, questions, _ = ev.load_eval()
    assert {q["type"] for q in questions} == TYPES


@pytest.mark.parametrize("pred, gold, em", [
    ("$2.5 billion", "$2.5 billion", 1.0),
    ("The State of New York", "State of New York", 1.0),
    ("1240", "1,240", 1.0),
    ("14.2 months", "142 months", 0.0),
    ("", "Tim Cook", 0.0),
])
def test_exact_match(pred, gold, em):
    assert ev.best_em_f1(pred, [gold])[0] == em


def test_f1_partial_credit_and_abstention():
    assert 0 < ev.best_em_f1("CEO Tim Cook said", ["Tim Cook"])[1] < 1
    assert ev.best_em_f1("", []) == (1.0, 1.0)          # correct abstention
    assert ev.best_em_f1("Boston", []) == (0.0, 0.0)    # answered an unanswerable question


def test_section_lookup_targets_exist():
    """Every section named in section_lookup.jsonl is a real section of its document."""
    import json

    from cadis.ingest.cleaning import clean_blocks
    from cadis.ingest.parsers import parse_document
    from cadis.ingest.sections import build_structure

    lookup = ev.EVAL_DIR / "section_lookup.jsonl"
    items = [json.loads(line) for line in lookup.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert items
    for item in items:
        path = ev.EVAL_DIR / "documents" / f"{item['doc']}.txt"
        parsed = parse_document(path.name, path.read_bytes())
        st = build_structure(clean_blocks(parsed.blocks, parsed.kind, parsed.pages), parsed.kind, item["doc"])
        assert item["section"] in [s.path for s in st.sections], item["id"]
