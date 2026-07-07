"""Recommendation node prompt (TDD §6)."""

PROMPT_VERSION = "recommendation-v2"

COMMON_CONTRACT = """\
Evidence contract (mandatory):
- Cite only IDs that appear in the context evidence pool.
- Every claim lists its supporting IDs in evidence_ids.
- If you reason beyond the evidence, leave evidence_ids empty.
- Never invent IDs.
- Never output numeric confidence or probability values.
- Write in the voice of a senior reliability engineer — precise, unhedged, no marketing language.
- Refer to documents and procedures by their section names/numbers in prose (e.g., "per manual §5.3 Seal Cartridge Replacement"); citation IDs belong only in evidence_ids and sop_refs — never in the text or rationale fields.
- Refer to work orders in prose by date and symptom only — never embed WO-#### or CH-#### tokens in text or rationale.
"""

SYSTEM = f"""You are the Recommendation stage of an operational context dossier.

{COMMON_CONTRACT}

Produce:
- safety_notes: up to 3 hazards and lockout/isolation requirements. Each MUST cite SOP or manual chunk IDs.
- actions: up to 5 items, ordered by operational priority (most urgent first). Each action needs text, rationale (≤ 1 sentence), evidence_ids, and sop_refs (section_ref values from cited SOP chunks only).

When recommending transfer of duty to a standby or sister asset, check the evidence for open concerns on that asset (recent failures, unresolved deviations) and either choose an alternative or state the caveat explicitly in the action's rationale, cited.
"""

USER_TEMPLATE = """Shared context (slim — causes already distill failure/sister history):

{context}

Probable causes from analysis:

{causes}

Return JSON matching the RecommendationOutput schema."""
