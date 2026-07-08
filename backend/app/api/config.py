"""Public app config (D-021)."""

from fastapi import APIRouter

from app.api.schemas import AppConfig
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=AppConfig)
def get_app_config() -> AppConfig:
    settings = get_settings()
    per_hr = settings.downtime_cost_per_hour_inr
    # ponytail: label is display-only; value comes from settings
    lakhs = per_hr / 100_000
    label = f"₹{lakhs:g}L/hr" if lakhs < 100 else f"₹{per_hr / 10_000_000:g}Cr/hr"
    return AppConfig(
        downtime_cost_per_hour_inr=per_hr,
        downtime_cost_label=label,
        model_costs=settings.model_costs,
    )
