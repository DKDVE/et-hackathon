"""Shared design-file loader + document catalogue (P10).

This module is the single source of truth for *what documents exist* and *where
they live*. Both the generators (which render the files) and scripts/seed.py
(which registers them in Postgres) import it, so the two can never disagree.

Deliberately dependency-light: stdlib + PyYAML only, so scripts/seed.py can
import it inside the backend container without pulling in fpdf2/pillow.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

# ponytail: one fixed seed threads all randomness — same yaml in, byte-identical
# artifacts out. Change it only if you deliberately want a different plant.
SEED = "meridian-2024"

DATASET_DIR = Path(__file__).resolve().parents[1]
DESIGN_PATH = DATASET_DIR / "design" / "meridian.yaml"
RENDERED_DIR = DATASET_DIR / "rendered"

# file_path stored in the DB is repo-relative so it is stable regardless of how
# the dataset dir is mounted at seed time. Rendered subdirs:
_REL_ROOT = "dataset/rendered"


def load_design(path: Path | str | None = None) -> dict[str, Any]:
    with open(path or DESIGN_PATH) as fh:
        return yaml.safe_load(fh)


def stable_rng(*parts: object) -> random.Random:
    """Deterministic RNG seeded from a stable hash (avoids PYTHONHASHSEED)."""
    key = ":".join([SEED, *(str(p) for p in parts)])
    seed_int = int(hashlib.sha256(key.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed_int)


@dataclass(frozen=True)
class DocMeta:
    doc_type: str
    title: str
    rel_path: str            # repo-relative, stored in documents.file_path
    owner_tag: str | None = None      # asset tag, if owned by an asset
    owner_class: str | None = None    # asset-class key, if owned by a class
    note_id: str | None = None        # source operational_history_note, if any
    tier: int = 3

    @property
    def abs_path(self) -> Path:
        # rel_path is "dataset/rendered/..."; strip the dataset/rendered prefix.
        suffix = self.rel_path.split(f"{_REL_ROOT}/", 1)[1]
        return RENDERED_DIR / suffix


# --- individual document families -------------------------------------------

def manual_doc(design: dict[str, Any]) -> DocMeta:
    m = design["documents"]["manual"]
    return DocMeta(
        doc_type="oem_manual",
        title=m["title"].strip(),
        rel_path=f"{_REL_ROOT}/manual/CP200_manual.pdf",
        owner_class=m["owner_class"],
        tier=1,
    )


def sop_docs(design: dict[str, Any]) -> list[DocMeta]:
    out: list[DocMeta] = []
    for sop in design["documents"]["sops"]:
        out.append(
            DocMeta(
                doc_type="sop",
                title=sop["title"],
                rel_path=f"{_REL_ROOT}/sops/{sop['id']}.pdf",
                owner_class=sop.get("owner_class"),
                tier=sop.get("tier", 3),
            )
        )
    return out


# Target report totals (TDD §11 / M2 spec): 30 inspection + 15 incident.
N_INSPECTION = 30
N_INCIDENT = 15


def report_docs(design: dict[str, Any]) -> list[DocMeta]:
    """Enumerate all inspection + incident reports, deterministically.

    Hero operational_history_notes become Tier-1 reports on the hero assets;
    the remainder are filler one-pagers spread across the other assets to reach
    the target counts.
    """
    notes = design["operational_history_notes"]
    assets = design["assets"]
    filler_assets = [a for a in assets if not a.get("hero")]

    inspection: list[DocMeta] = []
    incident: list[DocMeta] = []

    # 1. Hero notes → deep Tier-1 reports.
    for note in notes:
        meta = DocMeta(
            doc_type=f"{note['kind']}_report",
            title=note["title"],
            rel_path=f"{_REL_ROOT}/reports/{note['kind']}/{note['id']}.pdf",
            owner_tag=note["owner_tag"],
            note_id=note["id"],
            tier=1,
        )
        (inspection if note["kind"] == "inspection" else incident).append(meta)

    # 2. Filler one-pagers to reach the target counts. Deterministic round-robin
    #    over the non-hero assets, with a stable date per report.
    def _fill(kind: str, target: int, bucket: list[DocMeta], seq_start: int) -> None:
        i = seq_start
        rng = stable_rng("report-fill", kind)
        while len(bucket) < target:
            asset = filler_assets[i % len(filler_assets)]
            rid = f"{'INSP' if kind == 'inspection' else 'INC'}-{i + 1:03d}"
            d = date(2021, 1, 1) + timedelta(days=rng.randint(0, 365 * 5))
            bucket.append(
                DocMeta(
                    doc_type=f"{kind}_report",
                    title=f"{'Routine inspection' if kind == 'inspection' else 'Incident report'} — {asset['tag']} ({d.isoformat()})",
                    rel_path=f"{_REL_ROOT}/reports/{kind}/{rid}.pdf",
                    owner_tag=asset["tag"],
                    tier=3,
                )
            )
            i += 1

    _fill("inspection", N_INSPECTION, inspection, 0)
    _fill("incident", N_INCIDENT, incident, 0)
    return inspection + incident


def pid_docs(design: dict[str, Any]) -> list[DocMeta]:
    # 2 static P&ID reference images (set-dressing; never parsed — PRD §15).
    return [
        DocMeta(
            doc_type="pid_drawing",
            title="P&ID — Unit 300 Esterification (ester feed pumps)",
            rel_path=f"{_REL_ROOT}/pid/PID_U300.png",
            tier=3,
        ),
        DocMeta(
            doc_type="pid_drawing",
            title="P&ID — Unit 100 Distillation (solvent bottoms pump)",
            rel_path=f"{_REL_ROOT}/pid/PID_U100.png",
            tier=3,
        ),
    ]


def registry_docs(design: dict[str, Any]) -> list[DocMeta]:
    return [
        DocMeta(
            doc_type="spares_catalogue",
            title="Meridian Spares Catalogue",
            rel_path=f"{_REL_ROOT}/registry/spares_catalogue.csv",
            tier=3,
        ),
        DocMeta(
            doc_type="pm_schedule",
            title="Meridian PM Schedule",
            rel_path=f"{_REL_ROOT}/registry/pm_schedule.csv",
            tier=3,
        ),
    ]


def all_documents(design: dict[str, Any]) -> list[DocMeta]:
    """The complete document catalogue (~60) that seed registers."""
    return [
        manual_doc(design),
        *sop_docs(design),
        *report_docs(design),
        *pid_docs(design),
        *registry_docs(design),
    ]
