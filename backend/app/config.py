"""All tunable configuration — single source for env-derived settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# ponytail: migration 0001 hardcodes this dim; change here + new migration to resize vectors
EMBEDDING_DIM = 1024


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://oce:oce@localhost:5432/oce"
    openrouter_api_key: str = ""
    embedding_dim: int = EMBEDDING_DIM
    demo_fallback: bool = False

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # LLM (used in M6+)
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # Ingestion / embeddings (M3, D-014)
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embed_batch_size: int = 32
    ocr_min_chars: int = 30
    chunk_target_tokens: int = 800

    # WO normalization thresholds (D-008) — human-tuned; do not auto-adjust
    # Calibrated 2026-07 against normalization audit: bge-large cosine range is
    # compressed; 0.60/0.05 yielded 52% unclassified vs ~12% designed. Human
    # decision per D-008; see DECISIONS.md D-008 + M3 audit.
    norm_threshold: float = 0.55
    norm_margin: float = 0.03
    normalization_score_threshold: float = 0.55
    normalization_margin_threshold: float = 0.03

    # Evidence Strength tiers (used in M4+)
    evidence_strength_strong: float = 8.0
    evidence_strength_moderate: float = 4.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
