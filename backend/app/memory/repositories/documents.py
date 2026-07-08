"""P&ID reference drawings linked by asset unit (M13)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, DocType, Document


def get_pid_drawings_for_asset(session: Session, asset_id: int) -> list[dict]:
    """Unit-level P&ID images — title match on 'Unit NNN' token, no parsing."""
    asset = session.get(Asset, asset_id)
    if asset is None:
        return []
    unit_token = asset.unit.split("—")[0].strip()
    if not unit_token:
        return []
    docs = session.scalars(
        select(Document)
        .where(Document.doc_type == DocType.pid_drawing)
        .order_by(Document.title)
    ).all()
    return [
        {
            "document_id": doc.id,
            "title": doc.title,
            "file_url": f"/api/sources/file/{doc.id}",
        }
        for doc in docs
        if unit_token in doc.title
    ]
