# CADIS: Context-Aware Document Intelligence System 🧠

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-orange?style=for-the-badge&logo=huggingface&logoColor=white)

CADIS is a comprehensive, 6-module Natural Language Processing (NLP) pipeline and research platform. It integrates standard transformer tasks (Extractive QA and Abstractive Summarization) with a novel, zero-shot semantic approach to resolving structural ambiguities (like Prepositional Phrase attachments). 

The platform features a visually stunning, dark-mode Streamlit dashboard for real-time document analysis and a decoupled benchmarking engine for rigorous academic evaluation.

---

## 🏗️ System Architecture

CADIS processes documents sequentially through 6 distinct modules:

1. **Preprocessing:** Tokenization, lemmatization, and POS tagging using `spaCy`.
2. **Semantic Embeddings:** Document and sentence-level dense vector encoding using `all-MiniLM-L6-v2` for similarity heatmaps and semantic search.
3. **NER & Information Extraction:** Entity recognition via `dslim/bert-base-NER` and rule-based Subject-Verb-Object (SVO) relation extraction.
4. **Ambiguity Resolution (Novel Contribution):** Detects PP-attachment and anaphoric ambiguities, resolving them using zero-shot cosine similarity against contextual embeddings.
5. **QA Engine:** Extractive question answering powered by `deepset/minilm-uncased-squad2`.
6. **Intelligent Summarization:** Abstractive executive summaries via `sshleifer/distilbart-cnn-12-6`, combined with entity-dense key sentence extraction.

---

## 🚀 Installation & Setup

### Prerequisites
Ensure you have Python 3.9+ installed on your system.

### 1. Clone the Repository
```bash
git clone [https://github.com/MKD2004/CADIS.git](https://github.com/MKD2004/CADIS.git)
cd CADIS
