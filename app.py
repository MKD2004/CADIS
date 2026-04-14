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

# ─────────────────────────────────────────
#  PAGE CONFIG  (must be first st call)
# ─────────────────────────────────────────
st.set_page_config(
    page_title="CADIS · Research Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ─────────────────────────────────────────
#  LOTTIE  (graceful fallback)
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
#  ANNOTATED TEXT  (graceful fallback)
# ─────────────────────────────────────────
try:
    from annotated_text import annotated_text
    HAS_ANNOTATED = True
except ImportError:
    HAS_ANNOTATED = False

# ─────────────────────────────────────────
#  CACHED MODEL LOADERS
# ─────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_spacy():
    import spacy
    return spacy.load("en_core_web_sm")

@st.cache_resource(show_spinner=False)
def load_ner_pipeline():
    from transformers import pipeline
    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

@st.cache_resource(show_spinner=False)
def load_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource(show_spinner=False)
def load_qa_pipeline():
    from transformers import pipeline
    return pipeline("question-answering", model="deepset/minilm-uncased-squad2")

@st.cache_resource(show_spinner=False)
def load_summarizer():
    from transformers import pipeline
    return pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# ─────────────────────────────────────────
#  SAMPLE DOCUMENTS
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    # Lottie or static header
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

# ─────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📝  Preprocessing",
    "🔢  Embeddings",
    "🏷️  NER + IE",
    "🔀  Ambiguity",
    "❓  QA Engine",
    "📋  Summary",
])

# ─────────────────────────────────────────
#  WELCOME STATE
# ─────────────────────────────────────────
if not run_btn:
    with t1:
        welcome_screen()
    st.stop()

if not doc_text.strip():
    st.error("⚠️  Paste a document in the sidebar first.")
    st.stop()

# ══════════════════════════════════════════════════════════════
#  TERMINAL-STYLE STATUS LOADER
# ══════════════════════════════════════════════════════════════
with st.status("🚀  Initializing CADIS pipeline…", expanded=True) as status:

    # ── Step 1 ──
    st.write("📝  **Module 1** — Loading spaCy `en_core_web_sm`…")
    nlp    = load_spacy()
    sp_doc = nlp(doc_text)
    tokens = [t for t in sp_doc if not t.is_space]
    sentences = [s.text.strip() for s in sp_doc.sents]
    st.write(f"   ✅  Tokenized `{len(tokens)}` tokens across `{len(sentences)}` sentences")

    # ── Step 2 ──
    st.write("🔢  **Module 2** — Loading `all-MiniLM-L6-v2` sentence encoder…")
    embedder   = load_embedder()
    valid_sents = [s for s in sentences if len(s) > 15]
    from sklearn.metrics.pairwise import cosine_similarity
    embeddings  = embedder.encode(valid_sents)
    st.write(f"   ✅  Encoded `{len(valid_sents)}` sentences → `{embeddings.shape[1]}`-dim vectors")

    # ── Step 3 ──
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

    # ── Step 4 ──
    st.write("🔀  **Module 4** — Running ambiguity detection (dependency + embeddings)…")
    found_ambs = []
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
                    found_ambs.append({
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
                    found_ambs.append({
                        "type": "Anaphoric", "emoji": "👁️",
                        "trigger": tok.text, "sentence": sent.text.strip(),
                        "description": f'Pronoun **"{tok.text}"** may refer to **"{prev_nouns[-1].text}"** or **"{prev_nouns[-2].text}"**',
                        "candidates": candidates,
                        "resolved": candidates[sc.argmax()],
                        "confidence": round(float(sc.max()), 3),
                    })
                    break
    st.write(f"   ✅  Detected `{len(found_ambs)}` ambiguities · all resolved via contextual embeddings")

    # ── Step 5 ──
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

    # ── Step 6 ──
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

# ══════════════════════════════════════════════════════════════
#  MODULE 1 — PREPROCESSING
# ══════════════════════════════════════════════════════════════
with t1:
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

# ══════════════════════════════════════════════════════════════
#  MODULE 2 — EMBEDDINGS
# ══════════════════════════════════════════════════════════════
with t2:
    module_header("🔢", "icon-purple",
                  "Semantic Embedding Module",
                  "UNIT 1 · One-hot vs Dense · Distributional Semantics · Contextual Embeddings (BERT)")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sentences Encoded", len(valid_sents))
    c2.metric("Embedding Dim",     embeddings.shape[1])
    c3.metric("Model",             "MiniLM-L6-v2")

    section_label("Embedding Vectors Preview")
    emb_df = pd.DataFrame({
        "Sentence":  [s[:55] + "…" if len(s) > 55 else s for s in valid_sents],
        "dim[0]":    embeddings[:, 0].round(4),
        "dim[1]":    embeddings[:, 1].round(4),
        "dim[2]":    embeddings[:, 2].round(4),
        "L2 Norm":   np.linalg.norm(embeddings, axis=1).round(4),
    })
    st.dataframe(emb_df, use_container_width=True)

    section_label("Sentence Similarity Heatmap")
    sim_matrix = cosine_similarity(embeddings)
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
        scores = cosine_similarity(q_emb, embeddings)[0]
        ranked = sorted(zip(valid_sents, scores.tolist()), key=lambda x: x[1], reverse=True)
        for i, (sent, score) in enumerate(ranked[:3]):
            search_bubble(i + 1, sent, score)

    info_strip("Module 2 complete — 384-dim dense embeddings computed; cosine similarity matrix and semantic retrieval operational.")

# ══════════════════════════════════════════════════════════════
#  MODULE 3 — NER + IE
# ══════════════════════════════════════════════════════════════
with t3:
    module_header("🏷️", "icon-amber",
                  "Named Entity Recognition + Information Extraction",
                  "UNIT 1 · NER · Relation Extraction · Event Extraction · JSON Structured Output")

    present = {k: v for k, v in entities.items() if v}
    cols    = st.columns(max(len(present), 1))
    for i, (etype, ents) in enumerate(present.items()):
        cols[i].metric(etype, len(ents))

    section_label("Annotated Text — Entities in Context")
    if HAS_ANNOTATED:
        # Build annotated_text tuples by scanning sp_doc
        ann_parts = []
        last = 0
        ent_list = [(e.start_char, e.end_char, e.text, e.label_) for e in sp_doc.ents
                    if e.label_ in ("PERSON","ORG","GPE","LOC","DATE","TIME","MONEY","EVENT")]
        label_remap = {"ORG": "ORGANIZATION", "GPE": "LOCATION", "LOC": "LOCATION",
                       "TIME": "DATE", "EVENT": "MISC"}
        ent_color_map = {
            "PERSON": "#f59e0b", "ORGANIZATION": "#a855f7",
            "LOCATION": "#10b981", "DATE": "#3b82f6",
            "MONEY": "#00e5ff", "MISC": "#64748b",
        }
        for start, end, text, label in sorted(ent_list, key=lambda x: x[0]):
            if start > last:
                ann_parts.append(doc_text[last:start])
            canon = label_remap.get(label, label)
            color = ent_color_map.get(canon, "#64748b")
            ann_parts.append((text, canon, color))
            last = end
        if last < len(doc_text):
            ann_parts.append(doc_text[last:])
        st.markdown('<div style="background:#0d1117;border:1px solid #1e2d40;border-radius:12px;padding:20px;">', unsafe_allow_html=True)
        annotated_text(*ann_parts)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        section_label("Extracted Entities")
        render_entities(present)

    section_label("Relation Extraction — Subject → Verb → Object")
    if relations:
        rel_html = ""
        for r in relations[:8]:
            rel_html += relation_row(r["Subject"], r["Verb"], r["Object"])
        st.markdown(rel_html, unsafe_allow_html=True)
    else:
        st.info("No clear SVO triples found. Try a different document.")

    section_label("Structured JSON Output")
    ie_json = {
        "document_entities": {k: v for k, v in entities.items() if v},
        "relations": relations[:5],
        "stats": {
            "total_entities":  sum(len(v) for v in entities.values()),
            "total_relations": len(relations),
        },
    }
    st.json(ie_json)

    info_strip("Module 3 complete — BERT-NER extracted + annotated entities; dependency SVO pipeline produced structured JSON.")

# ══════════════════════════════════════════════════════════════
#  MODULE 4 — AMBIGUITY
# ══════════════════════════════════════════════════════════════
with t4:
    module_header("🔀", "icon-amber",
                  "Ambiguity Detection & Resolution",
                  "UNIT 1 · PP-Attachment · Anaphoric · Lexical · Semantic — Novel Research Contribution")

    section_label("Live Ambiguity Tester")
    test_input = st.text_input(
        "Enter any sentence to test for structural ambiguity:",
        "I saw the man with binoculars on the roof",
        placeholder="Try: 'She gave the dog a bone in the kitchen'",
    )
    if test_input:
        t_doc    = nlp(test_input)
        detected = []
        for tok in t_doc:
            if tok.pos_ == "ADP":
                head = tok.head
                alt  = [t for t in t_doc if t != head and t.pos_ in ("NOUN","VERB")
                        and 0 < abs(t.i - tok.i) < 5]
                if alt:
                    detected.append(
                        f'⚠️ **PP-Attachment ambiguity** detected: '
                        f'`"{tok.text}"` could attach to `"{head.text}"` or `"{alt[0].text}"`'
                    )
        if detected:
            for d in detected:
                st.warning(d)
        else:
            st.success("✅ No structural ambiguity detected.")

    section_label("Ambiguities Found in Document")
    if found_ambs:
        for i, a in enumerate(found_ambs):
            ambiguity_card(a, i)
    else:
        st.markdown("""
        <div class="glass-card amber-glow" style="text-align:center;padding:40px">
          <div style="font-size:2rem;margin-bottom:12px">🔍</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;color:#64748b">
            No strong structural ambiguities auto-detected.<br>
            Use the tester above with classic examples:
          </div>
          <div style="margin-top:16px;font-family:'JetBrains Mono',monospace;font-size:0.78rem;color:#94a3b8">
            "She saw the man with the telescope"<br>
            "He told John that he was wrong"<br>
            "The chicken is ready to eat"<br>
            "Visiting relatives can be boring"
          </div>
        </div>
        """, unsafe_allow_html=True)

    info_strip("Module 4 complete — ambiguities detected via dependency parsing; resolved using contextual embedding similarity. Novel contribution — no baseline LLM reports this.")

# ══════════════════════════════════════════════════════════════
#  MODULE 5 — QA ENGINE
# ══════════════════════════════════════════════════════════════
with t5:
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

# ══════════════════════════════════════════════════════════════
#  MODULE 6 — SUMMARY
# ══════════════════════════════════════════════════════════════
with t6:
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
