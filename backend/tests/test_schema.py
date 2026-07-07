"""Assert TDD §3 schema exists post-migration."""

from sqlalchemy import inspect, text

from app.db.engine import engine

EXPECTED_TABLES = (
    "asset_classes",
    "assets",
    "failure_modes",
    "work_orders",
    "operational_events",
    "documents",
    "chunks",
    "dossiers",
    "evidence_links",
)

EXPECTED_ENUMS = (
    "criticality",
    "event_source",
    "event_status",
    "doc_type",
    "dossier_status",
    "evidence_kind",
)

KEY_COLUMNS: dict[str, list[str]] = {
    "assets": ["tag", "asset_class_id", "criticality"],
    "work_orders": ["wo_number", "failure_mode_id", "normalization_score"],
    "operational_events": ["source", "symptom_category", "status"],
    "chunks": ["embedding", "document_id", "page"],
    "dossiers": ["shared_context", "sections", "event_id"],
    "evidence_links": ["claim_ref", "evidence_kind", "work_order_id", "chunk_id"],
}


def test_all_tables_exist() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    for table in EXPECTED_TABLES:
        assert table in tables, f"missing table: {table}"


def test_vector_extension_present() -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        ).fetchone()
    assert row is not None, "pgvector extension not installed"


def test_enum_types_exist() -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT typname FROM pg_type WHERE typtype = 'e' ORDER BY typname")
        ).fetchall()
    enum_names = {r[0] for r in rows}
    for enum_name in EXPECTED_ENUMS:
        assert enum_name in enum_names, f"missing enum type: {enum_name}"


def test_hnsw_index_on_chunks_embedding() -> None:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'chunks' AND indexdef LIKE '%hnsw%'"
            )
        ).fetchone()
    assert row is not None, "HNSW index on chunks.embedding not found"


def test_key_columns_exist() -> None:
    inspector = inspect(engine)
    for table, columns in KEY_COLUMNS.items():
        actual = {c["name"] for c in inspector.get_columns(table)}
        for col in columns:
            assert col in actual, f"{table}.{col} missing"
