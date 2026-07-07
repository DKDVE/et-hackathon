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

    # M6 reasoning layer gate (P5). MUST default false: nothing may crash when it
    # is off — M5 serves a deterministic-only dossier and degrades honestly.
    reasoning_enabled: bool = False

    # CORS
    frontend_origin: str = "http://localhost:5173"

    # LLM (M6, D-009/P7)
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2
    llm_temperature: float = 0.2
    llm_models: dict[str, str] = {
        # Quality-critical root-cause synthesis — keep on Sonnet (D-009).
        "analysis": "anthropic/claude-sonnet-4.6",
        # Structured action/safety output; Haiku sufficient with slim context (M6.1).
        "recommendation": "anthropic/claude-haiku-4.5",
        # Per-claim verdict JSON; Haiku sufficient with claim-scoped input (M6.1).
        "validation": "anthropic/claude-haiku-4.5",
        # Contextual Q&A (FR-9, M8).
        "chat": "anthropic/claude-haiku-4.5",
    }
    llm_max_tokens: dict[str, int] = {
        "analysis": 900,
        "recommendation": 1400,
        "validation": 900,
        "chat": 600,
    }

    # D-021 — downtime cost for pattern impact display (₹/hr).
    downtime_cost_per_hour_inr: int = 450_000

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

    # OCE assembler — retrieval caps (TDD §5, D-015). Semantic top-k per bucket.
    retrieval_manual_k: int = 12
    retrieval_sop_k: int = 8
    retrieval_reports_k: int = 6
    # D-015 lexical channel: lexical-only hits may exceed a bucket cap by ≤ this.
    retrieval_lexical_overflow: int = 4
    # OCE assembler — history / sister caps (TDD §5).
    failure_history_cap: int = 30
    sister_incidents_cap: int = 20

    # Evidence Strength (TDD §6, D-003/P8). Formula constants — all hand-computable.
    #   score = min(count, cap_count) * w_count
    #         + distinct_source_types    * w_source_type
    #         + (w_recency_near if newest < recency_threshold_months else w_recency_far)
    #         + min(distinct_sister_assets, cap_sister) * w_sister
    evidence_strength_strong: float = 8.0
    evidence_strength_moderate: float = 4.0
    evidence_w_count: float = 1.0
    evidence_w_source_type: float = 1.5
    evidence_w_recency_near: float = 2.0
    evidence_w_recency_far: float = 0.5
    evidence_w_sister: float = 1.5
    evidence_cap_count: int = 4
    evidence_cap_sister: int = 3
    evidence_recency_threshold_months: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
