"""Add failure_modes.family — hierarchical taxonomy for the cross-family margin
rule (D-017).

Append-only. D-016's reasoning_runs table lands in migration 0003 (M6).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "failure_modes",
        sa.Column("family", sa.Text(), nullable=False, server_default="general"),
    )


def downgrade() -> None:
    op.drop_column("failure_modes", "family")
