FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# Pre-download all models at build time so cold starts are instant
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
RUN python -c "from transformers import pipeline; pipeline('ner', model='dslim/bert-base-NER', aggregation_strategy='simple')"
RUN python -c "from transformers import pipeline; pipeline('question-answering', model='deepset/minilm-uncased-squad2')"
RUN python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; AutoTokenizer.from_pretrained('sshleifer/distilbart-cnn-12-6'); AutoModelForSeq2SeqLM.from_pretrained('sshleifer/distilbart-cnn-12-6')"

COPY api_server.py .

EXPOSE 7860

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "7860"]
