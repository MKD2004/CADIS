"""Abstractive summarization + extractive key sentences + timeline.

DistilBART accepts 1024 tokens (~750 words). Anything past that is silently
truncated, so every input handed to the model — chunk or reduce step — must
fit. Long documents are summarized chunk-by-chunk (map) and the partial
summaries are condensed (reduce), recursively if they are still too long.

Chunks are sized in *tokens*, not words: word counts under-estimate tokens
for numeric or technical text, and a "400-word" chunk could still overflow.
There is deliberately no cap on the number of chunks — capping it either
dropped the tail of the document or forced chunks past 1024 tokens. Latency
therefore grows linearly with document length.
"""

import math
import re

from cadis.config import get_settings


def _n_tokens(text, tokenizer):
    # Counting only — no model call — so silence the over-length warning.
    return len(tokenizer(text, add_special_tokens=False, verbose=False)["input_ids"])


def _sentence_units(text, tokenizer, limit):
    """Split into sentences, then break any sentence longer than `limit`
    tokens into word windows. PDF extraction often yields long runs with no
    sentence punctuation, which would otherwise become one oversized chunk."""
    units = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        sent = sent.strip()
        if not sent:
            continue
        n = _n_tokens(sent, tokenizer)
        if n <= limit:
            units.append((sent, n))
            continue
        words = sent.split()
        step = max(1, int(len(words) * limit / n * 0.9))
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i + step])
            units.append((piece, _n_tokens(piece, tokenizer)))
    return units


def _sentence_chunks(text, tokenizer, target=None, limit=None):
    """Split into evenly-sized, sentence-aligned chunks that each fit the model.

    Packing greedily leaves a stub final chunk, which then gets the same
    summary budget as a full one and skews coverage toward the end of the
    document. Instead each sentence goes to the chunk its *midpoint* falls in
    when the document is divided into n equal parts, so chunks differ by at
    most about one sentence. A chunk is also closed early if the next
    sentence would push it past `limit`.
    Every sentence lands in exactly one chunk — nothing is dropped.
    """
    s = get_settings()
    target = s.sum_chunk_tokens if target is None else target
    limit = s.sum_max_tokens - 2 if limit is None else limit

    units = _sentence_units(text, tokenizer, limit)
    if not units:
        return []
    total = sum(n for _, n in units)
    n_chunks = max(1, math.ceil(total / target))

    chunks, current, count, done = [], [], 0, 0
    for sent, n in units:
        part = min(n_chunks - 1, int((done + n / 2) * n_chunks / total)) if total else 0
        if current and (part >= len(chunks) + 1 or count + n > limit):
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += n
        done += n
    if current:
        chunks.append(" ".join(current))
    return chunks


def _clean_summary(text):
    """DistilBART leaves detached punctuation and often stops mid-sentence."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    if text and text[-1] not in ".!?":
        cut = max(text.rfind("."), text.rfind("!"), text.rfind("?"))
        if cut > len(text) * 0.5:      # only trim if we keep most of it
            text = text[:cut + 1]
    return text


_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "with", "by", "from",
    "and", "or", "but", "is", "are", "was", "were", "be", "been", "being", "as",
    "that", "this", "these", "those", "it", "its", "will", "shall", "would",
    "can", "could", "may", "might", "has", "have", "had", "not", "no", "than",
}


def _dedupe_sentences(text, threshold=0.5):
    """Drop near-duplicate sentences. Beam search re-states the same fact in
    different words across chunk summaries, which `no_repeat_ngram_size` cannot
    catch because the wording differs. Comparison ignores stopwords — two
    paraphrases share their content words but little of their grammar."""
    def stem(w):
        # Crude singularization so "laws"/"law" count as the same content word.
        return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w

    kept, seen = [], []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        words = {w.lower().strip(".,;:!?\"'") for w in sent.split()}
        content = {stem(w) for w in words if w and w not in _STOPWORDS}
        if not content:
            continue
        if any(len(content & prev) / len(content | prev) > threshold for prev in seen):
            continue
        seen.append(content)
        kept.append(sent.strip())
    return " ".join(kept)


def _generate(text, tokenizer, model, max_len, min_len, beams=4):
    inputs = tokenizer(text, return_tensors="pt", max_length=get_settings().sum_max_tokens,
                       truncation=True)
    ids = model.generate(
        inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
        max_length=max_len,
        min_length=min_len,
        num_beams=beams,
        length_penalty=2.0,
        no_repeat_ngram_size=3,
        early_stopping=True,
    )
    return _clean_summary(tokenizer.decode(ids[0], skip_special_tokens=True))


def summarize_document(text, tokenizer, model):
    s = get_settings()
    words = text.split()

    # Short enough to summarize in one pass.
    if len(words) <= s.sum_short_words and _n_tokens(text, tokenizer) <= s.sum_max_tokens - 2:
        max_len = max(80, min(150, len(words) // 3))
        return _generate(text, tokenizer, model, max_len, min(45, max_len - 20))

    # Map: summarize each chunk with cheap beams.
    chunks = _sentence_chunks(text, tokenizer)
    partials = [_generate(c, tokenizer, model, 110, 40, beams=2) for c in chunks]

    # Reduce: condense the partials into one executive summary.
    joined = _dedupe_sentences(" ".join(partials))
    if len(joined.split()) <= 160:
        return _clean_summary(joined)
    if _n_tokens(joined, tokenizer) <= s.sum_max_tokens - 2:
        return _generate(joined, tokenizer, model, 160, 70)
    # Partials still exceed the input limit (very long documents): recurse.
    # Each round shrinks the text ~4x (<=110 output tokens per ~512 in), so
    # this terminates in a few rounds.
    return summarize_document(joined, tokenizer, model)


def run_summary(text: str, sp_doc, summarizer):
    tokenizer, model = summarizer
    try:
        exec_sum = summarize_document(text, tokenizer, model)
    except Exception as e:
        exec_sum = f"Summarization error: {e}"

    # Extractive key sentences — ranked by entity/verb density normalized for
    # length, then restored to document order so they read as a narrative.
    scored = []
    for idx, sent in enumerate(sp_doc.sents):
        body = sent.text.strip()
        n_words = len(body.split())
        if n_words < 6:
            continue
        ent_score  = len(list(sent.ents)) * 2
        verb_score = sum(1 for t in sent if t.pos_ == "VERB")
        density    = (ent_score + verb_score) / math.sqrt(n_words)
        scored.append((idx, body, density))

    top = sorted(scored, key=lambda x: x[2], reverse=True)[:4]
    key_sents = [body for _, body, _ in sorted(top, key=lambda x: x[0])]

    # Timeline
    timeline = []
    for sent in sp_doc.sents:
        time_ents = [e for e in sent.ents if e.label_ in ("DATE", "TIME")]
        if time_ents:
            timeline.append({"time": time_ents[0].text, "event": sent.text.strip()})

    orig_w  = len(text.split())
    summ_w  = len(exec_sum.split())
    compression = f"{max(0, 100 - round(summ_w / max(orig_w, 1) * 100))}%"

    return {
        "executive":    exec_sum,
        "key_sentences": key_sents,
        "timeline":     timeline,
        "stats": {
            "original_words":  orig_w,
            "summary_words":   summ_w,
            "compression":     compression,
            "key_sentences":   len(key_sents),
            "timeline_events": len(timeline),
        },
    }
