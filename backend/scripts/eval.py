"""CADIS evaluation — measures retrieval and answer quality on data/eval.

    python backend/scripts/eval.py                       # V2 pipeline (default)
    python backend/scripts/eval.py --save phase2         # also write data/eval/results/phase2.json
    python backend/scripts/eval.py --pipeline v1         # the Phase 0 (V1) pipeline
    python backend/scripts/eval.py --no-answers          # retrieval only (fast; for comparisons)
    python backend/scripts/eval.py --mode dense --no-rerank --no-sections   # ablations

Model and size settings come from the usual environment variables, e.g.
``CADIS_EMB_MODEL=BAAI/bge-small-en-v1.5 CADIS_CHUNK_TOKENS=384``.

Pipelines
---------
* **v2** — every document is ingested through the real Phase 1 pipeline
  (parse → clean → section tree → chunks → SQLite/FTS5/ChromaDB) into a
  temporary data folder, then each question goes through ``retrieve``
  (hybrid search, RRF, re-rank, section soft filter), ``expand`` and the
  extractive span finder over the expanded contexts.
* **v1** — all documents joined into one text, split into V1 passages and
  ranked with the embedding model; the V1 extractive engine answers. This is
  how ``results/phase0.json`` was produced.

Metrics
-------
* Retrieval: a question's evidence counts as found at k if every evidence
  quote lies inside the top-k chunks (passages for v1). recall@1/3/6/8 and
  MRR (first chunk holding any evidence). v2 ranks the top 20 only.
* Section-targeted questions are also retrieved with the section filter
  switched off, to show what the filter adds (CADIS V2 Phase 2 done-when).
* Section lookup (``section_lookup.jsonl``, v2 only): questions where the
  section name is the main clue ("What is in the Warranty section of the
  supply agreement?"); reported as "right section in the top 1 / 3", with and
  without the section filter.
* Answers per question type: SQuAD-style Exact Match and token F1 (best over
  the accepted answers); for unanswerable questions, whether no answer was
  given. Numeric, comparison and cross-document questions are expected to
  fail with an extractive engine: they are the targets for Phases 3–4.
* Latency per question (retrieval + answer), median and p95.
"""

import argparse
import json
import os
import re
import statistics
import string
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import numpy as np  # noqa: E402

EVAL_DIR = ROOT / "data" / "eval"
KS = (1, 3, 6, 8)
V2_RANK_DEPTH = 20


# ── data ──────────────────────────────────────────────────────────────────────

def load_eval(eval_dir=EVAL_DIR):
    docs = {p.stem: p.read_text(encoding="utf-8").strip()
            for p in sorted((eval_dir / "documents").glob("*.txt"))}
    questions = [json.loads(line) for line in
                 (eval_dir / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    # One collection text (v1); remember where each document starts.
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


def ranks_from_cover(ordered_cover):
    """ordered_cover: for each ranked item, the set of evidence indexes it
    covers; returns (first rank covering any, rank at which all are covered)."""
    first, all_at, seen = None, None, set()
    for rank, covered in enumerate(ordered_cover, start=1):
        seen |= covered
        if covered and first is None:
            first = rank
        if seen >= ordered_cover.all_needed:
            all_at = rank
            break
    return first, all_at


class _Cover(list):
    all_needed: set


def retrieval_ranks(question, spans, passages, p_vec, embedder):
    """v1: rank of the first passage covering any evidence (1-based, None if
    never) and the smallest k at which *all* evidence is covered."""
    q = np.asarray(embedder.encode([question]))[0]
    pv = np.asarray(p_vec)
    sims = pv @ q / (np.linalg.norm(pv, axis=1) * np.linalg.norm(q) + 1e-12)
    cover = _Cover()
    cover.all_needed = set(range(len(spans)))
    for pi in np.argsort(-sims):
        text, base = passages[pi]
        cover.append({i for i, (s, e) in enumerate(spans) if base <= s and e <= base + len(text)})
    return ranks_from_cover(cover)


# ── v1 run ────────────────────────────────────────────────────────────────────

def run_v1(args):
    from cadis.answer import extractive as ex
    from cadis.models import registry

    docs, questions, collection = load_eval()
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
    info = {"documents": len(docs), "units": len(passages), "unit_name": "passages"}
    return questions, rows, info


# ── v2 run ────────────────────────────────────────────────────────────────────

def _ingest_eval_docs(data_dir, distractors=0, quotes=()):
    """Ingest data/eval/documents (plus ``distractors`` WikiText-2 articles)
    into a fresh V2 store. Returns (allowed collection IDs,
    {doc name: (document_id, cleaned text)}, chunk count)."""
    os.environ["CADIS_DATA_DIR"] = str(data_dir)
    os.environ["CADIS_RUN_WORKER"] = "false"
    from cadis.config import get_settings
    get_settings.cache_clear()

    from sqlalchemy import func, select

    from cadis.ingest.pipeline import HANDLERS
    from cadis.ingest.service import upload
    from cadis.jobs.worker import Worker
    from cadis.storage import repositories
    from cadis.storage.db import init_db, session_scope
    from cadis.storage.tables import Chunk, Collection, Document, DocumentText

    init_db()
    names = {}
    eval_files = {p.name: p.stem for p in (EVAL_DIR / "documents").glob("*.txt")}
    with session_scope() as s:
        existing = s.scalars(select(Collection).where(Collection.name == "eval")).first()
        if existing is not None:                      # --data-dir reuse: already ingested
            for doc in repositories.list_documents(s, existing.id, [existing.id]):
                if doc.filename in eval_files:
                    names[doc.id] = eval_files[doc.filename]
            col_id = existing.id
        else:
            col_id = None
    if col_id is None:
        with session_scope() as s:
            tenant = get_settings().default_tenant
            repositories.ensure_tenant(s, tenant)
            col_id = repositories.create_collection(s, tenant, "eval").id
            for p in sorted((EVAL_DIR / "documents").glob("*.txt")):
                names[upload(s, col_id, p.name, p.read_bytes()).document_id] = p.stem
            if distractors:
                import wikitext
                n = 0
                for title, text in wikitext.load_articles():
                    if n >= distractors:
                        break
                    if any(q in text for q in quotes):      # a distractor must never hold evidence
                        continue
                    slug = re.sub(r"\W+", "_", title)[:40]
                    upload(s, col_id, f"wiki_{n:04d}_{slug}.txt", text.encode("utf-8"))
                    n += 1
        Worker(HANDLERS, "eval").drain(max_jobs=len(names) + distractors + 5)
    out = {}
    with session_scope() as s:
        for doc in s.scalars(select(Document)):
            if doc.status != "READY":
                raise SystemExit(f"ingest failed for {doc.filename}: {doc.error}")
            if doc.id not in names:
                continue
            text = s.scalar(select(DocumentText.text).where(
                DocumentText.document_id == doc.id, DocumentText.version == doc.current_version))
            out[names[doc.id]] = (doc.id, text)
        n_chunks = s.scalar(select(func.count(Chunk.id)))
        n_docs = s.scalar(select(func.count(Document.id)))
    return [col_id], out, n_chunks, n_docs


def _find(text, quote):
    """Locate a quote in cleaned text (whitespace may differ after cleaning)."""
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    m = re.search(pattern, text)
    return (m.start(), m.end()) if m else None


def _cover(hits, spans):
    cover = _Cover()
    cover.all_needed = set(range(len(spans)))
    for h in hits:
        cover.append({i for i, (doc_id, s, e) in enumerate(spans)
                      if h.document_id == doc_id and h.char_start <= s and e <= h.char_end})
    return cover


def run_v2(args):
    from cadis.answer.extractive import answer_contexts
    from cadis.models import registry
    from cadis.retrieval.expand import expand
    from cadis.retrieval.retrieve import Retrieval, retrieve

    _, questions, _ = load_eval()
    tmp = args.data_dir or tempfile.mkdtemp(prefix="cadis-eval-")
    t_ingest = time.perf_counter()
    quotes = [ev["quote"] for q in questions for ev in q["evidence"]]
    allowed, docs, n_chunks, n_docs = _ingest_eval_docs(tmp, args.distractors, quotes)
    ingest_s = time.perf_counter() - t_ingest
    tokenizer = model = None
    if not args.no_answers:
        tokenizer, model = registry.get_qa_pipe()

    opts = dict(use_sections=not args.no_sections, use_reranker=not args.no_rerank, mode=args.mode)
    rows = []
    for q in questions:
        spans = []
        for ev in q["evidence"]:
            doc_id, text = docs[ev["doc"]]
            found = _find(text, ev["quote"])
            if found is None:
                raise SystemExit(f"{q['id']}: quote not found after cleaning: {ev['quote']!r}")
            spans.append((doc_id, *found))

        t0 = time.perf_counter()
        result = retrieve(q["question"], allowed, k=V2_RANK_DEPTH, **opts)
        t_retrieve = time.perf_counter() - t0
        first = all_at = None
        if spans:
            first, all_at = ranks_from_cover(_cover(result.hits, spans))
        row = {"id": q["id"], "type": q["type"], "question": q["question"],
               "first_rank": first, "all_evidence_rank": all_at,
               "sections_found": [t.phrase for t in result.targets],
               "retrieve_ms": round(t_retrieve * 1000, 1), "timings": result.timings_ms}
        if q["type"] == "section" and opts["use_sections"]:
            plain = retrieve(q["question"], allowed, k=V2_RANK_DEPTH,
                             **{**opts, "use_sections": False})
            row["all_evidence_rank_no_sections"] = ranks_from_cover(_cover(plain.hits, spans))[1]

        prediction, conf, context_hit = "", 0.0, None
        if not args.no_answers:
            t1 = time.perf_counter()
            top = Retrieval(result.question, result.hits[:args.k], result.targets)
            contexts = expand(top, neighbours=args.neighbours)
            ans = answer_contexts(q["question"], [c.text for c in contexts], tokenizer, model)
            prediction, conf = ans["answer"], ans["confidence"]
            context_hit = all(any(c.document_id == d and c.char_start <= s and e <= c.char_end
                                  for c in contexts) for d, s, e in spans) if spans else None
            row["ms"] = round((t_retrieve + time.perf_counter() - t1) * 1000, 1)
        else:
            row["ms"] = row["retrieve_ms"]
        em, f = best_em_f1(prediction, q["answers"])
        row.update({"prediction": prediction, "confidence": conf, "em": em, "f1": round(f, 4),
                    "evidence_in_context": context_hit})
        rows.append(row)
    lookup = []
    lookup_file = EVAL_DIR / "section_lookup.jsonl"
    if lookup_file.exists():
        for line in lookup_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            doc_id = docs[item["doc"]][0]
            ranks = {}
            for label, on in (("with_filter", True), ("without_filter", False)):
                hits = retrieve(item["question"], allowed, k=V2_RANK_DEPTH,
                                **{**opts, "use_sections": on}).hits
                ranks[label] = next((i for i, h in enumerate(hits, 1) if h.document_id == doc_id
                                     and h.section_path == item["section"]), None)
            lookup.append({**item, **ranks})
    info = {"documents": n_docs, "units": n_chunks, "unit_name": "chunks",
            "section_lookup": lookup,
            "ingest_seconds": round(ingest_s, 1), "distractors": n_docs - len(docs)}
    return questions, rows, info


# ── report ────────────────────────────────────────────────────────────────────

def _recall(rows, key, k):
    return round(sum(1 for r in rows if r.get(key) and r[key] <= k) / len(rows), 3) if rows else 0.0


def summarize(rows, info, answers=True):
    with_ev = [r for r in rows if r["type"] != "unanswerable"]
    retrieval = {f"recall@{k}": _recall(with_ev, "all_evidence_rank", k) for k in KS}
    retrieval["mrr"] = round(sum(1 / r["first_rank"] for r in with_ev if r["first_rank"]) / len(with_ev), 3)
    retrieval[f"{info['unit_name']}_in_collection"] = info["units"]

    by_type = defaultdict(list)
    for r in rows:
        by_type[r["type"]].append(r)
    retrieval_by_type = {t: {f"recall@{k}": _recall(rs, "all_evidence_rank", k) for k in (3, 8)}
                         for t, rs in sorted(by_type.items()) if t != "unanswerable"}

    out = {"retrieval": retrieval, "retrieval_by_type": retrieval_by_type}
    if info.get("section_lookup"):
        lk = info["section_lookup"]
        out["section_lookup"] = {
            "n": len(lk),
            **{f"top{k}_{label}": round(sum(1 for r in lk if r[label] and r[label] <= k) / len(lk), 3)
               for k in (1, 3) for label in ("with_filter", "without_filter")},
            "questions": lk,
        }
    sec = [r for r in rows if "all_evidence_rank_no_sections" in r]
    if sec:
        out["section_filter"] = {
            "n": len(sec),
            "recall@8_with_filter": _recall(sec, "all_evidence_rank", 8),
            "recall@8_without_filter": _recall(sec, "all_evidence_rank_no_sections", 8),
            "recall@3_with_filter": _recall(sec, "all_evidence_rank", 3),
            "recall@3_without_filter": _recall(sec, "all_evidence_rank_no_sections", 3),
            "questions_with_sections_found": sum(1 for r in sec if r["sections_found"]),
        }
        non_sec = [r for r in rows if r["type"] != "section"]
        out["section_filter"]["false_triggers_on_other_questions"] = sum(
            1 for r in non_sec if r.get("sections_found"))

    if answers:
        ans = {}
        for t, rs in sorted(by_type.items()):
            if t == "unanswerable":
                ans[t] = {"n": len(rs), "correct_abstain": round(sum(r["prediction"] == "" for r in rs) / len(rs), 3)}
            else:
                ans[t] = {"n": len(rs), "em": round(statistics.mean(r["em"] for r in rs), 3),
                          "f1": round(statistics.mean(r["f1"] for r in rs), 3),
                          "no_answer": round(sum(r["prediction"] == "" for r in rs) / len(rs), 3)}
        answerable = [r for r in rows if r["type"] != "unanswerable"]
        ans["all_answerable"] = {"n": len(answerable),
                                 "em": round(statistics.mean(r["em"] for r in answerable), 3),
                                 "f1": round(statistics.mean(r["f1"] for r in answerable), 3)}
        hits = [r["evidence_in_context"] for r in answerable if r.get("evidence_in_context") is not None]
        if hits:
            ans["evidence_in_answer_context"] = round(sum(hits) / len(hits), 3)
        out["answers"] = ans
    ms = sorted(r["ms"] for r in rows)
    out["latency"] = {"median_ms": round(statistics.median(ms), 1),
                      "p95_ms": round(ms[min(len(ms) - 1, int(0.95 * len(ms)))], 1)}
    return out


def git_state():
    try:
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True).stdout.strip())
        return head + ("+uncommitted" if dirty else "")
    except OSError:
        return "unknown"


def print_report(summary, questions, info, args):
    print(f"\nCADIS eval [{args.pipeline}] — {len(questions)} questions, {info['documents']} documents"
          f"{' (incl. ' + str(info['distractors']) + ' distractors)' if info.get('distractors') else ''}, "
          f"{info['units']} {info['unit_name']}")
    print("=" * 76)
    rt = summary["retrieval"]
    print("Retrieval (all evidence in top-k):  " +
          "  ".join(f"@{k} {rt[f'recall@{k}']:.2f}" for k in KS) + f"  MRR {rt['mrr']:.2f}")
    for t, m in summary["retrieval_by_type"].items():
        print(f"   {t:16} recall@3 {m['recall@3']:.2f}  recall@8 {m['recall@8']:.2f}")
    if "section_filter" in summary:
        sf = summary["section_filter"]
        print(f"Section filter ({sf['n']} section questions): recall@8 {sf['recall@8_with_filter']:.2f} "
              f"with vs {sf['recall@8_without_filter']:.2f} without; recall@3 "
              f"{sf['recall@3_with_filter']:.2f} vs {sf['recall@3_without_filter']:.2f}; "
              f"names found in {sf['questions_with_sections_found']}/{sf['n']}; "
              f"false triggers on other questions: {sf['false_triggers_on_other_questions']}")
    if "section_lookup" in summary:
        lk = summary["section_lookup"]
        print(f"Section lookup ({lk['n']} questions, right section in top 1 / top 3): "
              f"{lk['top1_with_filter']:.2f} / {lk['top3_with_filter']:.2f} with filter vs "
              f"{lk['top1_without_filter']:.2f} / {lk['top3_without_filter']:.2f} without")
    if "answers" in summary:
        print("-" * 76)
        print(f"{'type':16} {'n':>3} {'EM':>6} {'F1':>6} {'no answer':>10}")
        for t, m in summary["answers"].items():
            if t == "evidence_in_answer_context":
                continue
            if t == "unanswerable":
                print(f"{t:16} {m['n']:>3} {'':>6} {'':>6} {m['correct_abstain']:>10.2f}  (correct when 1.00)")
            else:
                print(f"{t:16} {m['n']:>3} {m['em']:>6.2f} {m['f1']:>6.2f} {m.get('no_answer', 0):>10.2f}")
        if "evidence_in_answer_context" in summary["answers"]:
            print(f"evidence inside the answer contexts: {summary['answers']['evidence_in_answer_context']:.2f}")
    print("-" * 76)
    print(f"Latency per question: median {summary['latency']['median_ms']:.0f} ms, "
          f"p95 {summary['latency']['p95_ms']:.0f} ms")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--save", metavar="NAME", help="write data/eval/results/NAME.json")
    ap.add_argument("--show", action="store_true", help="print every question's result")
    ap.add_argument("--pipeline", choices=("v1", "v2"), default="v2")
    ap.add_argument("--mode", choices=("hybrid", "dense", "keyword"), default="hybrid")
    ap.add_argument("--no-rerank", action="store_true")
    ap.add_argument("--no-sections", action="store_true")
    ap.add_argument("--no-answers", action="store_true", help="retrieval metrics only")
    ap.add_argument("--k", type=int, default=8, help="chunks given to the answer step")
    ap.add_argument("--neighbours", type=int, default=None, help="small-to-big neighbours")
    ap.add_argument("--data-dir", help="ingest into / reuse this folder (skip re-ingesting "
                    "between runs; use a new folder when the model or chunk size changes)")
    ap.add_argument("--distractors", type=int, default=0,
                    help="add N WikiText-2 articles to the collection (harder retrieval; ~19 chunks each)")
    args = ap.parse_args()

    if args.pipeline == "v1":
        args.no_answers = False
        questions, rows, info = run_v1(args)
    else:
        questions, rows, info = run_v2(args)
    summary = summarize(rows, info, answers=not args.no_answers)
    print_report(summary, questions, info, args)

    if args.show:
        print()
        for r in rows:
            mark = "ok " if r["em"] else ("~  " if r["f1"] > 0 else "x  ")
            extra = f" sec={r['sections_found']}" if r.get("sections_found") else ""
            print(f"{mark}{r['id']:5} {r['type']:15} {r['prediction'][:38]!r:42} "
                  f"all@={r['all_evidence_rank']}{extra}")

    if args.save:
        from cadis.config import get_settings
        s = get_settings()
        settings = {"pipeline": args.pipeline}
        if args.pipeline == "v2":
            settings.update({"mode": args.mode, "rerank": not args.no_rerank,
                             "rerank_model": s.rerank_model, "sections": not args.no_sections,
                             "chunk_tokens": s.chunk_tokens, "chunk_overlap": s.chunk_overlap_tokens,
                             "retrieve_k": s.retrieve_k, "rerank_candidates": s.rerank_candidates,
                             "answer_k": args.k,
                             "neighbours": s.expand_neighbours if args.neighbours is None else args.neighbours,
                             "ingest_seconds": info.get("ingest_seconds"),
                             "distractors": info.get("distractors")})
        out = {"name": args.save, "git": git_state(), "date": time.strftime("%Y-%m-%d"),
               "models": {"embedding": s.emb_model, "qa": s.qa_model}, "settings": settings,
               "summary": summary, "questions": rows}
        path = EVAL_DIR / "results" / f"{args.save}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nsaved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
