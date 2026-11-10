"""Extractive QA engine (moved from V1 ``api_server.py``; DECISIONS ADR-024).

Span decoding has to be done properly or the model returns garbage:
  * `end` must come after `start` — an unconstrained argmax over each logit
    vector independently can produce start=CLS(0) and end=last-token, which
    decodes to the entire question+context (this was the original bug).
  * Only *context* tokens are valid answers — question tokens and padding
    must be masked out.
  * SQuAD2 models emit a null answer at the CLS position; a span is only a
    real answer if it outscores that null.
  * Char offsets must come from the offset mapping of the token's own
    sequence, otherwise the frontend highlights the wrong region.
"""

import hashlib
import math
import threading
from collections import OrderedDict

import numpy as np

from cadis.config import get_settings

def passage_token_limit(embedder):
    """Largest passage (in embedding tokens) the embedder can read in full."""
    s = get_settings()
    cap = int(getattr(embedder, "max_seq_length", 256) or 256) - 2   # [CLS] … [SEP]
    return max(16, min(s.passage_tokens, cap))


def _split_passages(text, embedder, max_tokens=None, overlap=None):
    """Split text into overlapping passages measured in the embedding model's
    tokens, keeping each one's char offset into the original document so
    answer spans stay addressable.

    Windows are cut on token boundaries, then shrunk to whole words so no
    passage starts or ends mid-word and none exceeds the limit."""
    s = get_settings()
    max_tokens = passage_token_limit(embedder) if max_tokens is None else max_tokens
    overlap = s.passage_overlap_tokens if overlap is None else overlap
    if not text.strip():
        return []

    # verbose=False: tokenizing the whole document is intentional here (it is
    # only used to measure and cut passages), so the "longer than the maximum
    # sequence length" warning would be misleading.
    enc = embedder.tokenizer(text, add_special_tokens=False,
                             return_offsets_mapping=True, truncation=False, verbose=False)
    offsets = [(a, b) for a, b in enc["offset_mapping"] if b > a]
    if not offsets:
        return []

    passages, step = [], max(1, max_tokens - overlap)
    for start in range(0, len(offsets), step):
        window = offsets[start:start + max_tokens]
        c0, c1 = _snap_inward(text, window[0][0], window[-1][1])
        passages.append((text[c0:c1], c0))
        if start + max_tokens >= len(offsets):
            break
    return passages


def _snap_inward(text, c0, c1):
    """Shrink [c0, c1) so it starts and ends on whole words.

    Shrinking (never growing) keeps the passage within the token limit even
    for number-heavy text, where one "word" like 4,200,000.50 is ~7 tokens.
    A word cut at a window edge is still covered whole by the neighbouring
    passage, because passages overlap by more tokens than a word has.
    A single word longer than the whole window is returned as cut."""
    a, b = c0, c1
    if a > 0 and not text[a - 1].isspace():          # starts mid-word → next word
        while a < b and not text[a].isspace():
            a += 1
        while a < b and text[a].isspace():
            a += 1
    if b < len(text) and not text[b].isspace():      # ends mid-word → previous word
        while b > a and not text[b - 1].isspace():
            b -= 1
        while b > a and text[b - 1].isspace():
            b -= 1
    return (a, b) if b > a else (c0, c1)


def _embed_passages(passages, embedder):
    """Encode passages once so a multi-question request doesn't re-encode the
    same document per question — that was ~0.5s of wasted MiniLM work per
    question on a 1700-word document."""
    if not passages:
        return None
    return embedder.encode([p for p, _ in passages])


class _PassageCache:
    """Small LRU of (passages, vectors) per document text and embedder.

    /api/qa-ask receives the whole document with every question; without
    this, every custom question re-split and re-embedded it. /api/process
    fills the cache too, so the first follow-up question is already warm."""

    def __init__(self):
        self._items = OrderedDict()
        self._lock = threading.Lock()

    def get(self, text, embedder):
        key = (id(embedder), hashlib.sha256(text.encode("utf-8")).hexdigest())
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key]
        passages = _split_passages(text, embedder)
        value = (passages, _embed_passages(passages, embedder))
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > max(1, get_settings().passage_cache_size):
                self._items.popitem(last=False)
        return value

    def clear(self):
        with self._lock:
            self._items.clear()

    def __len__(self):
        return len(self._items)


passage_cache = _PassageCache()


def _select_passages(question, passages, embedder, k=None, p_vec=None):
    """Semantic retrieval — rank passages against the question and keep the
    top-k, in document order. Keeps long documents answerable without running
    the QA model over every window."""
    k = get_settings().qa_max_passages if k is None else k
    if len(passages) <= k:
        return passages

    from sklearn.metrics.pairwise import cosine_similarity
    q_vec = embedder.encode([question])
    if p_vec is None:
        p_vec = _embed_passages(passages, embedder)
    sims = cosine_similarity(q_vec, p_vec)[0]
    keep = sorted(int(i) for i in np.argsort(-sims)[:k])
    return [passages[i] for i in keep]


def _merge_passages(doc, passages):
    """Merge retrieved passages that are adjacent or overlapping in the document
    into contiguous blocks.

    Retrieval ranks at passage granularity, but one passage is shorter than
    the QA window, so feeding passages individually meant the sliding window
    never overflowed and the stride never did anything. Merging first means a
    retrieved region is one long context, so the window with its stride
    genuinely tiles it, and an answer straddling two adjacent passages is
    recoverable instead of being cut at the seam."""
    if not passages:
        return []

    spans = [[base, base + len(p)] for p, base in passages]
    merged = [spans[0]]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:          # contiguous or overlapping
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(doc[s:e], s) for s, e in merged]


def _trim_span(text, start, end):
    """Shrink a char span off surrounding whitespace/punctuation so the
    answer and its highlight stay aligned."""
    while start < end and (text[start].isspace() or text[start] in ",.;:!?)]}\"'"):
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ",;:([{\"'"):
        end -= 1
    return start, end


def _best_span(question, passages, tokenizer, model):
    """Run one batched forward pass over every sliding window of every passage
    and return (best, null_score) where best = (score, char_start, char_end)."""
    import torch

    s = get_settings()
    enc = tokenizer(
        [question] * len(passages),
        [p for p, _ in passages],
        truncation="only_second",
        max_length=s.qa_window,
        stride=s.qa_stride,
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding=True,
        return_tensors="pt",
    )

    n_features  = enc["input_ids"].shape[0]
    seq_ids     = [enc.sequence_ids(i) for i in range(n_features)]
    offsets     = enc["offset_mapping"]
    sample_map  = enc["overflow_to_sample_mapping"].tolist()

    model_inputs = {
        k: v for k, v in enc.items()
        if k in ("input_ids", "attention_mask", "token_type_ids")
    }
    with torch.no_grad():
        out = model(**model_inputs)

    best, null_score = None, None

    for i in range(n_features):
        s_log, e_log = out.start_logits[i], out.end_logits[i]

        # Null (no-answer) score lives at CLS. Across windows we take the
        # lowest — i.e. the window most convinced an answer exists.
        ns = float(s_log[0]) + float(e_log[0])
        null_score = ns if null_score is None else min(null_score, ns)

        # Only context tokens (sequence id 1) are valid answer positions.
        ctx = {j for j, sid in enumerate(seq_ids[i]) if sid == 1}
        if not ctx:
            continue

        k = min(s.qa_top_k, s_log.shape[0])
        s_cands = [int(x) for x in torch.topk(s_log, k).indices.tolist() if x in ctx]
        e_cands = [int(x) for x in torch.topk(e_log, k).indices.tolist() if x in ctx]

        base = passages[sample_map[i]][1]
        for st in s_cands:
            for en in e_cands:
                if en < st or en - st + 1 > s.qa_max_answer_tokens:
                    continue
                score = float(s_log[st]) + float(e_log[en])
                if best is None or score > best[0]:
                    best = (
                        score,
                        int(offsets[i][st][0]) + base,
                        int(offsets[i][en][1]) + base,
                    )

    return best, null_score


def answer_question(question, text, tokenizer, model, embedder,
                    passages=None, p_vec=None):
    """Answer one question against a document. Returns an empty answer when the
    model is more confident there is no answer than in any candidate span."""
    question = (question or "").strip()
    # Offsets are computed on the stripped text but returned relative to the
    # text the caller sent, so a client highlighting its own copy of the
    # document lines up even when that copy has leading whitespace.
    raw = text or ""
    text = raw.strip()
    lead = len(raw) - len(raw.lstrip())
    empty = {"question": question, "answer": "", "confidence": 0.0, "start": 0, "end": 0}
    if not question or not text:
        return empty

    if passages is None:
        passages, p_vec = passage_cache.get(text, embedder)
    passages = _select_passages(question, passages, embedder, p_vec=p_vec)
    # Merge before windowing so the sliding window actually tiles the
    # retrieved region rather than seeing one short passage at a time.
    blocks = _merge_passages(text, passages)
    if not blocks:
        return empty

    best, null_score = _best_span(question, blocks, tokenizer, model)
    if best is None:
        return empty

    score, char_start, char_end = best
    margin = score - (null_score if null_score is not None else 0.0)

    char_start, char_end = _trim_span(text, char_start, char_end)
    answer = text[char_start:char_end]

    # margin > 0 means the span beat the model's own no-answer prediction.
    if margin <= 0 or not answer:
        return empty

    return {
        "question":   question,
        "answer":     answer,
        "confidence": round(1.0 / (1.0 + math.exp(-margin)), 4),
        "start":      char_start + lead,
        "end":        char_end + lead,
    }


def answer_contexts(question, contexts, tokenizer, model):
    """V2: answer over retrieved contexts (texts of possibly different
    documents). Returns {"answer", "confidence", "context", "start", "end"}
    with offsets local to ``contexts[context]``, or an empty answer.

    Contexts are laid out in one virtual coordinate space with a gap between
    them, so the shared span decoder can be reused and a span never runs from
    one context into the next."""
    empty = {"answer": "", "confidence": 0.0, "context": None, "start": 0, "end": 0}
    question = (question or "").strip()
    texts = [t for t in contexts if t and t.strip()]
    if not question or not texts:
        return empty
    bases, pos = [], 0
    for t in contexts:
        bases.append(pos)
        pos += len(t or "") + 1000
    blocks = [(t, b) for t, b in zip(contexts, bases) if t and t.strip()]

    best, null_score = _best_span(question, blocks, tokenizer, model)
    if best is None:
        return empty
    score, start, end = best
    idx = max(i for i, b in enumerate(bases) if b <= start)
    text, base = contexts[idx], bases[idx]
    s, e = _trim_span(text, start - base, min(end - base, len(text)))
    margin = score - (null_score if null_score is not None else 0.0)
    if margin <= 0 or e <= s:
        return empty
    return {"answer": text[s:e], "confidence": round(1.0 / (1.0 + math.exp(-margin)), 4),
            "context": idx, "start": s, "end": e}


PRESET_QUESTIONS = [
    "Who is the main person mentioned?",
    "What organization is involved?",
    "Where did the event take place?",
    "When did this happen?",
    "What was the amount of money involved?",
    "Who made the announcement?",
    "What was the outcome?",
]


def run_qa(text: str, qa_pipe, embedder):
    """The QA module of /api/process: answer the preset questions."""
    tokenizer, model = qa_pipe
    # Split and embed once, then reuse for every question — only the question
    # vector changes per question, so re-encoding the document was pure waste.
    passages, p_vec = passage_cache.get(text, embedder)

    results = []
    for q in PRESET_QUESTIONS:
        try:
            results.append(answer_question(q, text, tokenizer, model, embedder,
                                           passages, p_vec))
        except Exception:
            results.append({"question": q, "answer": "", "confidence": 0.0, "start": 0, "end": 0})

    answered = [r for r in results if r["answer"]]
    avg_conf = round(
        sum(r["confidence"] for r in answered) / len(answered), 3
    ) if answered else 0.0

    return {
        "results": results,
        "stats": {
            "answered":      len(answered),
            "total":         len(PRESET_QUESTIONS),
            "avg_confidence": avg_conf,
        },
    }
