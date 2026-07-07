"""Asset registry endpoints (TDD §7)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.deps import DbDep
from app.api.schemas import AssetSummary
from app.db.models import Asset, AssetClass
from app.memory.repositories import assets

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _to_summary(asset: Asset, klass: AssetClass) -> AssetSummary:
    return AssetSummary(
        asset_id=asset.id,
        tag=asset.tag,
        name=asset.name,
        asset_class=klass.class_name,
        plant=asset.plant,
        unit=asset.unit,
        area=asset.area,
        service_duty=asset.service_duty,
        criticality=str(asset.criticality),
    )


@router.get("", response_model=list[AssetSummary])
def list_assets(db: DbDep) -> list[AssetSummary]:
    return [_to_summary(a, k) for a, k in assets.list_asset_profiles(db)]


@router.get("/{tag}", response_model=AssetSummary)
def get_asset(tag: str, db: DbDep) -> AssetSummary:
    asset_id = assets.get_asset_id_by_tag(db, tag)
    if asset_id is None:
        raise HTTPException(404, f"asset '{tag}' not found")
    profile = assets.get_asset_profile(db, asset_id)
    assert profile is not None
    return AssetSummary(
        asset_id=profile.asset_id,
        tag=profile.tag,
        name=profile.name,
        asset_class=profile.asset_class,
        plant=profile.plant,
        unit=profile.unit,
        area=profile.area,
        service_duty=profile.service_duty,
        criticality=profile.criticality,
    )