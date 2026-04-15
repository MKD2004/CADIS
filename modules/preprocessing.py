import streamlit as st
import pandas as pd
from modules.utils import load_spacy
from ui_components import (
    module_header, section_label, token_stream, info_strip
)

def render(doc_text):
    nlp = load_spacy()
    sp_doc = nlp(doc_text)
    tokens = [t for t in sp_doc if not t.is_space]
    sentences = [s.text.strip() for s in sp_doc.sents]

    module_header("📝", "icon-cyan",
                  "NLP Preprocessing Engine",
                  "UNIT 1 · Tokenization · POS Tagging · Open/Closed Class Words · Normalization")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tokens",  len(tokens))
    c2.metric("Sentences",     len(sentences))
    c3.metric("Unique Tokens", len(set(t.text.lower() for t in tokens)))
    c4.metric("Stop Words",    sum(1 for t in tokens if t.is_stop))

    section_label("Token Stream  ·  color-coded by POS class")
    open_cls   = {'NOUN','VERB','ADJ','ADV','PROPN'}
    closed_cls = {'DET','ADP','CONJ','PRON','AUX','PART'}
    tok_data   = [(t.text, t.pos_, t.is_stop) for t in tokens[:60]]
    token_stream(tok_data)

    section_label("POS Tag Table  ·  first 30 tokens")
    pos_rows = []
    for t in tokens[:30]:
        pos_rows.append({
            "Token":       t.text,
            "Lemma":       t.lemma_,
            "POS":         t.pos_,
            "Dep":         t.dep_,
            "Word Class":  "Open"   if t.pos_ in open_cls
                           else "Closed" if t.pos_ in closed_cls
                           else "Other",
            "Stop?": "✓" if t.is_stop else "",
        })
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, height=320)

    col_a, col_b = st.columns(2)
    with col_a:
        section_label("Open-Class Words")
        ow = sorted(set(t.text for t in tokens if t.pos_ in open_cls and not t.is_stop))[:18]
        token_stream([(w, "NOUN", False) for w in ow])
    with col_b:
        section_label("Closed-Class Words")
        cw = sorted(set(t.text.lower() for t in tokens if t.pos_ in closed_cls))[:18]
        token_stream([(w, "DET", True) for w in cw])

    info_strip("Module 1 complete — document tokenized, lemmatized, POS-tagged and word classes identified.")
