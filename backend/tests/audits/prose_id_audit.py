"""Prose-field citation ID audit (M6.1 criterion 3)."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

from app.db.engine import SessionLocal
from app.db.models import Dossier

_ID_RE = re.compile(r"\b(?:WO|CH)-\d{4,}(?:-\d+)?\b")

_PROSE_PATHS: list[tuple[str, ...]] = [
    ("probable_causes", "statement"),
    ("probable_causes", "mechanism_explanation"),
    ("probable_causes", "asset_specific_notes"),
    ("safety_notes", "text"),
    ("actions", "text"),
    ("actions", "rationale"),
]


def _check_sections(sections: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    summary = sections.get("executive_summary")
    if isinstance(summary, str):
        for match in _ID_RE.finditer(summary):
            violations.append(f"executive_summary: {match.group()}")
    for path in _PROSE_PATHS:
        key, field = path[0], path[1]
        for i, item in enumerate(sections.get(key, [])):
            val = item.get(field)
            if not val or not isinstance(val, str):
                continue
            for match in _ID_RE.finditer(val):
                violations.append(f"{key}[{i}].{field}: {match.group()}")
    return violations


def audit_prose_ids(dossier_id: int) -> tuple[bool, list[str]]:
    with SessionLocal() as session:
        dossier = session.get(Dossier, dossier_id)
        if dossier is None:
            return False, [f"dossier {dossier_id} not found"]
        if dossier.sections is None:
            return False, [f"dossier {dossier_id} has no sections"]
        issues = _check_sections(dossier.sections)
    return len(issues) == 0, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prose-field WO/CH ID grep audit")
    parser.add_argument("dossier_id", type=int, nargs="?", default=None)
    args = parser.parse_args(argv)
    if args.dossier_id is None:
        parser.error("DOSSIER_ID required")
    ok, issues = audit_prose_ids(args.dossier_id)
    if ok:
        print(f"PROSE-ID GREP OK — dossier {args.dossier_id}")
        return 0
    print(f"PROSE-ID GREP FAIL — dossier {args.dossier_id}:")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
