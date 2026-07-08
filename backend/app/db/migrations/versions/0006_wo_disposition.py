"""D-024: routine-closure disposition on work_orders."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_wo_disposition = sa.Enum(
    "failure",
    "routine",
    name="wo_disposition",
    create_type=True,
)


def upgrade() -> None:
    _wo_disposition.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "work_orders",
        sa.Column(
            "disposition",
            _wo_disposition,
            nullable=False,
            server_default="failure",
        ),
    )


def downgrade() -> None:
    op.drop_column("work_orders", "disposition")
    _wo_disposition.drop(op.get_bind(), checkfirst=True)
