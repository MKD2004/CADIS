"""
CADIS latency benchmark — measures what model caching actually buys.

The five model loaders in api_server.py are wrapped in @lru_cache(maxsize=1),
so weights are loaded once per process and reused. This script quantifies that
by timing the two things a request can pay for:

    cold request = model load + inference      (first request to a fresh worker)
    warm request = inference only              (every request after)

What this does NOT measure: the model *download*. On a fresh HuggingFace Spaces
container the weights (~1.5 GB) are fetched over the network on first use,
because the Dockerfile deliberately skips pre-downloading them (doing so blew
past the Spaces build timeout). That download dominates a true cold start in
deployment and is bandwidth-dependent, so it is not reproducible as a number —
run this locally and you are measuring load-from-disk, with weights already in
~/.cache/huggingface.

Usage:
    python benchmark.py              # default document sizes
    python benchmark.py 200 800      # specific word counts
"""

import sys
import time

import api_server as A

SENTENCE = (
    "The agreement between Acme Corporation and Globex was signed in Berlin "
    "on March 14 2023 for 4.2 million dollars covering logistics and "
    "compliance obligations. Maria Chen announced the outcome at the Geneva "
    "summit in April. "
)

DEFAULT_SIZES = (100, 200, 400, 800, 1600)


def make_doc(n_words):
    return " ".join((SENTENCE * (n_words // 10 + 20)).split()[:n_words])


def time_model_load():
    """Time one cold fill of every lru_cache, then prove the cache hits."""
    loaders = (A.get_nlp, A.get_embedder, A.get_ner_pipe,
               A.get_qa_pipe, A.get_summarizer)

    t0 = time.perf_counter()
    for fn in loaders:
        fn()
    cold = time.perf_counter() - t0

    t0 = time.perf_counter()
    for fn in loaders:
        fn()
    warm = time.perf_counter() - t0

    return cold, warm


class _Req:
    """Stands in for the pydantic ProcessRequest body."""
    def __init__(self, text):
        self.text = text


def time_inference(n_words, repeats=2):
    """Median-ish warm inference: discard the first run, keep the best of the rest."""
    req = _Req(make_doc(n_words))
    A.process(req)                      # discard — absorbs any lazy init
    return min(_timed(req) for _ in range(repeats))


def _timed(req):
    t0 = time.perf_counter()
    A.process(req)
    return time.perf_counter() - t0


def main():
    sizes = [int(a) for a in sys.argv[1:]] or list(DEFAULT_SIZES)

    print("\nCADIS latency benchmark")
    print("=" * 62)

    load_cold, load_warm = time_model_load()
    print(f"model load, lru_cache MISS (weights on local disk) : {load_cold:7.2f}s")
    print(f"model load, lru_cache HIT                          : {load_warm:7.6f}s")
    speedup = load_cold / load_warm if load_warm else float("inf")
    print(f"  -> caching removes {load_cold:.1f}s of load from every request "
          f"after the first ({speedup:,.0f}x on the load step alone)")

    print("\nper-request latency by document size")
    print("-" * 62)
    print(f"{'words':>7} {'warm (infer)':>13} {'cold (load+infer)':>18} {'ratio':>7}")
    for n in sizes:
        infer = time_inference(n)
        cold = load_cold + infer
        print(f"{n:>7} {infer:>12.2f}s {cold:>17.2f}s {cold / infer:>6.2f}x")

    print("-" * 62)
    print("Ratio is highest on short documents (load dominates) and falls as")
    print("inference grows. It is a property of the document, not a single")
    print("headline number: quote it with the document size attached.\n")


if __name__ == "__main__":
    main()
