import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import plotly.graph_objects as go
from modules.utils import load_spacy, load_embedder

def render(doc_text):
    st.header("🔢 Module 2 — Semantic Embedding Module")
    
    nlp = load_spacy()
    embedder = load_embedder()
    sents = [s.text.strip() for s in nlp(doc_text).sents if len(s.text.strip()) > 15]

    with st.spinner("Computing embeddings…"):
        embeddings = embedder.encode(sents)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sentences Encoded", len(sents))
    c2.metric("Embedding Dim", embeddings.shape[1])
    c3.metric("Model", "MiniLM-L6-v2")

    st.subheader("🌡️ Sentence Similarity Heatmap")
    sim_matrix = cosine_similarity(embeddings)
    labels = [s[:35] + "…" if len(s) > 35 else s for s in sents]

    fig = go.Figure(go.Heatmap(
        z=sim_matrix, x=labels, y=labels, colorscale="Blues",
        text=sim_matrix.round(2), texttemplate="%{text}", textfont={"size": 9},
    ))
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔍 Semantic Search Demo")
    query = st.text_input("Search the document semantically:", "Who is responsible for the decision?")
    if query:
        q_emb  = embedder.encode([query])
        scores = cosine_similarity(q_emb, embeddings)[0]
        ranked = sorted(zip(sents, scores.tolist()), key=lambda x: x[1], reverse=True)
        for i, (sent, score) in enumerate(ranked[:3]):
            bar = "█" * int(score * 20)
            color = "#27ae60" if score > 0.45 else "#f39c12" if score > 0.25 else "#e74c3c"
            st.markdown(f"""
            <div style="border-left:4px solid {color};padding:10px 14px;background:#1e1e1e;
                        border-radius:6px;margin:6px 0;color:white;">
              <b>#{i+1}</b> &nbsp; Score: <code>{score:.3f}</code>
              &nbsp; <span style="color:{color};font-family:monospace;font-size:0.8rem">{bar}</span>
              <br>{sent}
            </div>""", unsafe_allow_html=True)
            
    st.markdown('<div class="info-card">✅ <b>Module 2 complete</b></div>', unsafe_allow_html=True)