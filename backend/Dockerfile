FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*


    WORKDIR /app

# ponytail: psycopg[binary] needs no apt build deps
COPY pyproject.toml ./
COPY app ./app
# ponytail: CPU-only torch keeps the image ~2GB not ~8GB; embeddings are CPU inference (D-014)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -e ".[dev]" && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"

ENV PYTHONPATH=/app
