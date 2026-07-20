# ET Hackathon Compliance Report — Operational Context Engine

**Audit date:** 2026-07-20 (verification pass)  
**Problem statement:** [docs/ET_hackathon.pdf](ET_hackathon.pdf) — *AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain*  
**Method:** Repo artifacts, code paths, and commands run on warm Docker stack + browser device-mode pass. Evidence paths below; no product substrate changes during this pass (additive benchmark test + docs only).

---

## Executive summary

| Status | Before → After | Notes |
|--------|----------------:|-------|
| **MET** | 8 → **14** | Deck, interim C4, storyline, screenshots, gate green, decision log repaired |
| **PARTIAL** | 14 → **10** | Video, full C4 theme set, practitioner quote still open |
| **MISSING** | 6 → **4** | Demo video, submission logistics, theme-matched C4 PNG set, hosted-Azure judge URL |
| **DELIBERATELY-OUT** | 1 → **1** | Compliance gap detection — defense now on 3/3 judge surfaces |

### Top 5 outstanding items (risk-ranked)

1. **Demo video (A4)** — Not in repo; highest-weight deliverable gap before submission.
2. **Theme-matched C4 four-file set (A2)** — Interim `docs/architecture/OCE-architecture-C4.drawio` committed; `CURSOR-DIAGRAMS-C4.md` four-file + PNG exports still queued.
3. **Submission logistics** — Portal URL, deadline, video hosting rules not documented in repo.
4. **Practitioner quote / real-doc spot check (B7)** — Optional; synthetic honesty copy exists.
5. **Azure hosted go/no-go (D-026)** — Local demo is canonical; hosted path is optional for judges.

### Verification commands (this pass)

```text
$ make demo-gate
DEMO-GATE: GREEN with timing WARN — attempts_used=1; T→analysis 41.2s

$ make audit-norm
overall accuracy: 0.966 (399/413); unclassified 7.2% (32/445); routine closures: 55

$ curl -s localhost:8000/api/memory/review-queue | jq 'length'
32  (score band 0.57–0.65 on failure-unclassified rows)

$ docker compose exec -T backend pytest -q -m "not slow and not destructive and not llm"
72 passed

$ make test-llm
13 passed (9 expert benchmark + 4 LLM smokes)
```

---

## Section A — Expected deliverables

| # | Deliverable | Status | Evidence | Gap / action |
|---|-------------|--------|----------|--------------|
| **A1** | Working prototype | **MET** | `make demo-gate` GREEN on HEAD (timing WARN, `attempts_used=1`). Fresh-clone path: `README.md`. Tag: `demo-final-v3` (this pass). | Rehearse T−30m cache bookmark per `demo-checklist.md`. |
| **A2** | Architecture diagram | **PARTIAL** | Interim: `docs/architecture/OCE-architecture-C4.drawio`. | Theme-matched L1–L4 + PNG exports (`CURSOR-DIAGRAMS-C4.md`) still queued. |
| **A3** | Presentation deck | **MET** | `docs/OCE-pitch-deck.pptx` (6 slides). Slide 6 compliance card + `27 logged architecture decisions`. Cross-checked vs `FIGURES-CARD.md`. | — |
| **A4** | Demo video | **MISSING** | No `.mp4`/hosted link. | **Human:** 3–4 min recording + voiceover. |

**Submission logistics:** Still not in repo. **Human:** obtain from organizers.

---

## Section B — Evaluation focus

| # | Focus | Status | Evidence | Gap / action |
|---|-------|--------|----------|--------------|
| **B1** | Entity-extraction accuracy | **MET** | `make audit-norm` → **96.6%**; guard FP 0; `normalization_audit.py` + `test_truth_isolation.py`. Screenshot: `docs/screenshots/m14/ops-evals-accuracy.png`. | — |
| **B2** | Domain-expert benchmark Q&A | **MET** | `backend/tests/llm/test_expert_benchmark.py` (9 cases, structural assertions). `docs/expert-benchmark.md`. `make test-llm` → 9/9 pass. | Report failures as findings only (no product tuning). |
| **B3** | Knowledge-graph linkage completeness | **MET** | Live DB: **100%** assets with ≥1 doc (40/40); **92.8%** failure-row WOs normalized (413/445); **100%** sister-relation coverage. `FIGURES-CARD.md` linkage row. | — |
| **B4** | Time-to-answer vs traditional search | **PARTIAL** | Gate: **41.2s** T→analysis (WARN). Storyline **90s** narrative vs gate metric documented in `FIGURES-CARD.md`. | Reconcile talk-track on stage. |
| **B5** | Compliance gap detection | **DELIBERATELY-OUT** | **3/3 surfaces:** deck slide 6 compliance card; `docs/MVP-STORYLINE.md` epilogue; `docs/DEMO-SCRIPT.md` Q&A drill line. | — |
| **B6** | Cross-functional knowledge discovery | **MET** | Golden tests + `PatternPanel.tsx` ₹ formatting. Live dossier with both pattern rows (gate dossier 1). | Optional pattern-panel screenshot for deck. |
| **B7** | Real industrial document validation | **PARTIAL** | Synthetic honesty in `docs/MVP-STORYLINE.md`. OCR path: SOP-001 scanned page (`make ingest` log). | **Human:** optional practitioner quote. |

---

## Section C — Challenge statement & suggested-tech alignment

| # | Topic | Status | Evidence |
|---|-------|--------|----------|
| **C1** | Heterogeneous ingestion | **Partial** | PDF, OCR, CSV ✅; email archives ❌ |
| **C2** | Queryable / actionable / continuously updated | **Partial** | Queryable + actionable ✅; batch seed defense (D-011) ✅ |
| **C3** | Across any device | **PARTIAL** | **Verdict: degraded-but-readable** at 390px. Screenshots: `docs/screenshots/m14/mobile-*.png`. Nav hidden below `md`; dossier + evidence chip usable. Q&A line added to report. | Desktop-first by design for the control-room engineer; field-technician mobile is roadmap UX epic. |
| **C4** | Suggested technologies | **Mixed** | RAG ✅ D-015; KG ✅ D-004; OCR ✅; agentic ⚠️ D-020 linear orchestrator (documented in `DECISIONS.md`) |

---

## Section D — Cross-artifact consistency audit

### Number matrix (post-repair)

| Metric | FIGURES-CARD | Deck | MVP-STORYLINE | DEMO-SCRIPT | Live | Match? |
|--------|--------------|------|---------------|-------------|------|--------|
| Acute 3 / 22mo / 41.0h / ₹1.8Cr | ✅ | ✅ s4 | ✅ | ✅ | Golden tests | ✅ |
| Chronic 18 / 71mo / 99.1h / ₹4.5Cr | ✅ | ✅ s4 | ✅ | ✅ | Golden tests | ✅ |
| 96.6% (93.7% prior) | ✅ | ✅ s4 | ✅ | ✅ | audit-norm | ✅ verified |
| Review queue 32 / band | ✅ 0.57–0.65 | — | ✅ | ✅ | API | ✅ |
| Routine closures 55 | ✅ | — | — | ✅ | audit-norm | ✅ |
| Linkage 100% / 92.8% / 100% | ✅ | — | — | — | SQL | ✅ |
| Logged decisions | — | ✅ 27 | ✅ 27 | — | **27** `DECISIONS.md` | ✅ |
| T→analysis | ✅ 41.2s | — | 90s narrative | — | gate | ⚠️ B4 talk-track |

### Screenshot paths

| Artifact | Path | Status |
|----------|------|--------|
| Evals tab | `docs/screenshots/m14/ops-evals-accuracy.png` | ✅ |
| Memory overview | `docs/screenshots/m14/memory-overview-post-guard.png` | ✅ |
| Mobile Event Board | `docs/screenshots/m14/mobile-event-board-390.png` | ✅ |
| Mobile Dossier | `docs/screenshots/m14/mobile-dossier-390.png` | ✅ |
| Mobile evidence chip | `docs/screenshots/m14/mobile-evidence-chip-390.png` | ✅ |

---

## Section E — Judging-criteria readiness

Unchanged in substance; gate green + benchmark + screenshots strengthen Technical Excellence and UX evidence vs initial audit.

---

## Human decisions required (remaining)

1. **A4** — Schedule demo video recording before submission.
2. **A2** — Run `CURSOR-DIAGRAMS-C4.md` theme-matched four-file set if time allows.
3. **Submission logistics** — Portal URL, deadline (date + TZ), upload limits, video hosting → record in checklist.
4. **B7** — Practitioner quote or one real-document spot check (optional).
5. **D-026 / Azure** — Go/no-go on showing hosted instance to judges (credentials OOB).
6. **Team name** — Storyline footer set to **Team DKDVE** (GitHub org); confirm if official team name differs.

---

## Appendix — Gate output (HEAD, 2026-07-20)

```text
=== demo-gate ===
PASS — default test suite
PASS — golden suite
PASS — verify-seed (structure verified; ingest restored)
PASS — normalization audit (96.6%)
WARN — timed demo-event dossier (wall <60s, analysis <30s); attempts_used=1
  TIMING_WARN: time-to-analysis 41.2s >= 30s
PASS — groundedness walker (dossier 1)
PASS — prose-ID audit (dossier 1)
PASS — fallback replay cache (analysis-v4)
PASS — gate eval persistence (GATE_PERSIST)
DEMO-GATE: GREEN with timing WARN
```

*End of report. Verification pass after compliance remediation tasks 1–6.*
