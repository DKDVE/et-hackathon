"""Groundedness walker — NFR-2 instrument (M6, pulled from M9)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from sqlalchemy import select

from app.db.engine import SessionLocal
from app.db.models import Dossier, EvidenceLink
from app.domain.models import SharedContext

_CONFIDENCE_RE = re.compile(r"confidence", re.IGNORECASE)


def _walk_sections(sections: dict[str, Any], pool: set[str]) -> list[str]:
    violations: list[str] = []

    def check_claim(kind: str, item: dict[str, Any]) -> None:
        ref = item.get("claim_ref", "?")
        grounding = item.get("grounding")
        ids = item.get("evidence_ids") or []

        if kind == "safety_notes" and grounding == "hypothesis":
            violations.append(f"{ref}: safety note with hypothesis grounding (must be deleted)")
            return

        if grounding == "hypothesis":
            if ids:
                violations.append(f"{ref}: hypothesis claim must not display evidence_ids")
            return

        if grounding != "evidenced":
            violations.append(f"{ref}: claim must be evidenced or hypothesis, got {grounding!r}")
            return

        if not ids:
            violations.append(f"{ref}: evidenced claim has no evidence_ids")
            return

        for cid in ids:
            if cid not in pool:
                violations.append(f"{ref}: evidence_id {cid} not in frozen evidence_pool")

    for key in ("probable_causes", "actions"):
        for item in sections.get(key, []):
            check_claim(key, item)
    for item in sections.get("safety_notes", []):
        check_claim("safety_notes", item)

    return violations


def _check_no_confidence(obj: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if _CONFIDENCE_RE.search(k):
                hits.append(p)
            hits.extend(_check_no_confidence(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_check_no_confidence(v, f"{path}[{i}]"))
    return hits


def audit_dossier(dossier_id: int) -> tuple[bool, list[str]]:
    issues: list[str] = []
    with SessionLocal() as session:
        dossier = session.get(Dossier, dossier_id)
        if dossier is None:
            return False, [f"dossier {dossier_id} not found"]
        if dossier.sections is None or dossier.shared_context is None:
            return False, [f"dossier {dossier_id} has no sections (not complete)"]

        ctx = SharedContext.model_validate(dossier.shared_context)
        pool = set(ctx.evidence_pool)
        sections = dossier.sections

        issues.extend(_walk_sections(sections, pool))
        issues.extend(_check_no_confidence(sections))

        links = session.scalars(
            select(EvidenceLink).where(EvidenceLink.dossier_id == dossier_id)
        ).all()
        linked_refs = {lnk.claim_ref for lnk in links}
        for key in ("probable_causes", "safety_notes", "actions"):
            for item in sections.get(key, []):
                ref = item.get("claim_ref")
                grounding = item.get("grounding")
                if grounding == "evidenced" and ref and ref not in linked_refs:
                    issues.append(f"{ref}: evidenced claim has no evidence_links row")

    return len(issues) == 0, issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Groundedness audit for a completed dossier")
    parser.add_argument("dossier_id", type=int, nargs="?", default=None)
    args = parser.parse_args(argv)
    if args.dossier_id is None:
        parser.error("DOSSIER_ID required")
    ok, issues = audit_dossier(args.dossier_id)
    if ok:
        print(f"GROUNDEDNESS OK — dossier {args.dossier_id}")
        return 0
    print(f"GROUNDEDNESS FAIL — dossier {args.dossier_id}:")
    for issue in issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
