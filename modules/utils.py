import streamlit as st

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
