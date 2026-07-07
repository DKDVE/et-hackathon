"""reasoning_runs tracing (D-016) + fallback SSE cache (P9, M6).

Append-only. reasoning_runs records every node execution; reasoning_fallback_cache
stores successful SSE sequences for DEMO_FALLBACK replay.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_reasoning_run_status = postgresql.ENUM(
    "ok", "repaired", "failed", name="reasoning_run_status", create_type=False
)


def upgrade() -> None:
    _reasoning_run_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "reasoning_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dossier_id",
            sa.Integer(),
            sa.ForeignKey("dossiers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", _reasoning_run_status, nullable=False),
        sa.Column("output_digest", sa.Text(), nullable=False),
    )
    op.create_index("ix_reasoning_runs_dossier_id", "reasoning_runs", ["dossier_id"])

    op.create_table(
        "reasoning_fallback_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cache_key", sa.String(128), nullable=False, unique=True),
        sa.Column("event_fingerprint", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(), nullable=False),
        sa.Column("events", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_reasoning_fallback_cache_lookup",
        "reasoning_fallback_cache",
        ["event_fingerprint", "content_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_reasoning_fallback_cache_lookup", "reasoning_fallback_cache")
    op.drop_table("reasoning_fallback_cache")
    op.drop_index("ix_reasoning_runs_dossier_id", "reasoning_runs")
    op.drop_table("reasoning_runs")
    _reasoning_run_status.drop(op.get_bind(), checkfirst=True)
