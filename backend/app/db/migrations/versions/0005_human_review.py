"""D-023: human-override provenance columns on work_orders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_human_verdict = sa.Enum(
    "confirmed",
    "corrected",
    "unclassifiable",
    name="human_verdict",
    create_type=True,
)


def upgrade() -> None:
    _human_verdict.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "work_orders",
        sa.Column("human_failure_mode_id", sa.Integer(), sa.ForeignKey("failure_modes.id"), nullable=True),
    )
    op.add_column("work_orders", sa.Column("human_verdict", _human_verdict, nullable=True))
    op.add_column(
        "work_orders",
        sa.Column("human_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("work_orders", "human_reviewed_at")
    op.drop_column("work_orders", "human_verdict")
    op.drop_column("work_orders", "human_failure_mode_id")
    _human_verdict.drop(op.get_bind(), checkfirst=True)
