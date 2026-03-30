import streamlit as st
import pandas as pd
from modules.utils import load_spacy, load_ner_pipeline

def render(doc_text):
    st.header("🏷️ Module 3 — Named Entity Recognition + Information Extraction")
    
    ner_pipe = load_ner_pipeline()
    nlp = load_spacy()
    
    with st.spinner("Running NER…"):
        bert_ents = ner_pipe(doc_text)
        sp_doc = nlp(doc_text)

    label_map = {"PER": "PERSON", "ORG": "ORGANIZATION", "LOC": "LOCATION", "MISC": "MISC"}
    entities  = {k: [] for k in ["PERSON", "ORGANIZATION", "LOCATION", "DATE", "MONEY", "MISC"]}

    for e in bert_ents:
        lbl = label_map.get(e["entity_group"], e["entity_group"])
        if lbl in entities:
            entities[lbl].append({"text": e["word"], "score": round(e["score"], 3)})

    for ent in sp_doc.ents:
        if ent.label_ in ("DATE", "TIME"):
            entities["DATE"].append({"text": ent.text, "score": 1.0})
        elif ent.label_ in ("MONEY", "CARDINAL", "PERCENT"):
            entities["MONEY"].append({"text": ent.text, "score": 1.0})

    # Deduplicate
    for k in entities:
        seen = set()
        deduped = []
        for item in entities[k]:
            if item["text"].lower() not in seen:
                seen.add(item["text"].lower())
                deduped.append(item)
        entities[k] = deduped

    present = {k: v for k, v in entities.items() if v}
    cols    = st.columns(max(len(present), 1))
    for i, (etype, ents) in enumerate(present.items()):
        cols[i].metric(etype, len(ents))

    st.subheader("🏷️ Extracted Entities")
    badge_cls = {"PERSON": "badge-per", "ORGANIZATION": "badge-org", "LOCATION": "badge-loc",
                 "DATE": "badge-date", "MONEY": "badge-mon", "MISC": "badge-misc"}
    for etype, ents in present.items():
        badges = "".join([f'<span class="badge {badge_cls.get(etype,"badge-misc")}">{e["text"]}</span>' for e in ents])
        st.markdown(f"**{etype}** &nbsp; {badges}", unsafe_allow_html=True)

    st.subheader("🔗 Relation Extraction — Who Did What")
    relations = []
    for sent in sp_doc.sents:
        for tok in sent:
            if tok.dep_ == "ROOT" and tok.pos_ == "VERB":
                subj = [w for w in tok.lefts  if w.dep_ in ("nsubj", "nsubjpass")]
                obj  = [w for w in tok.rights if w.dep_ in ("dobj", "pobj", "attr", "acomp")]
                if subj and obj:
                    relations.append({
                        "Subject": subj[0].text, "Relation": tok.text, "Object": obj[0].text
                    })

    if relations:
        st.dataframe(pd.DataFrame(relations), use_container_width=True)
    else:
        st.info("No clear SVO relations found.")

    st.markdown('<div class="info-card">✅ <b>Module 3 complete</b></div>', unsafe_allow_html=True)