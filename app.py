import streamlit as st
import time

# Import your custom modules
from modules import preprocessing, embeddings, ner_ie, ambiguity, qa_engine, summarizer

# ─────────────────────────────────────────
#  PAGE CONFIG & CSS (Professional UI)
# ─────────────────────────────────────────
# Emojis removed, layout kept wide
st.set_page_config(page_title="CADIS", layout="wide")

st.markdown("""
<style>
/* Smooth fade-in animation for content */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.6s ease-out forwards;
}

/* Header Styling */
.cadis-header { 
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); 
    padding: 24px 30px; 
    border-radius: 8px; 
    margin-bottom: 24px; 
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.cadis-header h1 { color: #ffffff; margin: 0; font-size: 2.2rem; font-weight: 600; letter-spacing: 0.5px;}
.cadis-header p  { color: #aab4cc; margin: 6px 0 0; font-size: 1.1rem;}

/* Interactive Element Hover Effects */
.info-card, .answer-box, .amb-resolved {
    transition: all 0.3s ease;
}
.info-card:hover, .answer-box:hover, .amb-resolved:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.08);
}

/* Component Styling */
.info-card { background: #f7f9fc; border-radius: 8px; padding: 16px 20px; border-left: 4px solid #302b63; margin: 10px 0; color: #1e1e1e !important; }
.answer-box { background: #f8fbff; border: 1px solid #d0e2f3; border-radius: 8px; padding: 20px; margin: 12px 0; color: #1e1e1e !important; }
.answer-box h3 { color: #2c3e50 !important; margin: 0 0 8px; font-size: 1.2rem; }
.answer-text { font-size: 1.1rem; font-weight: 500; color: #34495e !important; }
.amb-resolved { background: #f9fbf9; border: 1px solid #c8e6c9; border-radius: 8px; padding: 10px 14px; margin-top: 8px; color: #1e1e1e !important; }

/* Badges */
.badge { display: inline-block; padding: 4px 10px; border-radius: 4px; margin: 3px 3px 3px 0; font-size: 0.75rem; font-weight: 600; color: #fff !important; text-transform: uppercase; letter-spacing: 0.5px;}
.badge-per { background: #e74c3c; } .badge-org { background: #2980b9; } .badge-loc { background: #27ae60; }
.badge-date { background: #8e44ad; } .badge-mon { background: #d35400; } .badge-misc { background: #7f8c8d; }

/* Clean up Streamlit native tab styling */
.stTabs [data-baseweb="tab-list"] { gap: 4px; }
.stTabs [data-baseweb="tab"] { padding: 10px 16px; transition: background-color 0.2s ease; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="cadis-header fade-in"><h1>CADIS</h1><p>Context-Aware Document Intelligence System</p></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────
SAMPLES = {
    "Legal — Corporate Acquisition": "Apple Inc. announced on Tuesday that it will acquire AI startup NeuralBase for $2.5 billion. The deal, expected to close by March 2025, was confirmed by CEO Tim Cook at a press conference held in San Francisco. Legal experts in New York warned that the acquisition might face regulatory scrutiny from the European Commission in Brussels. Sarah Johnson, the CFO, stated that the merger would help Apple expand its AI capabilities significantly. However, she noted that the board had approved the deal on Monday morning after reviewing the contract she was carrying."
}

st.sidebar.title("Document Input")
doc_choice = st.sidebar.selectbox("Choose a sample:", list(SAMPLES.keys()))
doc_text = st.sidebar.text_area("Or paste your own document:", value=SAMPLES[doc_choice], height=260)
run_btn = st.sidebar.button("Run Full CADIS Pipeline", type="primary", use_container_width=True)

# ─────────────────────────────────────────
#  MAIN EXECUTION
# ─────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs([
    "1. Preprocessing", "2. Embeddings", "3. NER + IE", 
    "4. Ambiguity", "5. QA Engine", "6. Summary"
])

if run_btn and doc_text.strip():
    # Initialize Progress UI
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Step 1
    status_text.markdown("**Status:** Initializing Preprocessing...")
    time.sleep(0.2) # Minor delay for UI feedback
    with t1: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        preprocessing.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(16)

    # Step 2
    status_text.markdown("**Status:** Generating Vector Embeddings...")
    time.sleep(0.2)
    with t2: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        embeddings.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(33)

    # Step 3
    status_text.markdown("**Status:** Extracting Named Entities...")
    time.sleep(0.2)
    with t3: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        ner_ie.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(50)

    # Step 4
    status_text.markdown("**Status:** Resolving Contextual Ambiguity...")
    time.sleep(0.2)
    with t4: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        ambiguity.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(66)

    # Step 5
    status_text.markdown("**Status:** Initializing QA Engine...")
    time.sleep(0.2)
    with t5: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        qa_engine.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(83)

    # Step 6
    status_text.markdown("**Status:** Generating Final Summary...")
    time.sleep(0.2)
    with t6: 
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        summarizer.render(doc_text)
        st.markdown('</div>', unsafe_allow_html=True)
    progress_bar.progress(100)

    # Completion State
    status_text.markdown("**Status:** Pipeline Execution Complete.")
    time.sleep(1.5)
    status_text.empty() # Clears the status text
    progress_bar.empty() # Clears the progress bar to keep UI clean

elif not run_btn:
    with t1: st.info("Select a document and click 'Run Full CADIS Pipeline' in the sidebar.")