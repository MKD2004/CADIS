"""Module 3 — named entities (BERT-NER + spaCy dates/numbers) and SVO relations.

BERT reads at most 512 tokens. V1 passed the whole document to the pipeline,
which silently dropped everything past that limit — on a 3,600-word test the
name in the last sentence was never found. The text is now run in windows of
whole sentences that each fit the model.
"""

from cadis.config import get_settings


def _n_tokens(text, tokenizer):
    # Counting only — no model call — so silence the over-length warning.
    return len(tokenizer(text, add_special_tokens=False, verbose=False)["input_ids"])


def _sentence_units(sp_doc, tokenizer, limit):
    """(char_start, char_end, n_tokens) per sentence; sentences longer than
    `limit` are split into runs of spaCy tokens that fit."""
    units = []
    for sent in sp_doc.sents:
        text = sent.text_with_ws.strip()
        if not text:
            continue
        n = _n_tokens(text, tokenizer)
        if n <= limit:
            units.append((sent.start_char, sent.end_char, n))
            continue
        toks = [t for t in sent if not t.is_space]
        step = max(1, int(len(toks) * limit / n * 0.9))
        for i in range(0, len(toks), step):
            piece = toks[i:i + step]
            s, e = piece[0].idx, piece[-1].idx + len(piece[-1].text)
            units.append((s, e, _n_tokens(sp_doc.text[s:e], tokenizer)))
    return units


def ner_windows(sp_doc, tokenizer, limit):
    """Pack consecutive sentences into windows of at most `limit` model tokens.
    Returns [(char_start, char_end)] into the document text. Entities never
    cross a sentence boundary, so no overlap between windows is needed."""
    windows, start, end, count = [], None, None, 0
    for s, e, n in _sentence_units(sp_doc, tokenizer, limit):
        if start is not None and count + n > limit:
            windows.append((start, end))
            start, count = None, 0
        if start is None:
            start = s
        end, count = e, count + n
    if start is not None:
        windows.append((start, end))
    return windows


def _bert_entities(text, sp_doc, ner_pipe):
    tokenizer = ner_pipe.tokenizer
    model_max = getattr(tokenizer, "model_max_length", 512) or 512
    limit = min(get_settings().ner_chunk_tokens, model_max - 2)
    windows = ner_windows(sp_doc, tokenizer, limit)
    if not windows:
        return []
    results = ner_pipe([text[s:e] for s, e in windows])
    entities = []
    for (w0, _), window_ents in zip(windows, results):
        for ent in window_ents:
            ent = dict(ent)
            # Take the surface text from the document by offset: the pipeline's
            # "word" is rebuilt from tokens and can differ from the source.
            if ent.get("start") is not None and ent.get("end") is not None:
                ent["start"] += w0
                ent["end"] += w0
                ent["word"] = text[ent["start"]:ent["end"]]
            entities.append(ent)
    return entities


def run_ner(text: str, sp_doc, ner_pipe):
    # BERT-NER, window by window
    bert_ents = _bert_entities(text, sp_doc, ner_pipe)
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
