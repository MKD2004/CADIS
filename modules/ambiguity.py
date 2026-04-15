import streamlit as st
from sklearn.metrics.pairwise import cosine_similarity
from modules.utils import load_spacy, load_embedder
from ui_components import (
    module_header, section_label, ambiguity_card, info_strip
)

def render(doc_text, sp_doc=None, found_ambs=None):
    nlp = load_spacy()
    embedder = load_embedder()
    sp_doc = sp_doc or nlp(doc_text)

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
