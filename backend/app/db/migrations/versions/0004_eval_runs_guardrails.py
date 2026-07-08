"""eval_runs persistence (M11) + dossiers.guardrail_stats."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_eval_suite = postgresql.ENUM(
    "golden",
    "groundedness",
    "normalization",
    "prose_id",
    "timing",
    name="eval_suite",
    create_type=False,
)
_eval_status = postgresql.ENUM(
    "pass",
    "warn",
    "fail",
    name="eval_status",
    create_type=False,
)


def upgrade() -> None:
    _eval_suite.create(op.get_bind(), checkfirst=True)
    _eval_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("suite", _eval_suite, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("git_ref", sa.Text(), nullable=False),
        sa.Column("prompt_versions", postgresql.JSONB(), nullable=False),
        sa.Column("status", _eval_status, nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_eval_runs_suite_started", "eval_runs", ["suite", "started_at"])

    op.add_column("dossiers", sa.Column("guardrail_stats", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("dossiers", "guardrail_stats")
    op.drop_index("ix_eval_runs_suite_started", "eval_runs")
    op.drop_table("eval_runs")
    _eval_status.drop(op.get_bind(), checkfirst=True)
    _eval_suite.drop(op.get_bind(), checkfirst=True)
