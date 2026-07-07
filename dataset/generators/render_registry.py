"""render_registry.py — spares & PM schedule CSVs + 2 P&ID reference PNGs.

Set-dressing tables and drawings (registered as documents, minimal content).
The P&IDs are never parsed (PRD §15) — they exist so the plant feels real.
"""

from __future__ import annotations

import csv

from PIL import Image, ImageDraw

from catalogue import load_design, pid_docs, registry_docs
from pdf_helpers import s


def _write_csv(rows: list[dict], path, fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path.stat().st_size


def _draw_pid(title: str, blocks: list[tuple[str, int, int]], path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 1400, 900
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, w - 20, h - 20], outline=(60, 60, 60), width=3)
    d.text((40, 35), s(title), fill="black")
    bw, bh = 200, 90
    centers = []
    for label, cx, cy in blocks:
        d.rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2],
                    outline=(20, 20, 20), width=3)
        d.text((cx - bw // 2 + 12, cy - 10), s(label), fill="black")
        centers.append((cx, cy))
    # Connect blocks left-to-right with process lines.
    for (x1, y1), (x2, y2) in zip(centers, centers[1:]):
        d.line([x1 + bw // 2, y1, x2 - bw // 2, y2], fill=(20, 20, 20), width=3)
    img.save(path, "PNG")


def render(design: dict) -> None:
    reg = {m.doc_type: m for m in registry_docs(design)}
    pids = pid_docs(design)

    spares = design["spares_catalogue"]
    pm = design["pm_schedule"]
    s1 = _write_csv(
        spares, reg["spares_catalogue"].abs_path,
        ["part_no", "description", "asset_class", "qty_on_hand", "reorder_level", "unit_cost_inr"],
    )
    s2 = _write_csv(
        pm, reg["pm_schedule"].abs_path,
        ["asset_tag", "task", "frequency", "last_done", "next_due"],
    )

    _draw_pid(
        "P&ID - Unit 300 Esterification (ester feed pumps)",
        [("TK-3201 Day Tank", 250, 450), ("P-3401 Feed Pump A", 700, 300),
         ("P-3402 Feed Pump B", 700, 600), ("E-3110 Cooler", 1150, 450)],
        pids[0].abs_path,
    )
    _draw_pid(
        "P&ID - Unit 100 Distillation (solvent bottoms pump)",
        [("Column C-101", 300, 450), ("P-3105 Bottoms Pump", 800, 450),
         ("TK-1201 Solvent Tank", 1200, 450)],
        pids[1].abs_path,
    )

    print(f"render_registry: spares.csv ({s1} B), pm_schedule.csv ({s2} B), 2 P&ID PNGs")


def main() -> None:
    from validate_design import validate_design

    design = load_design()
    validate_design(design)
    render(design)


if __name__ == "__main__":
    main()
