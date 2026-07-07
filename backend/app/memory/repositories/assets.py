"""Asset repository — profile + sister-asset resolution (TDD §5.1/§5.3, D-004).

Sisters are a plain two-predicate SQL query: same asset class OR same service
duty. No LLM, no graph DB (D-004).
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetClass
from app.domain.models import AssetProfile


def get_asset_id_by_tag(session: Session, tag: str) -> int | None:
    return session.scalar(select(Asset.id).where(Asset.tag == tag))


def get_asset_class_id(session: Session, asset_id: int) -> int | None:
    return session.scalar(select(Asset.asset_class_id).where(Asset.id == asset_id))


def get_asset_profile(session: Session, asset_id: int) -> AssetProfile | None:
    row = session.execute(
        select(Asset, AssetClass)
        .join(AssetClass, Asset.asset_class_id == AssetClass.id)
        .where(Asset.id == asset_id)
    ).first()
    if row is None:
        return None
    asset, klass = row
    return AssetProfile(
        asset_id=asset.id,
        tag=asset.tag,
        name=asset.name,
        asset_class=klass.class_name,
        manufacturer=klass.manufacturer,
        model=klass.model,
        plant=asset.plant,
        unit=asset.unit,
        area=asset.area,
        service_duty=asset.service_duty,
        criticality=str(asset.criticality),
        installed_on=asset.installed_on,
    )


def get_sister_asset_ids(
    session: Session, asset_id: int, *, include_self: bool = False
) -> list[int]:
    """Asset IDs sharing this asset's class OR its service duty (D-004).

    Ordered by id for determinism. ``include_self`` controls whether the anchor
    asset is part of the returned set (pattern stats need self; sister incidents
    do not).
    """
    anchor = session.execute(
        select(Asset.asset_class_id, Asset.service_duty).where(Asset.id == asset_id)
    ).first()
    if anchor is None:
        return []
    class_id, service_duty = anchor
    stmt = (
        select(Asset.id)
        .where(or_(Asset.asset_class_id == class_id, Asset.service_duty == service_duty))
        .order_by(Asset.id)
    )
    ids = list(session.scalars(stmt).all())
    if not include_self:
        ids = [i for i in ids if i != asset_id]
    return ids
