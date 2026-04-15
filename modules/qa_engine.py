import streamlit as st
from modules.utils import load_qa_pipeline
from ui_components import (
    module_header, section_label, qa_answer_card, qa_context_highlight, info_strip
)

def render(doc_text, qa_results=None):
    qa_pipe = load_qa_pipeline()

    module_header("❓", "icon-green",
                  "Extractive QA Engine",
                  "UNIT 1 · QA Systems · LLM Application Patterns · Extractive vs Generative QA")

    section_label("Auto-Generated Questions")
    if qa_results:
        for qa in qa_results:
            col_q, col_a, col_c = st.columns([3, 3, 1])
            with col_q:
                st.markdown(
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
                    f'color:#64748b;padding:8px 0">{qa["Question"]}</div>',
                    unsafe_allow_html=True
                )
            with col_a:
                st.markdown(
                    f'<div style="font-family:\'Syne\',sans-serif;font-size:0.88rem;'
                    f'font-weight:600;color:#00e5ff;padding:8px 0">{qa["Answer"]}</div>',
                    unsafe_allow_html=True
                )
            with col_c:
                conf = qa["Confidence"]
                color = "#10b981" if conf > 0.5 else "#f59e0b" if conf > 0.2 else "#ef4444"
                st.markdown(
                    f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:0.78rem;'
                    f'color:{color};padding:8px 0;text-align:right">{conf:.0%}</div>',
                    unsafe_allow_html=True
                )
        st.markdown('<div style="height:1px;background:#1e2d40;margin:4px 0 20px"></div>', unsafe_allow_html=True)

    section_label("Ask Your Own Question")
    user_q = st.text_input("Question:", "Who confirmed the deal?", key="user_qa")

    if user_q:
        with st.spinner("Extracting answer…"):
            r = qa_pipe(question=user_q, context=doc_text)
        qa_answer_card(user_q, r["answer"], r["score"], r["start"], r["end"])
        section_label("Source Context")
        qa_context_highlight(doc_text, r["start"], r["end"])

    info_strip("Module 5 complete — every answer is grounded in the document with exact character-span provenance. No hallucination possible.")
