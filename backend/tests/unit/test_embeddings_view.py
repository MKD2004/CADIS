import numpy as np
import pytest

from cadis.analysis import embeddings_view as ev
from fakes import FakeEmbedder


def _brute_force_pairs(vecs, k):
    unit = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    sims = unit @ unit.T
    pairs = [(float(sims[i, j]), i, j) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    return sorted(pairs, key=lambda t: (-round(t[0], 6), t[1], t[2]))[:k]


@pytest.mark.parametrize("n, block", [(2, 512), (30, 512), (30, 7), (101, 16)])
def test_top_pairs_match_brute_force(monkeypatch, n, block):
    monkeypatch.setattr(ev, "_BLOCK", block)
    vecs = np.random.default_rng(n).normal(size=(n, 8))
    got = ev.top_similar_pairs(vecs, k=5)
    want = _brute_force_pairs(vecs, 5)
    assert [(i, j) for _, i, j in got] == [(i, j) for _, i, j in want]
    assert np.allclose([s for s, _, _ in got], [s for s, _, _ in want])


def test_top_pairs_ties_keep_document_order():
    vecs = np.array([[1.0, 0], [1.0, 0], [1.0, 0], [0, 1.0]])
    assert [(i, j) for _, i, j in ev.top_similar_pairs(vecs, 3)] == [(0, 1), (0, 2), (1, 2)]


def test_top_pairs_small_inputs():
    assert ev.top_similar_pairs(np.ones((1, 3)), 5) == []
    assert len(ev.top_similar_pairs(np.eye(3), 10)) == 3       # only 3 pairs exist


def test_pca_matches_svd_projection_and_is_sign_stable():
    x = np.random.default_rng(0).normal(size=(40, 10))
    coords = ev.pca_2d(x)
    c = x - x.mean(axis=0)
    _, _, vt = np.linalg.svd(c, full_matrices=False)
    expected = c @ vt[:2].T
    assert np.allclose(np.abs(coords), np.abs(expected))
    assert np.allclose(coords, ev.pca_2d(x))                   # deterministic
    for col in range(2):
        assert coords[np.argmax(np.abs(coords[:, col])), col] > 0


@pytest.mark.parametrize("n", [0, 1, 2])
def test_pca_tiny_inputs(n):
    assert ev.pca_2d(np.ones((n, 4))).shape == (n, 2)


def test_response_size_is_bounded(monkeypatch):
    monkeypatch.setenv("CADIS_SIM_MATRIX_MAX", "10")
    monkeypatch.setenv("CADIS_VECTOR_PREVIEW_MAX", "12")
    sentences = [f"Sentence number {i} talks about topic {i % 7} in detail." for i in range(200)]
    out = ev.run_embeddings(sentences, FakeEmbedder())
    assert out["total_sentences"] == 200
    assert out["matrix_size"] == 10 and len(out["similarity_matrix"]) == 10
    assert all(len(row) == 10 for row in out["similarity_matrix"])
    assert len(out["vector_preview"]) == 12
    assert len(out["positions"]) == 200 and out["projection"] == "pca"
    assert len(out["top_pairs"]) == 5


def test_short_sentences_fall_back_to_first_three():
    out = ev.run_embeddings(["Hi.", "Ok.", "Yes.", "No."], FakeEmbedder())
    assert out["sentences"] == ["Hi.", "Ok.", "Yes."]
