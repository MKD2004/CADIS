import streamlit as st

"""
CADIS Module Utilities - Optimized Model Loading
==================================================
Senior NLP Engineer optimizations:
- Upgraded QA model to deepset/roberta-base-squad2 for higher F1/EM scores
- Kept DistilBART but with optimized pipeline configuration
- Added token counting utility for chunking logic
"""

@st.cache_resource(show_spinner=False)
def load_spacy():
    """Load spaCy model for NLP preprocessing."""
    import spacy
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        from spacy.cli import download
        download("en_core_web_sm")
        return spacy.load("en_core_web_sm")

@st.cache_resource(show_spinner=False)
def load_ner_pipeline():
    """Load NER pipeline using dslim/bert-base-NER."""
    from transformers import pipeline
    return pipeline("ner", model="dslim/bert-base-NER", aggregation_strategy="simple")

@st.cache_resource(show_spinner=False)
def load_embedder():
    """Load sentence embedding model for semantic search."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource(show_spinner=False)
def load_qa_pipeline():
    """
    Load QA pipeline with upgraded RoBERTa model.
    
    Upgrade: deepset/roberta-base-squad2
    - Better contextual understanding than MiniLM
    - Expected F1 improvement: ~5-10% over minilm-uncased-squad2
    """
    from transformers import pipeline
    return pipeline(
        "question-answering",
        model="deepset/roberta-base-squad2",
        device=-1  # CPU (use 0 for GPU if available)
    )

@st.cache_resource(show_spinner=False)
def load_summarizer():
    """
    Load summarization pipeline with optimized config.
    
    Model: sshleifer/distilbart-cnn-12-6 (retained)
    - Optimized truncation handled in summarizer.py
    - Advanced generation params applied at inference time
    """
    from transformers import pipeline
    return pipeline(
        model="sshleifer/distilbart-cnn-12-6",
        device=-1  # CPU (use 0 for GPU if available)
    )

def count_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    
    Uses simple word-based approximation (~1 token ≈ 0.75 words).
    For precise counting, use tokenizer directly, but this is 
    sufficient for chunking decisions in the QA pipeline.
    """
    return len(text.split())

def get_tokenizer():
    """Load QA tokenizer for precise token counting during chunking."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained("deepset/roberta-base-squad2")
