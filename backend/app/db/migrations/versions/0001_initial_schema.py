"""Initial schema — TDD §3.

Embedding dimension must match app.config.EMBEDDING_DIM (currently 1024).
To change dims: edit EMBEDDING_DIM in config.py and add a new migration.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# Keep in sync with app.config.EMBEDDING_DIM
EMBEDDING_DIM = 1024

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _pg_enum(name: str, *values: str) -> postgresql.ENUM:
    """Create enum type once, then return column type without re-create."""
    created = postgresql.ENUM(*values, name=name)
    created.create(op.get_bind(), checkfirst=True)
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    criticality = _pg_enum("criticality", "A", "B", "C")
    event_source = _pg_enum("event_source", "manual", "simulated", "integration")
    event_status = _pg_enum("event_status", "open", "reviewed", "closed")
    doc_type = _pg_enum(
        "doc_type",
        "oem_manual",
        "sop",
        "inspection_report",
        "incident_report",
        "pid_drawing",
        "spares_catalogue",
        "pm_schedule",
    )
    dossier_status = _pg_enum(
        "dossier_status", "assembling", "reasoning", "complete", "failed"
    )
    evidence_kind = _pg_enum("evidence_kind", "work_order", "chunk")

    op.create_table(
        "asset_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("manufacturer", sa.String(255), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("class_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tag", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "asset_class_id",
            sa.Integer(),
            sa.ForeignKey("asset_classes.id"),
            nullable=False,
        ),
        sa.Column("plant", sa.String(128), nullable=False),
        sa.Column("unit", sa.String(128), nullable=False),
        sa.Column("area", sa.String(128), nullable=False),
        sa.Column("service_duty", sa.String(255), nullable=False),
        sa.Column("criticality", criticality, nullable=False),
        sa.Column("installed_on", sa.Date()),
        sa.UniqueConstraint("tag", name="uq_assets_tag"),
    )
    op.create_table(
        "failure_modes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.UniqueConstraint("code", name="uq_failure_modes_code"),
    )
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wo_number", sa.String(64), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("opened_on", sa.Date(), nullable=False),
        sa.Column("closed_on", sa.Date()),
        sa.Column("raw_description", sa.Text(), nullable=False),
        sa.Column("actions_taken", sa.Text()),
        sa.Column("downtime_hours", sa.Numeric(10, 2)),
        sa.Column("failure_mode_id", sa.Integer(), sa.ForeignKey("failure_modes.id")),
        sa.Column("normalization_score", sa.Float()),
        sa.UniqueConstraint("wo_number", name="uq_work_orders_wo_number"),
    )
    op.create_table(
        "operational_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id"), nullable=False),
        sa.Column("source", event_source, nullable=False),
        sa.Column("symptom_category", sa.String(255), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("criticality", criticality, nullable=False),
        sa.Column("status", event_status, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doc_type", doc_type, nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id")),
        sa.Column("asset_class_id", sa.Integer(), sa.ForeignKey("asset_classes.id")),
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("section_ref", sa.String(255)),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
    )
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "dossiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("operational_events.id"), nullable=False),
        sa.Column("status", dossier_status, nullable=False),
        sa.Column("shared_context", sa.dialects.postgresql.JSONB()),
        sa.Column("sections", sa.dialects.postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("event_id", name="uq_dossiers_event_id"),
    )
    op.create_table(
        "evidence_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dossier_id", sa.Integer(), sa.ForeignKey("dossiers.id"), nullable=False),
        sa.Column("claim_ref", sa.String(128), nullable=False),
        sa.Column("evidence_kind", evidence_kind, nullable=False),
        sa.Column("work_order_id", sa.Integer(), sa.ForeignKey("work_orders.id")),
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("chunks.id")),
        sa.CheckConstraint(
            "(work_order_id IS NOT NULL AND chunk_id IS NULL) OR "
            "(work_order_id IS NULL AND chunk_id IS NOT NULL)",
            name="ck_evidence_links_one_fk",
        ),
    )


def downgrade() -> None:
    op.drop_table("evidence_links")
    op.drop_table("dossiers")
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("operational_events")
    op.drop_table("work_orders")
    op.drop_table("failure_modes")
    op.drop_table("assets")
    op.drop_table("asset_classes")

    for name in (
        "evidence_kind",
        "dossier_status",
        "doc_type",
        "event_status",
        "event_source",
        "criticality",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)

    op.execute("DROP EXTENSION IF EXISTS vector")
