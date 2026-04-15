import streamlit as st
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from modules.utils import load_embedder, load_spacy
from ui_components import (
    module_header, section_label, search_bubble, info_strip
)

def render(doc_text, valid_sents=None, embeddings_arr=None):
    embedder = load_embedder()
    
    if valid_sents is None or embeddings_arr is None:
        nlp = load_spacy()
        sp_doc = nlp(doc_text)
        sentences = [s.text.strip() for s in sp_doc.sents]
        valid_sents = [s for s in sentences if len(s) > 15]
        embeddings_arr = embedder.encode(valid_sents)

    module_header("🔢", "icon-purple",
                  "Semantic Embedding Module",
                  "UNIT 1 · One-hot vs Dense · Distributional Semantics · Contextual Embeddings (BERT)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sentences Encoded", len(valid_sents))
    c2.metric("Embedding Dim",     embeddings_arr.shape[1])
    c3.metric("Model",             "MiniLM-L6-v2")

    section_label("Embedding Vectors Preview")
    import pandas as pd
    emb_df = pd.DataFrame({
        "Sentence":  [s[:55] + "…" if len(s) > 55 else s for s in valid_sents],
        "dim[0]":    embeddings_arr[:, 0].round(4),
        "dim[1]":    embeddings_arr[:, 1].round(4),
        "dim[2]":    embeddings_arr[:, 2].round(4),
        "L2 Norm":   np.linalg.norm(embeddings_arr, axis=1).round(4),
    })
    st.dataframe(emb_df, use_container_width=True)

    section_label("Sentence Similarity Heatmap")
    sim_matrix = cosine_similarity(embeddings_arr)
    labels     = [s[:30] + "…" if len(s) > 30 else s for s in valid_sents]

    import plotly.graph_objects as go
    fig = go.Figure(go.Heatmap(
        z=sim_matrix, x=labels, y=labels,
        colorscale=[[0,"#07090f"],[0.5,"#1e2d40"],[1,"#00e5ff"]],
        text=sim_matrix.round(2),
        texttemplate="%{text}",
        textfont={"size": 9, "color": "#e2e8f0"},
        showscale=True,
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        font=dict(color="#94a3b8", family="JetBrains Mono"),
        title=dict(text="Cosine Similarity Matrix", font=dict(color="#e2e8f0", size=13)),
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(tickfont=dict(size=9), tickangle=-30),
        yaxis=dict(tickfont=dict(size=9)),
    )
    st.plotly_chart(fig, use_container_width=True)

    section_label("Semantic Search")
    query = st.text_input("Enter a question to search the document semantically:",
                          "Who is responsible for the decision?",
                          placeholder="Type any query…")
    if query:
        q_emb  = embedder.encode([query])
        scores = cosine_similarity(q_emb, embeddings_arr)[0]
        ranked = sorted(zip(valid_sents, scores.tolist()), key=lambda x: x[1], reverse=True)
        for i, (sent, score) in enumerate(ranked[:3]):
            search_bubble(i + 1, sent, score)

    info_strip("Module 2 complete — 384-dim dense embeddings computed; cosine similarity matrix and semantic retrieval operational.")
