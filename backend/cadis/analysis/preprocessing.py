"""Module 1 — spaCy preprocessing: tokens, lemmas, POS, dependencies, sentences."""


def run_preprocessing(text: str, nlp):
    """Returns (result, spacy_doc). The doc is reused by NER, ambiguity and summary."""
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
