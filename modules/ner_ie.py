import streamlit as st
from modules.utils import load_spacy, load_ner_pipeline
from ui_components import (
    module_header, section_label, render_entities, relation_row, info_strip
)

try:
    from annotated_text import annotated_text
    HAS_ANNOTATED = True
except ImportError:
    HAS_ANNOTATED = False

def render(doc_text, sp_doc=None, entities=None, relations=None):
    nlp = load_spacy()
    sp_doc = sp_doc or nlp(doc_text)
    
    if entities is None:
        ner_pipe = load_ner_pipeline()
        bert_ents = ner_pipe(doc_text)

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
    
    if relations is None:
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

    module_header("🏷️", "icon-amber",
                  "Named Entity Recognition + Information Extraction",
                  "UNIT 1 · NER · Relation Extraction · Event Extraction · JSON Structured Output")

    present = {k: v for k, v in entities.items() if v}
    cols    = st.columns(max(len(present), 1))
    for i, (etype, ents) in enumerate(present.items()):
        cols[i].metric(etype, len(ents))

    section_label("Annotated Text — Entities in Context")
    if HAS_ANNOTATED:
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
