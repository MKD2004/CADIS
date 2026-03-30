import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
from modules.utils import load_spacy, load_embedder

def render(doc_text):
    st.header("🔀 Module 4 — Ambiguity Detection & Resolution")
    
    nlp = load_spacy()
    embedder = load_embedder()
    doc = nlp(doc_text)
    found_ambs = []

    for sent in doc.sents:
        s_doc = nlp(sent.text)
        for tok in s_doc:
            if tok.pos_ == "ADP":
                head = tok.head
                alt  = [t for t in s_doc if t != head and t.pos_ in ("NOUN", "VERB") and 0 < abs(t.i - tok.i) < 5]
                if alt:
                    candidates = [head.text, alt[0].text]
                    q_e = embedder.encode([doc_text])
                    c_e = embedder.encode(candidates)
                    sc  = cosine_similarity(q_e, c_e)[0]
                    found_ambs.append({
                        "type": "PP Attachment", "trigger": tok.text, "sentence": sent.text.strip(),
                        "candidates": candidates, "resolved": candidates[sc.argmax()],
                        "confidence": round(float(sc.max()), 3)
                    })
                    break

    st.subheader("📊 Ambiguities Found in Document")
    if found_ambs:
        for i, a in enumerate(found_ambs):
            with st.expander(f"⚠️ {a['type']} — trigger: \"{a['trigger']}\"", expanded=(i == 0)):
                st.markdown(f"**Sentence:** _{a['sentence']}_")
                st.markdown(f"**Candidates:** {', '.join([f'`{c}`' for c in a['candidates']])}")
                st.markdown(f'<div class="amb-resolved">✅ <b>Resolved to:</b> <code>{a["resolved"]}</code> (Confidence: {a["confidence"]})</div>', unsafe_allow_html=True)
    else:
        st.info("No strong structural ambiguities detected.")

    st.markdown('<div class="info-card">✅ <b>Module 4 complete</b></div>', unsafe_allow_html=True)