FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_RETRIES=5 PIP_TIMEOUT=120

# ponytail: psycopg[binary] needs no apt build deps
COPY pyproject.toml ./
COPY app ./app

# ponytail: CPU-only torch in its own layer so a pip flake retries cheaply (NFR-6)
RUN pip install --no-cache-dir --retries 5 --timeout 120 \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --retries 5 --timeout 120 -e ".[dev]" && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"

ENV PYTHONPATH=/app
