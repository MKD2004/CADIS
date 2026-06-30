"""
CADIS FastAPI server — exposes the full 6-module NLP pipeline as a single REST endpoint.
Run: uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from functools import lru_cache
import numpy as np
import io

app = FastAPI(title="CADIS API", version="2.0")

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

# ── Model loaders (cached so they load once) ──────────────────────────────────

@lru_cache(maxsize=1)
def get_nlp():
    import spacy
    return spacy.load("en_core_web_sm")

@lru_cache(maxsize=1)
def get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

@lru_cache(maxsize=1)
def get_ner_pipe():
    from transformers import pipeline
    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

@lru_cache(maxsize=1)
def get_qa_pipe():
    from transformers import AutoTokenizer, AutoModelForQuestionAnswering
    import torch
    model_id = "deepset/minilm-uncased-squad2"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForQuestionAnswering.from_pretrained(model_id)
    return tokenizer, model

@lru_cache(maxsize=1)
def get_summarizer():
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    model_id = "sshleifer/distilbart-cnn-12-6"
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    return tokenizer, model


# ── Request / Response models ─────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    text: str


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
    from sklearn.metrics.pairwise import cosine_similarity

    ambiguities = []
    for sent in sp_doc.sents:
        s_doc = sp_doc.vocab.strings  # dummy — we re-parse per sentence
        import spacy
        nlp2 = get_nlp()
        s_doc = nlp2(sent.text)

        for tok in s_doc:
            # PP attachment
            if tok.pos_ == "ADP":
                head = tok.head
                alt  = [t for t in s_doc if t != head and t.pos_ in ("NOUN", "VERB")
                        and 0 < abs(t.i - tok.i) < 5]
                if alt:
                    candidates = [head.text, alt[0].text]
                    q_e = embedder.encode([text])
                    c_e = embedder.encode(candidates)
                    sc  = cosine_similarity(q_e, c_e)[0]
                    ambiguities.append({
                        "type":        "PP Attachment",
                        "trigger":     tok.text,
                        "sentence":    sent.text.strip(),
                        "candidates":  candidates,
                        "resolved":    candidates[int(sc.argmax())],
                        "confidence":  round(float(sc.max()), 3),
                    })
                    break  # one per sentence

            # Anaphora
            if tok.pos_ == "PRON" and tok.text.lower() in (
                "he", "she", "it", "they", "his", "her", "their", "its"
            ):
                prev_nouns = [t for t in s_doc[: tok.i] if t.pos_ in ("NOUN", "PROPN")]
                if len(prev_nouns) >= 2:
                    candidates = [p.text for p in prev_nouns[-3:]]
                    q_e = embedder.encode([text])
                    c_e = embedder.encode(candidates)
                    sc  = cosine_similarity(q_e, c_e)[0]
                    ambiguities.append({
                        "type":        "Anaphoric",
                        "trigger":     tok.text,
                        "sentence":    sent.text.strip(),
                        "candidates":  candidates,
                        "resolved":    candidates[int(sc.argmax())],
                        "confidence":  round(float(sc.max()), 3),
                    })
                    break

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


def run_qa(text: str, qa_pipe):
    import torch
    tokenizer, model = qa_pipe

    questions = [
        "Who is the main person mentioned?",
        "What organization is involved?",
        "Where did the event take place?",
        "When did this happen?",
        "What was the amount of money involved?",
        "Who made the announcement?",
        "What was the outcome?",
    ]

    def answer_question(question: str, context: str):
        inputs = tokenizer(question, context, return_tensors="pt",
                           truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        start = torch.argmax(outputs.start_logits).item()
        end   = torch.argmax(outputs.end_logits).item() + 1
        # Convert confidence via softmax
        start_conf = float(torch.softmax(outputs.start_logits, dim=-1)[0][start])
        end_conf   = float(torch.softmax(outputs.end_logits,   dim=-1)[0][end - 1])
        score = (start_conf + end_conf) / 2

        input_ids = inputs["input_ids"][0]
        # Find context offset (after [SEP] token)
        sep_idx = (input_ids == tokenizer.sep_token_id).nonzero(as_tuple=True)[0]
        ctx_start = int(sep_idx[0]) + 1 if len(sep_idx) > 0 else 0

        answer_ids = input_ids[start:end]
        answer = tokenizer.decode(answer_ids, skip_special_tokens=True).strip()

        # Map token positions back to char positions in context
        char_start, char_end = 0, 0
        try:
            encoding = tokenizer(question, context, return_offsets_mapping=True,
                                 truncation=True, max_length=512)
            offsets = encoding["offset_mapping"]
            if start < len(offsets) and end - 1 < len(offsets):
                char_start = offsets[start][0]
                char_end   = offsets[end - 1][1]
        except Exception:
            pass

        return answer, score, char_start, char_end

    results = []
    for q in questions:
        try:
            answer, score, char_start, char_end = answer_question(q, text[:2000])
            if score > 0.04 and answer:
                results.append({
                    "question":   q,
                    "answer":     answer,
                    "confidence": round(score, 3),
                    "start":      char_start,
                    "end":        char_end,
                })
            else:
                results.append({"question": q, "answer": "", "confidence": 0.0, "start": 0, "end": 0})
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
            "total":         len(questions),
            "avg_confidence": avg_conf,
        },
    }


def run_summary(text: str, sp_doc, summarizer):
    # Abstractive — DistilBART (direct model call)
    tokenizer, model = summarizer
    trunc = " ".join(text.split()[:400])
    try:
        inputs = tokenizer(trunc, return_tensors="pt", max_length=1024, truncation=True)
        ids = model.generate(
            inputs["input_ids"],
            max_length=90, min_length=25,
            num_beams=4, early_stopping=True,
        )
        exec_sum = tokenizer.decode(ids[0], skip_special_tokens=True)
    except Exception as e:
        exec_sum = f"Summarization error: {e}"

    # Extractive key sentences
    scored = []
    for sent in sp_doc.sents:
        ent_score  = len(list(sent.ents)) * 2
        verb_score = sum(1 for t in sent if t.pos_ == "VERB")
        if len(sent.text.strip()) > 20:
            scored.append((sent.text.strip(), ent_score + verb_score))
    key_sents = [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:4]]

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
    import torch
    tokenizer, model = get_qa_pipe()
    try:
        inputs = tokenizer(req.question.strip(), req.text.strip()[:2000],
                           return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        start = torch.argmax(outputs.start_logits).item()
        end   = torch.argmax(outputs.end_logits).item() + 1
        start_conf = float(torch.softmax(outputs.start_logits, dim=-1)[0][start])
        end_conf   = float(torch.softmax(outputs.end_logits,   dim=-1)[0][end - 1])
        score = (start_conf + end_conf) / 2
        answer = tokenizer.decode(inputs["input_ids"][0][start:end], skip_special_tokens=True).strip()

        char_start, char_end = 0, 0
        try:
            enc = tokenizer(req.question.strip(), req.text.strip()[:2000],
                            return_offsets_mapping=True, truncation=True, max_length=512)
            offsets = enc["offset_mapping"]
            if start < len(offsets) and end - 1 < len(offsets):
                char_start = offsets[start][0]
                char_end   = offsets[end - 1][1]
        except Exception:
            pass

        return {
            "question":   req.question,
            "answer":     answer if score > 0.01 and answer else "",
            "confidence": round(score, 4),
            "start":      char_start,
            "end":        char_end,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok", "service": "CADIS API v2.0"}


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
        "qa":            run_qa(text, qa_pipe),
        "summary":       run_summary(text, sp_doc, summarizer),
    }
