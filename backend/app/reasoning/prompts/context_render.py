"""Render frozen SharedContext as compact plain-text for prompts (TDD §4)."""

from __future__ import annotations

from app.domain.models import SharedContext


def _fmt_wo_line(wo_number: str, asset_tag: str, desc: str, downtime: float | None) -> str:
    dt = f" ({downtime:g}h downtime)" if downtime is not None else ""
    snippet = desc.replace("\n", " ").strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "…"
    return f"[{wo_number}] {asset_tag}: \"{snippet}\"{dt}"


def _fmt_chunk_line(cid: str, section_ref: str | None, content: str) -> str:
    ref = section_ref or "section unknown"
    snippet = content.replace("\n", " ").strip()
    if len(snippet) > 160:
        snippet = snippet[:157] + "…"
    return f"[{cid}] {ref}: {snippet}"


def render_shared_context(ctx: SharedContext) -> str:
    """Every item headed by its citation ID — the evidence contract spine."""
    lines: list[str] = []

    ev = ctx.event
    lines.append("=== EVENT ===")
    lines.append(
        f"Asset {ev.asset_tag} | symptom={ev.symptom_category} | "
        f"criticality={ev.criticality} | note={ev.note or '(none)'}"
    )

    ap = ctx.asset_profile
    lines.append("\n=== ASSET PROFILE ===")
    lines.append(
        f"{ap.tag} {ap.name} | {ap.manufacturer} {ap.model} | "
        f"{ap.plant}/{ap.unit}/{ap.area} | duty={ap.service_duty}"
    )

    lines.append("\n=== FAILURE HISTORY (newest first) ===")
    for wo in ctx.failure_history:
        lines.append(_fmt_wo_line(wo.wo_number, wo.asset_tag, wo.raw_description, wo.downtime_hours))

    lines.append("\n=== SISTER INCIDENTS ===")
    for si in ctx.sister_incidents:
        lines.append(_fmt_wo_line(si.wo_number, si.asset_tag, si.raw_description, si.downtime_hours))

    lines.append("\n=== PATTERN STATS (consider together) ===")
    for p in ctx.pattern_stats:
        phrasings = "; ".join(p.distinct_phrasings[:3])
        lines.append(
            f"{p.failure_mode}: {p.occurrences} occurrences over {p.span_months}mo, "
            f"{p.total_downtime_hours:g}h total | assets={','.join(p.asset_tags)} | "
            f"phrasings: {phrasings}"
        )

    lines.append("\n=== MANUAL CHUNKS ===")
    for c in ctx.manual_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== SOP CHUNKS ===")
    for c in ctx.sop_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== REPORT CHUNKS ===")
    for c in ctx.report_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== EVIDENCE POOL (cite ONLY these IDs) ===")
    lines.append(", ".join(sorted(ctx.evidence_pool)))

    return "\n".join(lines)


def render_recommendation_context(ctx: SharedContext) -> str:
    """Slim context for recommendation — omits failure history and sister incidents (M6.1).

    Causes from analysis already distill WO/sister evidence; full re-render wastes tokens.
    """
    lines: list[str] = []

    ev = ctx.event
    lines.append("=== EVENT ===")
    lines.append(
        f"Asset {ev.asset_tag} | symptom={ev.symptom_category} | "
        f"criticality={ev.criticality} | note={ev.note or '(none)'}"
    )

    ap = ctx.asset_profile
    lines.append("\n=== ASSET PROFILE ===")
    lines.append(
        f"{ap.tag} {ap.name} | {ap.manufacturer} {ap.model} | "
        f"{ap.plant}/{ap.unit}/{ap.area} | duty={ap.service_duty}"
    )

    lines.append("\n=== PATTERN STATS (consider together) ===")
    for p in ctx.pattern_stats:
        phrasings = "; ".join(p.distinct_phrasings[:3])
        lines.append(
            f"{p.failure_mode}: {p.occurrences} occurrences over {p.span_months}mo, "
            f"{p.total_downtime_hours:g}h total | assets={','.join(p.asset_tags)} | "
            f"phrasings: {phrasings}"
        )

    lines.append("\n=== MANUAL CHUNKS ===")
    for c in ctx.manual_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== SOP CHUNKS ===")
    for c in ctx.sop_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== REPORT CHUNKS (safety / incident context) ===")
    for c in ctx.report_chunks:
        lines.append(_fmt_chunk_line(c.citation_id, c.section_ref, c.content))

    lines.append("\n=== EVIDENCE POOL (cite ONLY these IDs) ===")
    lines.append(", ".join(sorted(ctx.evidence_pool)))

    return "\n".join(lines)


def render_validated_sections(sections: dict) -> str:
    """Validated findings only — no re-assembly, no retrieval (P4)."""
    lines: list[str] = ["\n=== VALIDATED FINDINGS ==="]

    for i, n in enumerate(sections.get("safety_notes", [])):
        ids = ", ".join(n.get("evidence_ids") or [])
        lines.append(f"[safety:{i}] {n.get('text', '')} (evidence: {ids or 'none'})")

    for i, c in enumerate(sections.get("probable_causes", [])):
        ids = ", ".join(c.get("evidence_ids") or [])
        tier = c.get("strength_tier") or c.get("grounding", "")
        lines.append(
            f"[cause:{i}] {c.get('statement', '')} — {c.get('mechanism_explanation', '')} "
            f"({tier}; evidence: {ids or 'hypothesis'})"
        )

    for i, a in enumerate(sections.get("actions", [])):
        ids = ", ".join(a.get("evidence_ids") or [])
        lines.append(
            f"[action:{i}] {a.get('text', '')} — {a.get('rationale', '')} "
            f"(evidence: {ids or 'none'})"
        )

    return "\n".join(lines)


def render_dossier_context(ctx: SharedContext, sections: dict | None) -> str:
    """Frozen shared context + validated sections for chat (P1/P4)."""
    base = render_shared_context(ctx)
    if sections:
        base += render_validated_sections(sections)
    return base
