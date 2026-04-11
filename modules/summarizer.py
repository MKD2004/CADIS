import streamlit as st
from modules.utils import load_summarizer, load_spacy, count_tokens

"""
CADIS Summarizer - Advanced Generation with Beam Search
=========================================================
Senior NLP Engineer optimizations:
- Retained dynamic length calculation for short text safety
- Added num_beams=4 for better beam search decoding
- Added early_stopping=True to prevent incomplete summaries
- Added no_repeat_ngram_size=3 to prevent repetitive phrases
- Added length_penalty for controlling summary verbosity
"""

# Generation hyperparameters (tuned for ROUGE improvement)
DEFAULT_BEAM_SIZE = 4
DEFAULT_NO_REPEAT_NGRAM = 3
DEFAULT_LENGTH_PENALTY = 2.0  # 2.0 encourages longer, more informative output

MAX_INPUT_TOKENS = 1024  # Model absolute max token limit


def get_summary(doc_text: str):
    """
    Bridge function for cadis_evaluator.py with advanced generation.
    
    Implements:
    1. Strict token truncation before hitting pipeline
    2. Bulletproof generation parameters for high-quality output
    3. Beam search with aggressive settings
    
    Args:
        doc_text: Input document to summarize
    
    Returns:
        Generated summary string
    """
    summarizer = load_summarizer()
    
    word_count = len(doc_text.split())
    input_len = word_count
    
    # Guard: Return original if text is too short to summarize
    if input_len < 15:
        truncated = " ".join(doc_text.split()[:150])
        return truncated
    
    # STRICT TRUNCATION: Truncate input BEFORE it hits the model
    # Use word count as proxy for tokens (1 token ≈ 0.75 words)
    max_input_words = int(MAX_INPUT_TOKENS * 0.75)
    truncated_text = " ".join(doc_text.split()[:max_input_words])
    
    # Dynamic length calculation
    # max_length: 60% of input, capped at 142 (model limit minus buffer)
    # min_length: 20% of input, minimum 30 words
    dynamic_max = min(142, max(30, int(input_len * 0.6)))
    dynamic_min = min(45, max(10, int(input_len * 0.2)))
    
    try:
        # Advanced generation parameters for improved ROUGE scores:
        result = summarizer(
            truncated_text,
            max_length=dynamic_max,
            min_length=dynamic_min,
            do_sample=False,  # False = beam search (deterministic)
            num_beams=4,  # Beam search with 4 beams
            length_penalty=2.0,  # 2.0 encourages longer output
            no_repeat_ngram_size=3,  # Block 3-gram repeats
            early_stopping=True,  # Stop when all beams produce EOS
            truncation=True  # Explicit truncation for safety
        )
        return result[0]["summary_text"]
    
    except Exception as e:
        print(f"Summarizer Error: {e}")
        return ""


def render(doc_text):
    """Streamlit render function for Module 6 - Summarizer."""
    st.header("📋 Module 6 — Intelligent Summary Generator")
    
    summarizer = load_summarizer()
    nlp = load_spacy()
    sp_doc = nlp(doc_text)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📌 Executive Summary")
        with st.spinner("Generating..."):
            exec_sum = get_summary(doc_text)
        
        if "Error" in exec_sum or not exec_sum:
            st.error("Could not generate summary.")
        else:
            st.markdown(
                f'<div style="background:#2b2b2b;border-radius:10px;padding:18px;'
                f'border-left:5px solid #302b63;color:white;">{exec_sum}</div>',
                unsafe_allow_html=True
            )
        
        # Show generation params used
        st.caption(
            f"Params: beams={DEFAULT_BEAM_SIZE}, "
            f"no_repeat_ngram={DEFAULT_NO_REPEAT_NGRAM}"
        )

    with col_right:
        st.subheader("🔹 Key Sentence Extraction")
        scored = []
        for sent in sp_doc.sents:
            # Score: 2 points per named entity, 1 point per verb
            score = (len(list(sent.ents)) * 2) + sum(1 for t in sent if t.pos_ == "VERB")
            if len(sent.text.strip()) > 20:
                scored.append((sent.text.strip(), score))
        
        top = sorted(scored, key=lambda x: x[1], reverse=True)[:4]
        for s, _ in top:
            st.markdown(f"• {s}")

    st.markdown('<div class="info-card">✅ <b>Module 6 complete</b></div>', unsafe_allow_html=True)
    st.balloons()
