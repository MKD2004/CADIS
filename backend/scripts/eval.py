"""CADIS evaluation — measures retrieval and answer quality on data/eval.

    python backend/scripts/eval.py                    # print results
    python backend/scripts/eval.py --save phase0      # also write data/eval/results/phase0.json

What it does
------------
All documents in data/eval/documents are joined into one *collection* text
(V1 can only search one text, so this is how "many documents" is simulated
until Phase 1 adds real collections). Then, for every question in
data/eval/questions.jsonl:

* Retrieval — passages are ranked against the question with the embedding
  model. A question's evidence counts as found at k if every evidence quote
  lies fully inside the top-k passages. Reported: recall@1/3/6 and MRR
  (reciprocal rank of the first passage holding any evidence).
* Answering — the extractive QA engine answers over the collection.
  Reported per question type: Exact Match and token F1 (SQuAD-style
  normalisation, best over the accepted answers), and for unanswerable
  questions whether the system correctly returned no answer.
* Latency — per-question answer time (median and p95).

Numeric, comparison and cross-document questions are *expected* to fail with
V1's extractive engine: they are the targets for Phases 3–4.
"""

import argparse
import json
import re
import statistics
import string
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402

from cadis.answer import extractive as ex  # noqa: E402
from cadis.config import get_settings  # noqa: E402
from cadis.models import registry  # noqa: E402

EVAL_DIR = ROOT / "data" / "eval"
KS = (1, 3, 6)


# ── data ──────────────────────────────────────────────────────────────────────

def load_eval(eval_dir=EVAL_DIR):
    docs = {p.stem: p.read_text(encoding="utf-8").strip()
            for p in sorted((eval_dir / "documents").glob("*.txt"))}
    questions = [json.loads(line) for line in
                 (eval_dir / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    # One collection text; remember where each document starts.
    parts, starts, pos = [], {}, 0
    for name, text in docs.items():
        starts[name] = pos
        parts.append(text)
        pos += len(text) + 2
    collection = "\n\n".join(parts)

    problems = []
    for q in questions:
        q["spans"] = []
        for ev in q["evidence"]:
            i = docs.get(ev["doc"], "").find(ev["quote"])
            if i < 0:
                problems.append(f"{q['id']}: quote not found in {ev['doc']}: {ev['quote']!r}")
                continue
            s = starts[ev["doc"]] + i
            q["spans"].append((s, s + len(ev["quote"])))
    if problems:
        raise SystemExit("Invalid evaluation data:\n  " + "\n  ".join(problems))
    return docs, questions, collection


# ── metrics ───────────────────────────────────────────────────────────────────

_PUNCT_EXCEPT_DOT = set(string.punctuation) - {"."}


def normalize(s):
    """SQuAD-style: lowercase, drop punctuation and articles. Decimal points
    are kept so 14.2 and 142 stay different; thousands commas are dropped so
    "1,240" == "1240"."""
    s = "".join(ch for ch in s.lower() if ch not in _PUNCT_EXCEPT_DOT)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", s)
    return " ".join(s.split())


def f1(pred, gold):
    p, g = normalize(pred).split(), normalize(gold).split()
    common = Counter(p) & Counter(g)
    same = sum(common.values())
    if not p or not g or same == 0:
        return float(p == g)
    precision, recall = same / len(p), same / len(g)
    return 2 * precision * recall / (precision + recall)


def best_em_f1(pred, answers):
    if not answers:
        return float(pred == ""), float(pred == "")
    return (max(float(normalize(pred) == normalize(a)) for a in answers),
            max(f1(pred, a) for a in answers))


def retrieval_ranks(question, spans, passages, p_vec, embedder):
    """Rank of the first passage covering any evidence (1-based, None if never),
    and the smallest k at which *all* evidence is covered (None if never)."""
    q = np.asarray(embedder.encode([question]))[0]
    pv = np.asarray(p_vec)
    sims = pv @ q / (np.linalg.norm(pv, axis=1) * np.linalg.norm(q) + 1e-12)
    order = np.argsort(-sims)

    def covers(pi, span):
        text, base = passages[pi]
        return base <= span[0] and span[1] <= base + len(text)

    first, all_at, remaining = None, None, set(range(len(spans)))
    for rank, pi in enumerate(order, start=1):
        hit = {i for i in remaining if covers(pi, spans[i])}
        if hit and first is None:
            first = rank
        remaining -= hit
        if not remaining:
            all_at = rank
            break
    return first, all_at


# ── run ───────────────────────────────────────────────────────────────────────

def run(eval_dir=EVAL_DIR):
    docs, questions, collection = load_eval(eval_dir)
    embedder = registry.get_embedder()
    tokenizer, model = registry.get_qa_pipe()
    passages, p_vec = ex.passage_cache.get(collection, embedder)

    rows = []
    for q in questions:
        first = all_at = None
        if q["spans"]:
            first, all_at = retrieval_ranks(q["question"], q["spans"], passages, p_vec, embedder)
        t0 = time.perf_counter()
        r = ex.answer_question(q["question"], collection, tokenizer, model, embedder)
        ms = (time.perf_counter() - t0) * 1000
        em, f = best_em_f1(r["answer"], q["answers"])
        rows.append({"id": q["id"], "type": q["type"], "question": q["question"],
                     "prediction": r["answer"], "confidence": r["confidence"],
                     "em": em, "f1": round(f, 4), "first_rank": first,
                     "all_evidence_rank": all_at, "ms": round(ms, 1)})
    return docs, questions, collection, passages, rows


def summarize(rows, n_passages):
    with_ev = [r for r in rows if r["type"] != "unanswerable"]
    retrieval = {f"recall@{k}": round(sum(1 for r in with_ev if r["all_evidence_rank"] and
                                          r["all_evidence_rank"] <= k) / len(with_ev), 3) for k in KS}
    retrieval["mrr"] = round(sum(1 / r["first_rank"] for r in with_ev if r["first_rank"]) / len(with_ev), 3)
    retrieval["passages_in_collection"] = n_passages

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    answers = {}
    for t, rs in sorted(by_type.items()):
        if t == "unanswerable":
            answers[t] = {"n": len(rs), "correct_abstain": round(sum(r["prediction"] == "" for r in rs) / len(rs), 3)}
        else:
            answers[t] = {"n": len(rs), "em": round(statistics.mean(r["em"] for r in rs), 3),
                          "f1": round(statistics.mean(r["f1"] for r in rs), 3),
                          "no_answer": round(sum(r["prediction"] == "" for r in rs) / len(rs), 3)}
    answerable = [r for r in rows if r["type"] != "unanswerable"]
    answers["all_answerable"] = {"n": len(answerable),
                                 "em": round(statistics.mean(r["em"] for r in answerable), 3),
                                 "f1": round(statistics.mean(r["f1"] for r in answerable), 3)}
    ms = sorted(r["ms"] for r in rows)
    latency = {"median_ms": round(statistics.median(ms), 1),
               "p95_ms": round(ms[min(len(ms) - 1, int(0.95 * len(ms)))], 1)}
    return {"retrieval": retrieval, "answers": answers, "latency": latency}


def git_state():
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True).stdout.strip())
        return head + ("+uncommitted" if dirty else "")
    except OSError:
        return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--save", metavar="NAME", help="write data/eval/results/NAME.json")
    ap.add_argument("--show", action="store_true", help="print every question's prediction")
    args = ap.parse_args()

    docs, questions, collection, passages, rows = run()
    summary = summarize(rows, len(passages))
    s = get_settings()

    print(f"\nCADIS eval — {len(questions)} questions, {len(docs)} documents "
          f"({len(collection.split())} words), {len(passages)} passages")
    print("=" * 72)
    rt = summary["retrieval"]
    print("Retrieval (all evidence in top-k):  " +
          "  ".join(f"recall@{k} {rt[f'recall@{k}']:.2f}" for k in KS) + f"  MRR {rt['mrr']:.2f}")
    print("-" * 72)
    print(f"{'type':16} {'n':>3} {'EM':>6} {'F1':>6} {'no answer':>10}")
    for t, m in summary["answers"].items():
        if t == "unanswerable":
            print(f"{t:16} {m['n']:>3} {'':>6} {'':>6} {m['correct_abstain']:>10.2f}  (correct when 1.00)")
        else:
            print(f"{t:16} {m['n']:>3} {m['em']:>6.2f} {m['f1']:>6.2f} {m.get('no_answer', 0):>10.2f}")
    print("-" * 72)
    print(f"Latency per question: median {summary['latency']['median_ms']:.0f} ms, "
          f"p95 {summary['latency']['p95_ms']:.0f} ms")

    if args.show:
        print()
        for r in rows:
            mark = "ok " if r["em"] else ("~  " if r["f1"] > 0 else "x  ")
            print(f"{mark}{r['id']:4} {r['type']:15} {r['prediction'][:40]!r:44} rank={r['first_rank']}")

    if args.save:
        out = {
            "name": args.save,
            "git": git_state(),
            "date": time.strftime("%Y-%m-%d"),
            "models": {"embedding": s.emb_model, "qa": s.qa_model},
            "settings": {"passage_tokens": ex.passage_token_limit(registry.get_embedder()),
                         "passage_overlap_tokens": s.passage_overlap_tokens,
                         "qa_max_passages": s.qa_max_passages, "qa_window": s.qa_window,
                         "qa_stride": s.qa_stride},
            "summary": summary,
            "questions": rows,
        }
        path = EVAL_DIR / "results" / f"{args.save}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nsaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
