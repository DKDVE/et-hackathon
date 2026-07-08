"""SQLAlchemy ORM models — TDD §3 physical schema."""

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import EMBEDDING_DIM


class Base(DeclarativeBase):
    pass


class Criticality(StrEnum):
    A = "A"
    B = "B"
    C = "C"


criticality_enum = Enum(
    Criticality, name="criticality", native_enum=True, create_constraint=True
)


class EventSource(StrEnum):
    manual = "manual"
    simulated = "simulated"
    integration = "integration"


class EventStatus(StrEnum):
    open = "open"
    reviewed = "reviewed"
    closed = "closed"


class DocType(StrEnum):
    oem_manual = "oem_manual"
    sop = "sop"
    inspection_report = "inspection_report"
    incident_report = "incident_report"
    pid_drawing = "pid_drawing"
    spares_catalogue = "spares_catalogue"
    pm_schedule = "pm_schedule"


class DossierStatus(StrEnum):
    assembling = "assembling"
    reasoning = "reasoning"
    complete = "complete"
    failed = "failed"


class ReasoningRunStatus(StrEnum):
    ok = "ok"
    repaired = "repaired"
    failed = "failed"


class EvalSuite(StrEnum):
    golden = "golden"
    groundedness = "groundedness"
    normalization = "normalization"
    prose_id = "prose_id"
    timing = "timing"


class EvalStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class EvidenceKind(StrEnum):
    work_order = "work_order"
    chunk = "chunk"


class HumanVerdict(StrEnum):
    confirmed = "confirmed"
    corrected = "corrected"
    unclassifiable = "unclassifiable"


human_verdict_enum = Enum(
    HumanVerdict,
    name="human_verdict",
    native_enum=True,
    create_constraint=True,
)


class AssetClass(Base):
    __tablename__ = "asset_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(255), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    assets: Mapped[list["Asset"]] = relationship(back_populates="asset_class")
    documents: Mapped[list["Document"]] = relationship(back_populates="asset_class")


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("tag", name="uq_assets_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class_id: Mapped[int] = mapped_column(ForeignKey("asset_classes.id"), nullable=False)
    plant: Mapped[str] = mapped_column(String(128), nullable=False)
    unit: Mapped[str] = mapped_column(String(128), nullable=False)
    area: Mapped[str] = mapped_column(String(128), nullable=False)
    service_duty: Mapped[str] = mapped_column(String(255), nullable=False)
    criticality: Mapped[Criticality] = mapped_column(criticality_enum, nullable=False)
    installed_on: Mapped[date | None] = mapped_column(Date)

    asset_class: Mapped[AssetClass] = relationship(back_populates="assets")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="asset")
    operational_events: Mapped[list["OperationalEvent"]] = relationship(back_populates="asset")
    documents: Mapped[list["Document"]] = relationship(back_populates="asset")


class FailureMode(Base):
    __tablename__ = "failure_modes"
    __table_args__ = (UniqueConstraint("code", name="uq_failure_modes_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # D-017: phenomenological grouping; margin gate is a cross-family guard only.
    family: Mapped[str] = mapped_column(Text, nullable=False, server_default="general")
    description: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    work_orders: Mapped[list["WorkOrder"]] = relationship(
        back_populates="failure_mode",
        foreign_keys="WorkOrder.failure_mode_id",
    )


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (UniqueConstraint("wo_number", name="uq_work_orders_wo_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    wo_number: Mapped[str] = mapped_column(String(64), nullable=False)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    opened_on: Mapped[date] = mapped_column(Date, nullable=False)
    closed_on: Mapped[date | None] = mapped_column(Date)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    actions_taken: Mapped[str | None] = mapped_column(Text)
    downtime_hours: Mapped[float | None] = mapped_column(Numeric(10, 2))
    # D-023: auto columns — ONLY the ingester (wo_normalizer) may write these.
    failure_mode_id: Mapped[int | None] = mapped_column(ForeignKey("failure_modes.id"))
    normalization_score: Mapped[float | None] = mapped_column()
    human_failure_mode_id: Mapped[int | None] = mapped_column(ForeignKey("failure_modes.id"))
    human_verdict: Mapped[HumanVerdict | None] = mapped_column(human_verdict_enum)
    human_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped[Asset] = relationship(back_populates="work_orders")
    failure_mode: Mapped[FailureMode | None] = relationship(
        back_populates="work_orders", foreign_keys=[failure_mode_id]
    )
    evidence_links: Mapped[list["EvidenceLink"]] = relationship(back_populates="work_order")


class OperationalEvent(Base):
    __tablename__ = "operational_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), nullable=False)
    source: Mapped[EventSource] = mapped_column(
        Enum(EventSource, name="event_source", native_enum=True, create_constraint=True),
        nullable=False,
    )
    symptom_category: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[Criticality] = mapped_column(criticality_enum, nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status", native_enum=True, create_constraint=True),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped[Asset] = relationship(back_populates="operational_events")
    dossier: Mapped["Dossier | None"] = relationship(back_populates="event")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, name="doc_type", native_enum=True, create_constraint=True),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    asset_class_id: Mapped[int | None] = mapped_column(ForeignKey("asset_classes.id"))

    asset: Mapped[Asset | None] = relationship(back_populates="documents")
    asset_class: Mapped[AssetClass | None] = relationship(back_populates="documents")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), nullable=False)
    page: Mapped[int] = mapped_column(nullable=False)
    section_ref: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    document: Mapped[Document] = relationship(back_populates="chunks")
    evidence_links: Mapped[list["EvidenceLink"]] = relationship(back_populates="chunk")


class Dossier(Base):
    __tablename__ = "dossiers"
    __table_args__ = (UniqueConstraint("event_id", name="uq_dossiers_event_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("operational_events.id"), nullable=False)
    status: Mapped[DossierStatus] = mapped_column(
        Enum(DossierStatus, name="dossier_status", native_enum=True, create_constraint=True),
        nullable=False,
    )
    shared_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sections: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guardrail_stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    event: Mapped[OperationalEvent] = relationship(back_populates="dossier")
    evidence_links: Mapped[list["EvidenceLink"]] = relationship(back_populates="dossier")
    reasoning_runs: Mapped[list["ReasoningRun"]] = relationship(back_populates="dossier")


class ReasoningRun(Base):
    __tablename__ = "reasoning_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id", ondelete="CASCADE"))
    node: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(nullable=False, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(nullable=False, server_default="0")
    status: Mapped[ReasoningRunStatus] = mapped_column(
        Enum(
            ReasoningRunStatus,
            name="reasoning_run_status",
            native_enum=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    output_digest: Mapped[str] = mapped_column(Text, nullable=False)

    dossier: Mapped[Dossier] = relationship(back_populates="reasoning_runs")


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite: Mapped[EvalSuite] = mapped_column(
        Enum(
            EvalSuite,
            name="eval_suite",
            native_enum=True,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    git_ref: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[EvalStatus] = mapped_column(
        Enum(
            EvalStatus,
            name="eval_status",
            native_enum=True,
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class ReasoningFallbackCache(Base):
    __tablename__ = "reasoning_fallback_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    event_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (
        CheckConstraint(
            "(work_order_id IS NOT NULL AND chunk_id IS NULL) OR "
            "(work_order_id IS NULL AND chunk_id IS NOT NULL)",
            name="ck_evidence_links_one_fk",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dossier_id: Mapped[int] = mapped_column(ForeignKey("dossiers.id"), nullable=False)
    claim_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_kind: Mapped[EvidenceKind] = mapped_column(
        Enum(EvidenceKind, name="evidence_kind", native_enum=True, create_constraint=True),
        nullable=False,
    )
    work_order_id: Mapped[int | None] = mapped_column(ForeignKey("work_orders.id"))
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id"))

    dossier: Mapped[Dossier] = relationship(back_populates="evidence_links")
    work_order: Mapped[WorkOrder | None] = relationship(back_populates="evidence_links")
    chunk: Mapped[Chunk | None] = relationship(back_populates="evidence_links")
