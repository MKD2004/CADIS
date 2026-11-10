"""Tiny stand-ins for the real models so unit tests run in milliseconds.

They mimic only the parts of each model's interface that CADIS uses.
"""

import hashlib
import re

import numpy as np

_TOKEN = re.compile(r"\w+|[^\w\s]")


class FakeTokenizer:
    """One token per word or punctuation mark, with character offsets."""

    model_max_length = 512

    def __call__(self, text, add_special_tokens=True, return_offsets_mapping=False,
                 truncation=False, **_):
        spans = [(m.start(), m.end()) for m in _TOKEN.finditer(text)]
        ids = [hash(text[a:b]) % 30000 for a, b in spans]
        if add_special_tokens:
            ids = [101] + ids + [102]
            spans = [(0, 0)] + spans + [(0, 0)]
        out = {"input_ids": ids}
        if return_offsets_mapping:
            out["offset_mapping"] = spans
        return out


def n_tokens(text):
    return len(_TOKEN.findall(text))


class FakeEmbedder:
    """Deterministic bag-of-words vectors (16-d, unit length)."""

    def __init__(self, max_seq_length=256, dims=16):
        self.max_seq_length = max_seq_length
        self.dims = dims
        self.tokenizer = FakeTokenizer()
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        out = np.zeros((len(texts), self.dims))
        for i, t in enumerate(texts):
            for w in _TOKEN.findall(t.lower()):
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                out[i, h % self.dims] += 1.0
            norm = np.linalg.norm(out[i])
            out[i] = out[i] / norm if norm else out[i]
            if not norm:
                out[i, 0] = 1.0
        return out


class FakeNerPipe:
    """Finds names from a fixed list, but — like the real BERT pipeline on an
    over-long input — only looks at the first `max_tokens` tokens of each text."""

    def __init__(self, names, max_tokens=50):
        self.names = names
        self.max_tokens = max_tokens
        self.tokenizer = FakeTokenizer()
        self.inputs = []

    def _one(self, text):
        spans = [m for m in _TOKEN.finditer(text)][: self.max_tokens]
        visible_end = spans[-1].end() if spans else 0
        ents = []
        for name, group in self.names.items():
            for m in re.finditer(re.escape(name), text):
                if m.end() <= visible_end:
                    ents.append({"entity_group": group, "score": 0.99, "word": name.lower(),
                                 "start": m.start(), "end": m.end()})
        return sorted(ents, key=lambda e: e["start"])

    def __call__(self, texts):
        self.inputs.append(texts)
        if isinstance(texts, str):
            return self._one(texts)
        return [self._one(t) for t in texts]


def blank_nlp():
    """spaCy pipeline with only a sentence splitter (no model download)."""
    import spacy
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    return nlp


def make_pdf(text: str) -> bytes:
    """A minimal one-page PDF containing `text` (ASCII), for parser tests."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


class InMemoryVectorStore:
    """Exact cosine search over a dict — same interface as ChromaVectorStore."""

    def __init__(self):
        self.rows = {}          # id -> (vector, metadata)

    def upsert(self, records):
        for r in records:
            v = np.asarray(r.vector, dtype=float)
            n = np.linalg.norm(v)
            self.rows[r.id] = (v / n if n else v, {
                "document_id": r.document_id, "collection_id": r.collection_id,
                "version": r.version, "page": r.page, "section_id": r.section_id,
                "section_path": r.section_path})

    def search(self, vector, allowed_collection_ids, k, document_ids=None, section_paths=None):
        from cadis.index.vector_store import VectorHit
        allowed = set(allowed_collection_ids)
        if not allowed:
            return []
        q = np.asarray(vector, dtype=float)
        q = q / (np.linalg.norm(q) or 1.0)
        hits = []
        for cid, (v, m) in self.rows.items():
            if m["collection_id"] not in allowed:
                continue
            if document_ids and m["document_id"] not in document_ids:
                continue
            if section_paths and m["section_path"] not in section_paths:
                continue
            hits.append(VectorHit(cid, float(v @ q), m["document_id"], m["section_path"]))
        return sorted(hits, key=lambda h: -h.score)[:k]

    def delete_document(self, document_id, keep_version=None):
        for cid in [c for c, (_, m) in self.rows.items() if m["document_id"] == document_id
                    and (keep_version is None or m["version"] != keep_version)]:
            del self.rows[cid]

    def delete_ids(self, ids):
        for cid in ids:
            self.rows.pop(cid, None)

    def ids_for_document(self, document_id):
        return {c for c, (_, m) in self.rows.items() if m["document_id"] == document_id}

    def all_ids(self):
        return set(self.rows)

    def count(self):
        return len(self.rows)
