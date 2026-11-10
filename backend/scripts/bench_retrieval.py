"""Retrieval latency and HNSW accuracy on a large collection (Phase 2 done-when).

    python backend/scripts/eval.py --data-dir var/bench --distractors 732 --no-answers   # build once
    python backend/scripts/bench_retrieval.py --data-dir var/bench --threads 2

* **Latency** — every eval question goes through ``retrieve`` (hybrid search,
  RRF, cross-encoder re-rank, section filter); median and p95 per stage.
  ``--threads 2`` limits PyTorch to two threads, roughly a free Hugging Face
  Space (2 vCPU). Each configuration in ``--candidates`` is the number of
  chunks the cross-encoder re-ranks.
* **HNSW vs exact** (ADR-012) — the same query vectors searched in ChromaDB
  and with a brute-force NumPy scan; reported as the share of the exact top-k
  that HNSW also returned.

Uses the settings of the store (``CADIS_EMB_MODEL`` must match how it was built).
"""

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--candidates", default="20,30", help="comma-separated re-rank sizes")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--save", help="write data/eval/results/NAME.json")
    args = ap.parse_args()

    os.environ["CADIS_DATA_DIR"] = args.data_dir
    os.environ["CADIS_RUN_WORKER"] = "false"
    import torch
    torch.set_num_threads(args.threads)

    from sqlalchemy import func, select

    from cadis.config import get_settings
    from cadis.index.exact import ExactIndex, overlap_at_k
    from cadis.index.vector_store import get_vector_store
    from cadis.models.embedding import embed_query
    from cadis.retrieval.retrieve import retrieve
    from cadis.storage.db import session_scope
    from cadis.storage.tables import Chunk, Collection

    with session_scope() as s:
        allowed = list(s.scalars(select(Collection.id)))
        n_chunks = s.scalar(select(func.count(Chunk.id)))
    questions = [json.loads(line)["question"] for line in
                 (ROOT / "data" / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
                 if line.strip()]
    s = get_settings()
    print(f"{n_chunks} chunks · {len(questions)} questions · torch threads {args.threads} · "
          f"embedding {s.emb_model} · re-ranker {s.rerank_model}")

    retrieve("warm up the models", allowed)                     # load models, fill caches
    report = {"chunks": n_chunks, "threads": args.threads, "embedding": s.emb_model, "latency": {}}
    for n in [int(x) for x in args.candidates.split(",")]:
        s.rerank_candidates = n
        totals, stages = [], {}
        for _ in range(args.repeat):
            for q in questions:
                t0 = time.perf_counter()
                r = retrieve(q, allowed)
                totals.append((time.perf_counter() - t0) * 1000)
                for k, v in r.timings_ms.items():
                    stages.setdefault(k, []).append(v)
        totals.sort()
        row = {"median_ms": round(statistics.median(totals)), "p95_ms": round(totals[int(0.95 * len(totals))]),
               "stages_median_ms": {k: round(statistics.median(v), 1) for k, v in stages.items() if k != "total"}}
        report["latency"][f"rerank_{n}"] = row
        print(f"re-rank {n:>2} candidates: median {row['median_ms']} ms, p95 {row['p95_ms']} ms  "
              + "  ".join(f"{k} {v:.0f}" for k, v in row["stages_median_ms"].items()))

    store = get_vector_store()
    t0 = time.perf_counter()
    exact = ExactIndex.from_store(store)
    load_s = time.perf_counter() - t0
    overlaps = {10: [], 50: []}
    t_hnsw, t_exact = [], []
    for q in questions:
        v = embed_query(q)
        a0 = time.perf_counter()
        approx = store.search(v, allowed, 50)
        a1 = time.perf_counter()
        truth = exact.search(v, allowed, 50)
        a2 = time.perf_counter()
        t_hnsw.append((a1 - a0) * 1000)
        t_exact.append((a2 - a1) * 1000)
        for k in overlaps:
            overlaps[k].append(overlap_at_k(approx, truth, k))
    report["hnsw_vs_exact"] = {f"overlap@{k}": round(statistics.mean(v), 4) for k, v in overlaps.items()}
    report["hnsw_vs_exact"].update({"hnsw_median_ms": round(statistics.median(t_hnsw), 1),
                                    "exact_median_ms": round(statistics.median(t_exact), 1),
                                    "exact_load_s": round(load_s, 1)})
    h = report["hnsw_vs_exact"]
    print(f"HNSW vs exact search: overlap@10 {h['overlap@10']:.3f}, overlap@50 {h['overlap@50']:.3f}; "
          f"HNSW {h['hnsw_median_ms']} ms vs exact {h['exact_median_ms']} ms per query")

    if args.save:
        path = ROOT / "data" / "eval" / "results" / f"{args.save}.json"
        path.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
