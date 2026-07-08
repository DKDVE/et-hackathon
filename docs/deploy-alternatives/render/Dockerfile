# Render deploy entrypoint (repo root). Local demo uses backend/Dockerfile via compose.
# Canonical recipe: backend/Dockerfile.prod (identical).

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PIP_RETRIES=5 PIP_TIMEOUT=120

COPY backend/pyproject.toml ./
COPY backend/app ./app

RUN pip install --no-cache-dir --retries 5 --timeout 120 \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --retries 5 --timeout 120 -e ".[dev]" && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-large-en-v1.5')"

COPY dataset/rendered /dataset/rendered
COPY dataset/design /dataset/design
COPY dataset/generators /dataset/generators
COPY scripts /scripts

ENV PYTHONPATH=/app
ENV DATASET_DIR=/dataset

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
