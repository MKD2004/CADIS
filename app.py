"""
CADIS — Context-Aware Document Intelligence System
Premium Research Platform · v2.0
"""

import streamlit as st
import json
import numpy as np
import pandas as pd
from ui_components import (
    inject_css, module_header, section_label,
    token_stream, render_entities, relation_row,
    ambiguity_card, search_bubble, qa_answer_card,
    qa_context_highlight, exec_summary_card, bullet_summary,
    timeline_item, stat_cards, info_strip, completion_banner,
    welcome_screen, sidebar_architecture
)
from modules.utils import load_spacy, load_embedder, load_ner_pipeline, load_qa_pipeline, load_summarizer
import modules.preprocessing as preprocessing
import modules.embeddings as embeddings
import modules.ner_ie as ner_ie
import modules.ambiguity as ambiguity
import modules.qa_engine as qa_engine
import modules.summarizer as summarizer_module

st.set_page_config(
    page_title="CADIS · Research Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

def load_lottie_url(url: str):
    try:
        import requests
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

try:
    from streamlit_lottie import st_lottie
    LOTTIE_DATA = load_lottie_url(
        "https://assets9.lottiefiles.com/packages/lf20_w51pcehl.json"
    )
    HAS_LOTTIE = LOTTIE_DATA is not None
except ImportError:
    HAS_LOTTIE = False
    LOTTIE_DATA = None

try:
    from annotated_text import annotated_text
    HAS_ANNOTATED = True
except ImportError:
    HAS_ANNOTATED = False

SAMPLES = {
    "⚖️ Legal — Corporate Acquisition": (
        "Apple Inc. announced on Tuesday that it will acquire AI startup NeuralBase "
        "for $2.5 billion. The deal, expected to close by March 2025, was confirmed "
        "by CEO Tim Cook at a press conference held in San Francisco. Legal experts "
        "in New York warned that the acquisition might face regulatory scrutiny from "
        "the European Commission in Brussels. Sarah Johnson, the CFO, stated that "
        "the merger would help Apple expand its AI capabilities significantly. "
        "However, she noted that the board had approved the deal on Monday morning "
        "after reviewing the contract she was carrying."
    ),
    "🏥 Medical — Case Report": (
        "Patient John Smith, aged 45, was admitted to St. Mary's Hospital in Chicago "
        "on January 15, 2024 with acute chest pain. Dr. Emily Chen, the attending "
        "cardiologist, diagnosed him with myocardial infarction. Emergency angioplasty "
        "was performed by Dr. Robert Williams on the same day. The procedure lasted "
        "approximately 3 hours and cost $85,000. John was discharged from the hospital "
        "on January 20. Dr. Chen prescribed a regimen of aspirin and beta-blockers. "
        "He was asked to report back to the clinic by February 10 for a follow-up."
    ),
    "📰 News — International Affairs": (
        "The United Nations Security Council convened an emergency session in New York "
        "on Friday following escalating tensions between Russia and Ukraine near Kyiv. "
        "Secretary-General António Guterres called for immediate ceasefire negotiations. "
        "President Biden announced a $500 million aid package for Ukraine from the White "
        "House in Washington. French President Emmanuel Macron expressed strong support "
        "for a diplomatic resolution during a call with Chancellor Scholz in Berlin. "
        "The session, which lasted six hours, concluded without a formal resolution. "
        "Analysts say the next meeting is scheduled for November 2024."
    ),
}

with st.sidebar:
    if HAS_LOTTIE and LOTTIE_DATA:
        st_lottie(LOTTIE_DATA, height=140, key="sidebar_lottie", speed=0.7)
    else:
        st.markdown("""
        <div style="text-align:center;padding:24px 0 16px;">
          <div style="font-size:3rem">🧠</div>
          <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;
                      background:linear-gradient(135deg,#00e5ff,#a855f7);
                      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                      background-clip:text;letter-spacing:1px">CADIS</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;
                      color:#475569;letter-spacing:2px;margin-top:4px">
            RESEARCH PLATFORM v2.0
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="height:1px;background:linear-gradient(90deg,transparent,#1e2d40,transparent);margin:0 0 16px"></div>
    """, unsafe_allow_html=True)

    doc_choice = st.selectbox("Sample Document", list(SAMPLES.keys()), label_visibility="collapsed")
    doc_text   = st.text_area("Document", value=SAMPLES[doc_choice], height=240, label_visibility="collapsed")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    run_btn = st.button("⚡  RUN PIPELINE", type="primary", use_container_width=True)

    st.markdown("""
    <div style="height:1px;background:linear-gradient(90deg,transparent,#1e2d40,transparent);margin:16px 0 12px"></div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#475569;
                letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Architecture</div>
    """, unsafe_allow_html=True)
    sidebar_architecture()

    st.markdown("""
    <div style="height:1px;background:linear-gradient(90deg,transparent,#1e2d40,transparent);margin:16px 0 12px"></div>
    <div style="text-align:center;font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:#334155">
      BERT-NER · MiniLM · RoBERTa · DistilBART<br>
      <span style="color:#1e2d40">────────────────</span><br>
      spaCy · HuggingFace · sentence-transformers
    </div>
    """, unsafe_allow_html=True)

t1, t2, t3, t4, t5, t6 = st.tabs([
    "📝  Preprocessing",
    "🔢  Embeddings",
    "🏷️  NER + IE",
    "🔀  Ambiguity",
    "❓  QA Engine",
    "📋  Summary",
])

if not run_btn:
    with t1:
        welcome_screen()
    st.stop()

if not doc_text.strip():
    st.error("⚠️  Paste a document in the sidebar first.")
    st.stop()

from sklearn.metrics.pairwise import cosine_similarity

with st.status("🚀  Initializing CADIS pipeline…", expanded=True) as status:
    st.write("📝  **Module 1** — Loading spaCy `en_core_web_sm`…")
    nlp    = load_spacy()
    sp_doc = nlp(doc_text)
    tokens = [t for t in sp_doc if not t.is_space]
    sentences = [s.text.strip() for s in sp_doc.sents]
    st.write(f"   ✅  Tokenized `{len(tokens)}` tokens across `{len(sentences)}` sentences")

    st.write("🔢  **Module 2** — Loading `all-MiniLM-L6-v2` sentence encoder…")
    embedder   = load_embedder()
    valid_sents = [s for s in sentences if len(s) > 15]
    embeddings_arr  = embedder.encode(valid_sents)
    st.write(f"   ✅  Encoded `{len(valid_sents)}` sentences → `{embeddings_arr.shape[1]}`-dim vectors")

    st.write("🏷️  **Module 3** — Loading `dslim/bert-base-NER`…")
    ner_pipe   = load_ner_pipeline()
    bert_ents  = ner_pipe(doc_text)

    label_map  = {"PER": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION", "MISC": "MISC"}
    entities   = {k: [] for k in ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY", "MISC"]}
    for e in bert_ents:
        lbl = label_map.get(e["entity_group"], e["entity_group"])
        if lbl in entities:
            entities[lbl].append({"text": e["word"], "score": round(e["score"], 3)})
    for ent in sp_doc.ents:
        if ent.label_ in ("DATE", "TIME"):
            entities["DATE"].append({"text": ent.text, "score": 1.0})
        elif ent.label_ in ("MONEY", "CARDINAL", "PERCENT"):
            entities["MONEY"].append({"text": ent.text, "score": 1.0})
    for k in entities:
        seen, deduped = set(), []
        for item in entities[k]:
            if item["text"].lower() not in seen:
                seen.add(item["text"].lower())
                deduped.append(item)
        entities[k] = deduped

    relations = []
    for sent in sp_doc.sents:
        for tok in sent:
            if tok.dep_ == "ROOT" and tok.pos_ == "VERB":
                subj = [w for w in tok.lefts  if w.dep_ in ("nsubj", "nsubjpass")]
                obj  = [w for w in tok.rights if w.dep_ in ("dobj", "pobj", "attr", "acomp")]
                if subj and obj:
                    relations.append({"Subject": subj[0].text, "Verb": tok.text,
                                      "Object": obj[0].text,
                                      "Sentence": sent.text.strip()[:90] + "…"})
    total_ents = sum(len(v) for v in entities.values())
    st.write(f"   ✅  Extracted `{total_ents}` entities · `{len(relations)}` SVO relations")

    st.write("🔀  **Module 4** — Running ambiguity detection (dependency + embeddings)…")
    ambiguities_list = []
    for sent in sp_doc.sents:
        s_doc = nlp(sent.text)
        for tok in s_doc:
            if tok.pos_ == "ADP":
                head = tok.head
                alt  = [t for t in s_doc if t != head and t.pos_ in ("NOUN","VERB")
                        and 0 < abs(t.i - tok.i) < 5]
                if alt:
                    candidates = [head.text, alt[0].text]
                    q_e = embedder.encode([doc_text])
                    c_e = embedder.encode(candidates)
                    sc  = cosine_similarity(q_e, c_e)[0]
                    ambiguities_list.append({
                        "type": "PP Attachment", "emoji": "🔗",
                        "trigger": tok.text, "sentence": sent.text.strip(),
                        "description": f'"{tok.text}" could attach to **"{head.text}"** or **"{alt[0].text}"**',
                        "candidates": candidates,
                        "resolved": candidates[sc.argmax()],
                        "confidence": round(float(sc.max()), 3),
                    })
                    break
            if tok.pos_ == "PRON" and tok.text.lower() in ("he","she","it","they","his","her","their","its"):
                prev_nouns = [t for t in s_doc[:tok.i] if t.pos_ in ("NOUN","PROPN")]
                if len(prev_nouns) >= 2:
                    candidates = [p.text for p in prev_nouns[-3:]]
                    q_e = embedder.encode([doc_text])
                    c_e = embedder.encode(candidates)
                    sc  = cosine_similarity(q_e, c_e)[0]
                    ambiguities_list.append({
                        "type": "Anaphoric", "emoji": "👁️",
                        "trigger": tok.text, "sentence": sent.text.strip(),
                        "description": f'Pronoun **"{tok.text}"** may refer to **"{prev_nouns[-1].text}"** or **"{prev_nouns[-2].text}"**',
                        "candidates": candidates,
                        "resolved": candidates[sc.argmax()],
                        "confidence": round(float(sc.max()), 3),
                    })
                    break
    st.write(f"   ✅  Detected `{len(ambiguities_list)}` ambiguities · all resolved via contextual embeddings")

    st.write("❓  **Module 5** — Loading `deepset/minilm-uncased-squad2` QA model…")
    qa_pipe = load_qa_pipeline()
    auto_qs = [
        "Who is the main person mentioned?",
        "What organization is involved?",
        "Where did the event take place?",
        "When did this happen?",
        "What was the amount of money involved?",
        "Who made the announcement?",
        "What was the outcome?",
    ]
    qa_results = []
    for q in auto_qs:
        try:
            r = qa_pipe(question=q, context=doc_text)
            if r["score"] > 0.04:
                qa_results.append({"Question": q, "Answer": r["answer"],
                                   "Confidence": round(r["score"], 3),
                                   "_start": r["start"], "_end": r["end"]})
        except Exception:
            pass
    st.write(f"   ✅  Answered `{len(qa_results)}` auto-generated questions")

    st.write("📋  **Module 6** — Loading `sshleifer/distilbart-cnn-12-6` summarizer…")
    summarizer = load_summarizer()
    trunc_text = " ".join(doc_text.split()[:400])
    try:
        result   = summarizer(trunc_text, max_length=90, min_length=25, do_sample=False)
        exec_sum = result[0]["summary_text"]
    except Exception as e:
        exec_sum = f"Summarization error: {e}"

    scored = []
    for sent in sp_doc.sents:
        ent_score  = len(list(sent.ents)) * 2
        verb_score = sum(1 for t in sent if t.pos_ == "VERB")
        if len(sent.text.strip()) > 20:
            scored.append((sent.text.strip(), ent_score + verb_score))
    top_sents = [s for s, _ in sorted(scored, key=lambda x: x[1], reverse=True)[:4]]

    timeline = []
    for sent in sp_doc.sents:
        time_ents = [e for e in sent.ents if e.label_ in ("DATE","TIME")]
        if time_ents:
            timeline.append({"time": time_ents[0].text, "event": sent.text.strip()})

    st.write(f"   ✅  Executive summary generated · {len(top_sents)} key sentences · {len(timeline)} timeline events")

    status.update(label="✅  CADIS pipeline complete — all 6 modules ready", state="complete", expanded=False)

with t1:
    preprocessing.render(doc_text)

with t2:
    embeddings.render(doc_text, valid_sents=valid_sents, embeddings_arr=embeddings_arr)

with t3:
    ner_ie.render(doc_text, sp_doc=sp_doc, entities=entities, relations=relations)

with t4:
    ambiguity.render(doc_text, sp_doc=sp_doc, found_ambs=ambiguities_list)

with t5:
    qa_engine.render(doc_text, qa_results=qa_results)

with t6:
    summarizer_module.render(doc_text, exec_sum=exec_sum, top_sents=top_sents, timeline=timeline)
