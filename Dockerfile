FROM python:3.11-slim

WORKDIR /app

# CPU-only torch (~200MB vs ~2.5GB for the default GPU build). Installed before
# requirements.txt so pip doesn't pull the CUDA wheels as a transitive dep.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

# NOTE: model weights are deliberately NOT pre-downloaded here. Doing so pushed
# the HuggingFace Spaces image build past its timeout. Models are fetched on
# first request instead, which is why the first call after a cold start is slow.
COPY api_server.py .

EXPOSE 7860

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "7860"]
