"""Generation-time design validator — hard-fail on demo-spec drift (M3.1)."""

from __future__ import annotations

from datetime import date, datetime

from catalogue import load_design

HERO_SISTER_TAGS = frozenset({"P-3401", "P-3402", "P-3105", "P-2210"})
PLANTED_SEAL_WOS = frozenset({"WO-2024-0117", "WO-2025-0289", "WO-2026-0034"})
_DATE_FMT = "%Y-%m-%d"


def _to_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), _DATE_FMT).date()


def validate_design(design: dict) -> None:
    """Raise ValueError if the design (and generated WO truth) violates demo spec."""
    errors: list[str] = []

    assets = {a["tag"]: a for a in design["assets"]}
    installed = {tag: _to_date(a["installed_on"]) for tag, a in assets.items()}

    # D-017: every failure mode must carry a non-empty family.
    modes_without_family = [
        m["code"] for m in design["failure_modes"] if not str(m.get("family", "")).strip()
    ]
    if modes_without_family:
        errors.append(
            f"failure modes missing a family (D-017): {sorted(modes_without_family)}"
        )

    # Lazy import avoids circular dependency at module load.
    from render_wo import generate

    _rows, truth = generate(design)

    seal_on_heroes = [
        t for t in truth
        if t["true_failure_mode"] == "mechanical_seal_leakage"
        and t["asset_tag"] in HERO_SISTER_TAGS
    ]
    seal_numbers = {t["wo_number"] for t in seal_on_heroes}

    if len(seal_on_heroes) != 3:
        errors.append(
            f"expected exactly 3 mechanical_seal_leakage WOs on {sorted(HERO_SISTER_TAGS)}, "
            f"got {len(seal_on_heroes)}: {sorted(seal_numbers)}"
        )
    if seal_numbers != PLANTED_SEAL_WOS:
        errors.append(
            f"seal-leakage WOs must be {sorted(PLANTED_SEAL_WOS)}, got {sorted(seal_numbers)}"
        )

    # Span/downtime from hard-coded planted trio (authoritative).
    hard = {w["wo_number"]: w for w in design["work_orders"]}
    planted_hard = [hard[wo] for wo in sorted(PLANTED_SEAL_WOS)]
    closed_dates = [_to_date(w["closed_on"]) for w in planted_hard]
    span = (max(closed_dates).year - min(closed_dates).year) * 12 + (
        max(closed_dates).month - min(closed_dates).month
    )
    downtime = sum(float(w["downtime_hours"]) for w in planted_hard)
    if span != 22:
        errors.append(f"planted trio span must be 22 months, got {span}")
    if abs(downtime - 41.0) > 1e-6:
        errors.append(f"planted trio downtime must be 41.0 h, got {downtime}")

    for row in _rows:
        opened = _to_date(row["opened_on"])
        tag = row["asset_tag"]
        if tag in installed and opened < installed[tag]:
            errors.append(
                f"{row['wo_number']} opened {opened} before {tag} install {installed[tag]}"
            )

    if errors:
        raise ValueError("Design validation failed:\n  - " + "\n  - ".join(errors))


def main() -> None:
    validate_design(load_design())
    print("validate_design: OK")


if __name__ == "__main__":
    main()
