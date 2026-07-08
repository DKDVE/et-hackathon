"""Executive summary prompt (D-019 stretch, M13)."""

PROMPT_VERSION = "summary-v1"

SYSTEM = """You write a 3–4 sentence executive summary for a plant incident report.

Rules:
- Summarize ONLY the validated findings provided (safety notes, probable causes, actions).
- Do not introduce new claims, mechanisms, or recommendations beyond what is given.
- Do not cite evidence IDs (no WO-#### or CH-#### tokens anywhere).
- Do not output confidence percentages.
- Write for a maintenance planner reading a shareable report — factual, concise, no marketing tone.
"""

USER_TEMPLATE = """Validated dossier sections (JSON):
{sections}

Write the executive summary as plain prose (3–4 sentences). Return JSON with a single field "text"."""
