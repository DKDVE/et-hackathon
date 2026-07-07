"""render_wo.py — expand the design into work_orders.csv (M3 ingestion input).

Deterministic: hard-authored WOs (the planted pattern + history) verbatim, plus
generated noise drawn ONLY from phrasings authored in meridian.yaml (P10). Two
outputs:
  - work_orders.csv        columns = TDD §3 work_orders minus failure_mode_id /
                           normalization_score / the true label. Seeded as-is.
  - work_orders_truth.csv  wo_number -> true_failure_mode ground truth for the
                           M3 normalization audit. NEVER seeded into Postgres.
"""

from __future__ import annotations

import csv
from datetime import date, datetime

from catalogue import RENDERED_DIR, load_design, stable_rng

_DATE_FMT = "%Y-%m-%d"
# ponytail: hero sisters carry seal-leakage only via the three planted WOs — generator must not add more
_HERO_SISTER_TAGS = frozenset({"P-3401", "P-3402", "P-3105", "P-2210"})


def _to_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), _DATE_FMT).date()


def _noise_profile(tag: str, profile: dict[str, int]) -> dict[str, int]:
    if tag in _HERO_SISTER_TAGS:
        return {k: v for k, v in profile.items() if k != "mechanical_seal_leakage"}
    return profile


def _weighted_choice(rng, profile: dict[str, int]) -> str:
    items = sorted(profile.items())  # stable order
    total = sum(w for _, w in items)
    r = rng.random() * total
    upto = 0.0
    for mode, w in items:
        upto += w
        if r <= upto:
            return mode
    return items[-1][0]


def _pick_phrase(rng, bank: list[dict[str, str]]) -> str:
    return bank[rng.randrange(len(bank))]["text"]


def generate(design: dict) -> tuple[list[dict], list[dict]]:
    gen = design["work_order_generation"]
    profiles = gen["class_failure_profiles"]
    downtime_ranges = gen["downtime_ranges"]
    phrase_bank = design["phrase_bank"]
    routine_phrases = design["routine_phrases"]
    actions_bank = design["actions_bank"]
    routine_ratio = float(gen["routine_ratio"])
    first_year = int(gen["first_wo_year"])
    last_date = _to_date(gen["last_wo_date"])

    assets = {a["tag"]: a for a in design["assets"]}

    # --- hard-coded WOs ---
    hardcoded = design["work_orders"]
    used_numbers = {w["wo_number"] for w in hardcoded}
    hard_per_asset: dict[str, int] = {}
    for w in hardcoded:
        hard_per_asset[w["asset_tag"]] = hard_per_asset.get(w["asset_tag"], 0) + 1

    rows: list[dict] = []
    truth: list[dict] = []

    def emit(wo_number, tag, opened, closed, raw, actions, downtime, true_mode):
        rows.append(
            {
                "wo_number": wo_number,
                "asset_tag": tag,
                "opened_on": opened.isoformat(),
                "closed_on": closed.isoformat(),
                "raw_description": raw,
                "actions_taken": actions,
                "downtime_hours": f"{float(downtime):.1f}",
            }
        )
        truth.append(
            {"wo_number": wo_number, "asset_tag": tag, "true_failure_mode": true_mode}
        )

    for w in hardcoded:
        emit(
            w["wo_number"], w["asset_tag"], _to_date(w["opened_on"]),
            _to_date(w["closed_on"]), w["raw_description"], w["actions_taken"],
            w["downtime_hours"], w["true_failure_mode"],
        )

    # --- generated noise, per asset, in yaml order (deterministic) ---
    year_counters: dict[int, int] = {}

    def next_number(year: int) -> str:
        n = year_counters.get(year, 2000)
        while True:
            candidate = f"WO-{year}-{n:04d}"
            n += 1
            if candidate not in used_numbers:
                year_counters[year] = n
                used_numbers.add(candidate)
                return candidate

    for tag, asset in assets.items():
        cls = asset["class"]
        n_total = int(asset["wo_count"])
        n_gen = n_total - hard_per_asset.get(tag, 0)
        if n_gen <= 0:
            continue
        profile = _noise_profile(tag, profiles[cls])
        rng = stable_rng("wo", tag)
        installed = _to_date(asset["installed_on"])
        start = max(installed, date(first_year, 1, 1))
        span_days = max(1, (last_date - start).days)

        for _ in range(n_gen):
            opened = date.fromordinal(start.toordinal() + rng.randint(0, span_days))
            closed = date.fromordinal(
                min(opened.toordinal() + rng.randint(0, 4), last_date.toordinal())
            )
            if rng.random() < routine_ratio:
                mode = "unclassified"
                raw = _pick_phrase(rng, routine_phrases)
            else:
                mode = _weighted_choice(rng, profile)
                raw = _pick_phrase(rng, phrase_bank[mode])
            lo, hi = downtime_ranges[mode]
            downtime = round(rng.uniform(lo, hi), 1)
            actions_list = actions_bank[mode]
            actions = actions_list[rng.randrange(len(actions_list))]
            emit(next_number(opened.year), tag, opened, closed, raw, actions, downtime, mode)

    # Stable ordering for byte-identical CSV output.
    rows.sort(key=lambda r: (r["opened_on"], r["wo_number"]))
    truth.sort(key=lambda r: r["wo_number"])
    return rows, truth


def main() -> None:
    from validate_design import validate_design

    design = load_design()
    rows, truth = generate(design)

    RENDERED_DIR.mkdir(parents=True, exist_ok=True)
    wo_path = RENDERED_DIR / "work_orders.csv"
    truth_path = RENDERED_DIR / "work_orders_truth.csv"

    with open(wo_path, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "wo_number", "asset_tag", "opened_on", "closed_on",
                "raw_description", "actions_taken", "downtime_hours",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    with open(truth_path, "w", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["wo_number", "asset_tag", "true_failure_mode"]
        )
        writer.writeheader()
        writer.writerows(truth)

    validate_design(design)
    print(f"render_wo: {len(rows)} work orders -> {wo_path.name} ({wo_path.stat().st_size} B)")
    print(f"render_wo: ground truth -> {truth_path.name} (NOT seeded)")


if __name__ == "__main__":
    main()
