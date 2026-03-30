import streamlit as st
import pandas as pd
from modules.utils import load_qa_pipeline

def render(doc_text):
    st.header("❓ Module 5 — Extractive QA Engine")
    
    qa_pipe = load_qa_pipeline()
    auto_qs = ["Who is the main person mentioned?", "Where did the event take place?", "What was the outcome?"]

    st.subheader("🤖 Auto-Generated Q&A")
    auto_results = []
    for q in auto_qs:
        try:
            r = qa_pipe(question=q, context=doc_text)
            if r["score"] > 0.04:
                auto_results.append({"Question": q, "Answer": r["answer"], "Confidence": round(r["score"], 3)})
        except Exception:
            pass

    if auto_results:
        st.dataframe(pd.DataFrame(auto_results), use_container_width=True)

    st.markdown("---")
    st.subheader("💬 Ask Your Own Question")
    user_q = st.text_input("Type any question about the document:", "Who confirmed the deal?")

    if user_q:
        with st.spinner("Finding answer…"):
            r = qa_pipe(question=user_q, context=doc_text)
        
        conf = r["score"]
        st.markdown(f"""
        <div class="answer-box">
          <h3>💡 Answer</h3>
          <div class="answer-text">{r['answer']}</div>
          <div class="answer-meta">Confidence: <b>{conf:.1%}</b></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="info-card">✅ <b>Module 5 complete</b></div>', unsafe_allow_html=True)