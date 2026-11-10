"""Module 2 — sentence embeddings for the visualisation page.

V1 sent an n × n similarity matrix and a row per sentence, so the response
grew with the square of the document (14 MB at ~10,400 words — more than
the browser's localStorage holds). Now:

* the matrix covers only the first `sim_matrix_max` sentences,
* the most similar pairs are still found across *all* sentences, in blocks,
  so memory stays bounded,
* the 2-D plot uses a PCA projection instead of the first two raw vector
  dimensions, which did not reflect similarity at all.
"""

import numpy as np

from cadis.config import get_settings

_BLOCK = 512


def _unit_rows(vecs):
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def top_similar_pairs(vecs, k):
    """The k most cosine-similar pairs (i < j) over all rows, computed in
    row blocks so an n × n matrix is never held in memory.
    Returns [(score, i, j)] sorted by score, then i, then j."""
    n = len(vecs)
    if n < 2 or k <= 0:
        return []
    unit = _unit_rows(np.asarray(vecs, dtype=np.float64))
    best = []
    for r0 in range(0, n, _BLOCK):
        block = unit[r0:r0 + _BLOCK] @ unit.T                      # (b, n)
        rows = np.arange(r0, r0 + block.shape[0])[:, None]
        block[np.arange(n)[None, :] <= rows] = -np.inf             # keep j > i only
        flat = block.ravel()
        take = min(k, int(np.isfinite(flat).sum()))
        if take == 0:
            continue
        idx = np.argpartition(-flat, take - 1)[:take]
        for f in idx:
            i, j = divmod(int(f), n)
            best.append((float(flat[f]), r0 + i, j))
        # Round the sort key so float noise (1.0 vs 0.9999999999999998) does not
        # reorder exact ties; ties then keep document order, as in V1.
        best = sorted(best, key=lambda t: (-round(t[0], 6), t[1], t[2]))[:k]
    return best


def pca_2d(vecs):
    """Project rows onto their first two principal components.
    Signs are fixed (largest-magnitude coordinate positive) so the plot does
    not flip between runs."""
    x = np.asarray(vecs, dtype=np.float64)
    n = len(x)
    if n == 0:
        return np.zeros((0, 2))
    if n == 1:
        return np.zeros((1, 2))
    centred = x - x.mean(axis=0)
    u, s, _ = np.linalg.svd(centred, full_matrices=False)
    coords = np.zeros((n, 2))
    m = min(2, len(s))
    coords[:, :m] = u[:, :m] * s[:m]
    for c in range(m):
        if coords[np.argmax(np.abs(coords[:, c])), c] < 0:
            coords[:, c] *= -1
    return coords


def run_embeddings(sentences: list, embedder):
    from sklearn.metrics.pairwise import cosine_similarity

    s = get_settings()
    valid = [t for t in sentences if len(t) > 15]
    if not valid:
        valid = sentences[:3]

    vecs = np.asarray(embedder.encode(valid))
    m = min(len(valid), s.sim_matrix_max)
    sim = cosine_similarity(vecs[:m]).tolist() if m else []

    pairs = [
        {"a": valid[i], "b": valid[j], "score": round(score, 4)}
        for score, i, j in top_similar_pairs(vecs, s.top_pairs)
    ]

    coords = pca_2d(vecs)
    positions = [
        {"sentence": sent, "x": round(float(coords[i, 0]), 4), "y": round(float(coords[i, 1]), 4)}
        for i, sent in enumerate(valid)
    ]

    p = min(len(valid), s.vector_preview_max)
    return {
        "sentences":         valid,
        "dims":              int(vecs.shape[1]) if vecs.ndim == 2 else 0,
        "total_sentences":   len(valid),
        "matrix_size":       m,
        "similarity_matrix": sim,
        "top_pairs":         pairs,
        "projection":        "pca",
        "positions":         positions,
        "vector_preview": [
            {
                "sentence": valid[i][:60],
                "dim0": round(float(vecs[i, 0]), 4),
                "dim1": round(float(vecs[i, 1]), 4),
                "dim2": round(float(vecs[i, 2]), 4),
                "norm": round(float(np.linalg.norm(vecs[i])), 4),
            }
            for i in range(p)
        ],
    }
