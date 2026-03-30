import streamlit as st
from modules.utils import load_summarizer, load_spacy

def render(doc_text):
    st.header("📋 Module 6 — Intelligent Summary Generator")
    
    summarizer = load_summarizer()
    nlp = load_spacy()
    sp_doc = nlp(doc_text)
    trunc_text = " ".join(doc_text.split()[:400])

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📌 Executive Summary")
        with st.spinner("Generating…"):
            try:
                result = summarizer(trunc_text, max_length=90, min_length=25, do_sample=False)
                exec_sum = result[0]["summary_text"]
            except Exception as e:
                exec_sum = f"[Summarization error: {e}]"
        
        st.markdown(f'<div style="background:#2b2b2b;border-radius:10px;padding:18px;border-left:5px solid #302b63;">{exec_sum}</div>', unsafe_allow_html=True)

    with col_right:
        st.subheader("🔹 Key Sentence Extraction")
        scored = []
        for sent in sp_doc.sents:
            score = (len(list(sent.ents)) * 2) + sum(1 for t in sent if t.pos_ == "VERB")
            if len(sent.text.strip()) > 20:
                scored.append((sent.text.strip(), score))
        
        top = sorted(scored, key=lambda x: x[1], reverse=True)[:4]
        for s, _ in top:
            st.markdown(f"• {s}")

    st.markdown('<div class="info-card">✅ <b>Module 6 complete</b></div>', unsafe_allow_html=True)
    st.balloons()