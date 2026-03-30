import streamlit as st
import pandas as pd
from modules.utils import load_spacy

def render(doc_text):
    st.header("📝 Module 1 — NLP Preprocessing Engine")
    
    with st.spinner("Loading spaCy…"):
        nlp = load_spacy()

    doc = nlp(doc_text)
    tokens      = [t for t in doc if not t.is_space]
    sentences   = [s.text.strip() for s in doc.sents]
    stopwords   = [t.text for t in tokens if t.is_stop]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tokens", len(tokens))
    c2.metric("Sentences", len(sentences))
    c3.metric("Unique Tokens", len(set(t.text.lower() for t in tokens)))
    c4.metric("Stop Words", len(stopwords))

    st.subheader("🔤 Tokenized Stream")
    st.markdown(" ".join([f"`{t.text}`" for t in tokens[:50]]) + ("  …" if len(tokens) > 50 else ""))

    st.subheader("🏷️ POS Tags (first 25 tokens)")
    pos_rows = []
    open_cls  = {'NOUN', 'VERB', 'ADJ', 'ADV', 'PROPN'}
    closed_cls = {'DET', 'ADP', 'CONJ', 'PRON', 'AUX', 'PART'}
    
    for t in tokens[:25]:
        pos_rows.append({
            "Token": t.text, "Lemma": t.lemma_, "POS": t.pos_,
            "Word Class": "Open" if t.pos_ in open_cls else "Closed" if t.pos_ in closed_cls else "Other",
            "Stop Word": "✓" if t.is_stop else ""
        })
    st.dataframe(pd.DataFrame(pos_rows), use_container_width=True, height=300)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📖 Open-Class Words")
        ow = sorted(set(t.text for t in tokens if t.pos_ in open_cls and not t.is_stop))[:20]
        st.markdown("  ".join([f"`{w}`" for w in ow]))
    with col_b:
        st.subheader("📌 Closed-Class Words")
        cw = sorted(set(t.text.lower() for t in tokens if t.pos_ in closed_cls))[:20]
        st.markdown("  ".join([f"`{w}`" for w in cw]))

    st.markdown('<div class="info-card">✅ <b>Module 1 complete</b></div>', unsafe_allow_html=True)