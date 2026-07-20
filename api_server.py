"""
CADIS FastAPI server — exposes the full 6-module NLP pipeline as a single REST endpoint.
Run: uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
import numpy as np
import math
import re
import io

app = FastAPI(title="CADIS API", version="2.1")

import os

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
]

# Add Vercel deployment URL from environment variable if set
_frontend_url = os.getenv("FRONTEND_URL")
if _frontend_url:
    ALLOWED_ORIGINS.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model IDs (env-overridable so the HF Space can swap without a code change) ──

QA_MODEL_ID  = os.getenv("QA_MODEL",  "deepset/roberta-base-squad2")
SUM_MODEL_ID = os.getenv("SUM_MODEL", "sshleifer/distilbart-cnn-12-6")
NER_MODEL_ID = os.getenv("NER_MODEL", "dslim/bert-base-NER")
EMB_MODEL_ID = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")

# ── Model loaders (cached so they load once) ──────────────────────────────────

@lru_cache(maxsize=1)
def get_nlp():
    import spacy
    return spacy.load("en_core_web_sm")

@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMB_MODEL_ID)

@lru_cache(maxsize=1)
def get_ner_pipe():
    from transformers import pipeline
    return pipeline("ner", model=NER_MODEL_ID, aggregation_strategy="simple")

@lru_cache(maxsize=1)
def get_qa_pipe():
    from transformers import AutoTokenizer, AutoModelForQuestionAnswering
    tokenizer = AutoTokenizer.from_pretrained(QA_MODEL_ID, use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(QA_MODEL_ID)
    model.eval()
    return tokenizer, model

@lru_cache(maxsize=1)
def get_summarizer():
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    tokenizer = AutoTokenizer.from_pretrained(SUM_MODEL_ID)
    model = AutoModelForSeq2SeqLM.from_pretrained(SUM_MODEL_ID)
    model.eval()
    return tokenizer, model


# ── Request / Response models ─────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    text: str


# ══════════════════════════════════════════════════════════════════════════════
# Extractive QA engine
#
# Span decoding has to be done properly or the model returns garbage:
#   * `end` must come after `start` — an unconstrained argmax over each logit
#     vector independently can produce start=CLS(0) and end=last-token, which
#     decodes to the entire question+context (this was the original bug).
#   * Only *context* tokens are valid answers — question tokens and padding
#     must be masked out.
#   * SQuAD2 models emit a null answer at the CLS position; a span is only a
#     real answer if it outscores that null.
#   * Char offsets must come from the offset mapping of the token's own
#     sequence, otherwise the frontend highlights the wrong region.
# ══════════════════════════════════════════════════════════════════════════════

QA_WINDOW        = 384   # tokens per sliding window
QA_STRIDE        = 128   # overlap between windows so answers aren't cut in half
MAX_ANSWER_TOKENS = 40   # longest span we will ever return
QA_TOP_K         = 20    # start/end candidates considered per window
MAX_PASSAGES     = 6     # passages retrieved per question (bounds CPU latency)
PASSAGE_WORDS    = 200
PASSAGE_OVERLAP  = 50


def _split_passages(text, words_per=PASSAGE_WORDS, overlap=PASSAGE_OVERLAP):
    """Split text into overlapping passages, keeping each one's char offset
    into the original document so answer spans stay addressable."""
    words = list(re.finditer(r"\S+", text))
    if not words:
        return []

    passages, step = [], max(1, words_per - overlap)
    for start in range(0, len(words), step):
        window = words[start:start + words_per]
        if not window:
            break
        c0, c1 = window[0].start(), window[-1].end()
        passages.append((text[c0:c1], c0))
        if start + words_per >= len(words):
            break
    return passages


def _select_passages(question, passages, embedder, k=MAX_PASSAGES):
    """Semantic retrieval — rank passages against the question and keep the
    top-k, in document order. Keeps long documents answerable without running
    the QA model over every window."""
    if len(passages) <= k:
        return passages

    from sklearn.metrics.pairwise import cosine_similarity
    q_vec = embedder.encode([question])
    p_vec = embedder.encode([p for p, _ in passages])
    sims = cosine_similarity(q_vec, p_vec)[0]
    keep = sorted(int(i) for i in np.argsort(-sims)[:k])
    return [passages[i] for i in keep]


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
    and return (best_score, char_start, char_end, null_score)."""
    import torch

    enc = tokenizer(
        [question] * len(passages),
        [p for p, _ in passages],
        truncation="only_second",
        max_length=QA_WINDOW,
        stride=QA_STRIDE,
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

        k = min(QA_TOP_K, s_log.shape[0])
        s_cands = [int(x) for x in torch.topk(s_log, k).indices.tolist() if x in ctx]
        e_cands = [int(x) for x in torch.topk(e_log, k).indices.tolist() if x in ctx]

        base = passages[sample_map[i]][1]
        for s in s_cands:
            for e in e_cands:
                if e < s or e - s + 1 > MAX_ANSWER_TOKENS:
                    continue
                score = float(s_log[s]) + float(e_log[e])
                if best is None or score > best[0]:
                    best = (
                        score,
                        int(offsets[i][s][0]) + base,
                        int(offsets[i][e][1]) + base,
                    )

    return best, null_score


def answer_question(question, text, tokenizer, model, embedder, passages=None):
    """Answer one question against a document. Returns an empty answer when the
    model is more confident there is no answer than in any candidate span."""
    question = (question or "").strip()
    text = (text or "").strip()
    empty = {"question": question, "answer": "", "confidence": 0.0, "start": 0, "end": 0}
    if not question or not text:
        return empty

    if passages is None:
        passages = _split_passages(text)
    passages = _select_passages(question, passages, embedder)
    if not passages:
        return empty

    best, null_score = _best_span(question, passages, tokenizer, model)
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
        "start":      char_start,
        "end":        char_end,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Abstractive summarization
#
# DistilBART accepts 1024 tokens (~750 words). Feeding it only the first 400
# words of a document — as the original did — throws away everything after the
# first two paragraphs, which is why summaries read as if they had missed the
# point. Long documents are summarized chunk-by-chunk and then condensed again.
# ══════════════════════════════════════════════════════════════════════════════

SUM_CHUNK_WORDS = 400   # target words per chunk (DistilBART's limit is ~750)
MAX_SUM_CHUNKS  = 6     # bounds latency on free-tier CPU


def _sentence_chunks(text, target_words=SUM_CHUNK_WORDS):
    """Split into evenly-sized chunks on sentence boundaries.

    Packing greedily at a fixed size leaves a stub final chunk, which then
    gets the same summary budget as a full one and skews coverage toward the
    end of the document. Sizing every chunk to total/n_chunks avoids that.
    """
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    total = len(text.split())
    n_chunks = max(1, min(MAX_SUM_CHUNKS, math.ceil(total / target_words)))
    per = math.ceil(total / n_chunks)

    chunks, current, count = [], [], 0
    for sent in sentences:
        n = len(sent.split())
        if current and count + n > per:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sent)
        count += n
    if current:
        chunks.append(" ".join(current))
    return chunks[:MAX_SUM_CHUNKS]


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
    inputs = tokenizer(text, return_tensors="pt", max_length=1024, truncation=True)
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
    words = text.split()

    # Short enough to summarize in one pass.
    if len(words) <= SUM_CHUNK_WORDS:
        max_len = max(80, min(150, len(words) // 3))
        return _generate(text, tokenizer, model, max_len, min(45, max_len - 20))

    # Map: summarize each chunk with cheap beams.
    chunks = _sentence_chunks(text)
    partials = [_generate(c, tokenizer, model, 110, 40, beams=2) for c in chunks]

    # Reduce: condense the partials into one executive summary.
    joined = _dedupe_sentences(" ".join(partials))
    if len(joined.split()) <= 160:
        return _clean_summary(joined)
    return _generate(joined, tokenizer, model, 160, 70)


# ── Pipeline logic ────────────────────────────────────────────────────────────

def run_preprocessing(text: str, nlp):
    doc = nlp(text)
    tokens = [t for t in doc if not t.is_space]
    sentences = [s.text.strip() for s in doc.sents]

    token_details = [
        {
            "text":    t.text,
            "lemma":   t.lemma_,
            "pos":     t.pos_,
            "dep":     t.dep_,
            "is_stop": t.is_stop,
        }
        for t in tokens
    ]

    return {
        "stats": {
            "total_tokens":  len(tokens),
            "sentences":     len(sentences),
            "unique_tokens": len(set(t.text.lower() for t in tokens)),
            "stop_words":    sum(1 for t in tokens if t.is_stop),
            "char_count":    len(text),
        },
        "token_details": token_details,
        "sentences": sentences,
    }, doc


def run_embeddings(sentences: list, embedder):
    from sklearn.metrics.pairwise import cosine_similarity

    valid = [s for s in sentences if len(s) > 15]
    if not valid:
        valid = sentences[:3]

    vecs = embedder.encode(valid)
    sim  = cosine_similarity(vecs).tolist()

    # Top similar pairs
    pairs = []
    n = len(valid)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append({
                "a":    valid[i],
                "b":    valid[j],
                "score": round(float(sim[i][j]), 4),
            })
    pairs.sort(key=lambda x: x["score"], reverse=True)

    # 2-D positions via PCA-like projection (first 2 dims of the vectors)
    positions = []
    for i, (sent, vec) in enumerate(zip(valid, vecs)):
        positions.append({
            "sentence": sent,
            "x": round(float(vec[0]), 4),
            "y": round(float(vec[1]), 4),
        })

    return {
        "sentences":        valid,
        "dims":             int(vecs.shape[1]),
        "similarity_matrix": sim,
        "top_pairs":        pairs[:5],
        "positions":        positions,
        "vector_preview": [
            {
                "sentence": valid[i][:60],
                "dim0": round(float(vecs[i, 0]), 4),
                "dim1": round(float(vecs[i, 1]), 4),
                "dim2": round(float(vecs[i, 2]), 4),
                "norm": round(float(np.linalg.norm(vecs[i])), 4),
            }
            for i in range(len(valid))
        ],
    }


def run_ner(text: str, sp_doc, ner_pipe):
    # BERT-NER
    bert_ents = ner_pipe(text)
    label_map = {"PER": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION", "MISC": "MISC"}
    entities  = {k: [] for k in ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY", "MISC"]}

    for e in bert_ents:
        lbl = label_map.get(e["entity_group"], e["entity_group"])
        if lbl in entities:
            entities[lbl].append({"text": e["word"], "score": round(float(e["score"]), 3)})

    # spaCy DATE / MONEY supplement
    for ent in sp_doc.ents:
        if ent.label_ in ("DATE", "TIME"):
            entities["DATE"].append({"text": ent.text, "score": 1.0})
        elif ent.label_ in ("MONEY", "CARDINAL", "PERCENT"):
            entities["MONEY"].append({"text": ent.text, "score": 1.0})

    # Deduplicate
    for k in entities:
        seen, deduped = set(), []
        for item in entities[k]:
            if item["text"].lower() not in seen:
                seen.add(item["text"].lower())
                deduped.append(item)
        entities[k] = deduped

    # SVO relations
    relations = []
    for sent in sp_doc.sents:
        for tok in sent:
            if tok.dep_ == "ROOT" and tok.pos_ == "VERB":
                subj = [w for w in tok.lefts  if w.dep_ in ("nsubj", "nsubjpass")]
                obj  = [w for w in tok.rights if w.dep_ in ("dobj", "pobj", "attr", "acomp")]
                if subj and obj:
                    relations.append({
                        "subject":  subj[0].text,
                        "verb":     tok.text,
                        "object":   obj[0].text,
                        "sentence": sent.text.strip()[:100] + ("…" if len(sent.text) > 100 else ""),
                    })

    return {
        "entities": entities,
        "relations": relations,
        "stats": {
            "total_entities":  sum(len(v) for v in entities.values()),
            "entity_types":    sum(1 for v in entities.values() if v),
            "total_relations": len(relations),
        },
    }


def run_ambiguity(text: str, sp_doc, embedder):
    """Detect PP-attachment and anaphoric ambiguities, resolving each candidate
    against its own sentence rather than the whole document — scoring against
    the full text gave every candidate in every sentence the same ranking."""
    from sklearn.metrics.pairwise import cosine_similarity

    ambiguities = []
    for sent in sp_doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue

        # Reuse the already-parsed span; re-running the full spaCy pipeline per
        # sentence was the single largest cost in this module.
        toks = list(sent)
        offset = sent.start

        def resolve(kind, trigger, candidates):
            ctx = embedder.encode([sent_text])
            cnd = embedder.encode(candidates)
            sc = cosine_similarity(ctx, cnd)[0]
            ambiguities.append({
                "type":       kind,
                "trigger":    trigger,
                "sentence":   sent_text,
                "candidates": candidates,
                "resolved":   candidates[int(sc.argmax())],
                "confidence": round(float(sc.max()), 3),
            })

        found = False
        for tok in toks:
            if found:
                break

            # PP attachment — a preposition with a competing nearby head.
            if tok.pos_ == "ADP":
                head = tok.head
                alt = [t for t in toks
                       if t != head and t.pos_ in ("NOUN", "VERB")
                       and 0 < abs(t.i - tok.i) < 5]
                if alt:
                    resolve("PP Attachment", tok.text, [head.text, alt[0].text])
                    found = True
                    continue

            # Anaphora — a pronoun with several possible antecedents.
            if tok.pos_ == "PRON" and tok.text.lower() in (
                "he", "she", "it", "they", "his", "her", "their", "its"
            ):
                prev_nouns = [t for t in toks[: tok.i - offset] if t.pos_ in ("NOUN", "PROPN")]
                if len(prev_nouns) >= 2:
                    resolve("Anaphoric", tok.text, [p.text for p in prev_nouns[-3:]])
                    found = True

    pp_count   = sum(1 for a in ambiguities if a["type"] == "PP Attachment")
    anap_count = sum(1 for a in ambiguities if a["type"] == "Anaphoric")

    return {
        "items": ambiguities,
        "stats": {
            "detected":      len(ambiguities),
            "pp_attachments": pp_count,
            "anaphoric":     anap_count,
            "resolved":      len(ambiguities),
        },
    }


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
    tokenizer, model = qa_pipe
    passages = _split_passages(text)   # built once, reused for every question

    results = []
    for q in PRESET_QUESTIONS:
        try:
            results.append(answer_question(q, text, tokenizer, model, embedder, passages))
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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/extract")
async def extract_text(file: UploadFile = File(...)):
    """Extract plain text from .txt, .pdf, or .docx uploads."""
    content = await file.read()
    name = (file.filename or "").lower()

    try:
        if name.endswith(".txt"):
            text = content.decode("utf-8", errors="replace")

        elif name.endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                raise HTTPException(status_code=500, detail="pypdf not installed. Run: pip install pypdf")

        elif name.endswith(".docx"):
            try:
                import docx
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                raise HTTPException(status_code=500, detail="python-docx not installed. Run: pip install python-docx")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {name}. Use .txt, .pdf, or .docx")

        text = text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="No text could be extracted from the file.")

        return {"text": text, "chars": len(text), "words": len(text.split())}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction error: {e}")


class AskRequest(BaseModel):
    text: str
    question: str

@app.post("/api/qa-ask")
def qa_ask(req: AskRequest):
    """Answer a single custom question against the provided document."""
    tokenizer, model = get_qa_pipe()
    try:
        return answer_question(req.question, req.text, tokenizer, model, get_embedder())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "service": "CADIS API v2.1"}


@app.post("/api/process")
def process(req: ProcessRequest):
    text = req.text.strip()
    if not text:
        return {"error": "Empty document"}

    nlp        = get_nlp()
    embedder   = get_embedder()
    ner_pipe   = get_ner_pipe()
    qa_pipe    = get_qa_pipe()
    summarizer = get_summarizer()  # returns (tokenizer, model) tuple

    preprocessing_result, sp_doc = run_preprocessing(text, nlp)
    sentences = preprocessing_result["sentences"]

    return {
        "preprocessing": preprocessing_result,
        "embeddings":    run_embeddings(sentences, embedder),
        "ner":           run_ner(text, sp_doc, ner_pipe),
        "ambiguity":     run_ambiguity(text, sp_doc, embedder),
        "qa":            run_qa(text, qa_pipe, embedder),
        "summary":       run_summary(text, sp_doc, summarizer),
    }
