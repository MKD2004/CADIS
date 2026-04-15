import streamlit as st
from modules.utils import load_summarizer, load_spacy
from ui_components import (
    module_header, section_label, exec_summary_card, bullet_summary,
    timeline_item, stat_cards, completion_banner, info_strip
)

def render(doc_text, exec_sum=None, top_sents=None, timeline=None):
    summarizer = load_summarizer()
    nlp = load_spacy()
    sp_doc = nlp(doc_text)
    
    if exec_sum is None:
        trunc_text = " ".join(doc_text.split()[:400])
        try:
            result   = summarizer(trunc_text, max_length=90, min_length=25, do_sample=False)
            exec_sum = result[0]["summary_text"]
        except Exception as e:
            exec_sum = f"Summarization error: {e}"
    
    if top_sents is None:
        scored = []
        for sent in sp_doc.sents:
            ent_score  = len(list(sent.ents)) * 2
            verb_score = sum(1 for t in sent if t.pos_ == "VERB")
            if len(sent.text.strip()) > 20:
                scored.append((sent.text.strip(), ent_score + verb_score))
        top_sents = [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:4]]
    
    if timeline is None:
        timeline = []
        for sent in sp_doc.sents:
            time_ents = [e for e in sent.ents if e.label_ in ("DATE","TIME")]
            if time_ents:
                timeline.append({"time": time_ents[0].text, "event": sent.text.strip()})

    module_header("📋", "icon-blue",
                  "Intelligent Summary Generator",
                  "UNIT 1 · Text Generation · Transformer Generation · Abstractive + Extractive Summarization")

    col_l, col_r = st.columns([3, 2])

    with col_l:
        section_label("Executive Summary  ·  DistilBART Abstractive")
        exec_summary_card(exec_sum)

    with col_r:
        section_label("Key Sentences  ·  Entity-Density Extraction")
        bullet_summary(top_sents)

    section_label("Event Timeline  ·  Temporal Entity Anchoring")
    if timeline:
        tl_html = ""
        for item in timeline:
            tl_html += timeline_item(item["time"], item["event"])
        st.markdown(f'<div style="padding:4px 0">{tl_html}</div>', unsafe_allow_html=True)
    else:
        st.info("No explicit temporal markers found. Try the Medical or News sample.")

    section_label("Compression Statistics")
    orig_w  = len(doc_text.split())
    summ_w  = len(exec_sum.split())
    ratio   = f"{100 - summ_w / orig_w * 100:.0f}%"
    stat_cards([
        (orig_w,          "Original Words"),
        (summ_w,          "Summary Words"),
        (ratio,           "Compression"),
        (len(top_sents),  "Key Sentences"),
        (len(timeline),   "Timeline Events"),
    ])

    completion_banner()
    st.balloons()

    info_strip("Module 6 complete — abstractive summary + extractive key sentences + event timeline. Full pipeline finished.")
