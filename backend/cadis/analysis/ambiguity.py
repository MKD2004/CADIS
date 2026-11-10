"""Module 4 — PP-attachment and anaphora *heuristic* (V1).

Known limits (see CADIS V2.md, Phase 5 and DECISIONS ADR-025): it flags almost
every sentence with a preposition, reports at most one item per sentence, and
its "resolution" compares a sentence embedding with single-word embeddings,
which does not find what a pronoun refers to. It is kept unchanged until the
coreference module replaces it.
"""


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
