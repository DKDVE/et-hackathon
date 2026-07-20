# ET Hackathon Compliance Report — Operational Context Engine

**Audit date:** 2026-07-20  
**Problem statement:** [docs/ET_hackathon.pdf](ET_hackathon.pdf) — *AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain*  
**Method:** Repo artifacts, code paths, and commands run in this environment. Claims without file/command evidence are findings, not passes. **No product fixes** were made during this pass.

---

## Executive summary

| Status | Count | Notes |
|--------|------:|-------|
| **MET** | 8 | Mostly code-level proofs; few judge-facing deliverables |
| **PARTIAL** | 14 | Working substrate + tests exist; live/demo artifacts incomplete |
| **MISSING** | 6 | Deck, C4 diagrams, demo video, screenshots, benchmark framing, submission logistics |
| **DELIBERATELY-OUT** | 1 | Compliance gap detection (B5) — defense incomplete in judge-facing materials |

### Top 5 outstanding items (risk-ranked)

1. **Demo video (A4)** — Not in repo; highest-weight deliverable gap before submission.
2. **Presentation deck `OCE-pitch-deck.pptx` (A3)** — Absent; cannot cross-check stage numbers or compliance roadmap slide (B5).
3. **C4 architecture package (A2)** — No `docs/architecture/`; no PNG exports; judges expecting a diagram will find only `ArchitecturePrinciples.md` / `TDD.md`.
4. **`make demo-gate` not re-run this audit** — Docker daemon unavailable (`unix:///var/run/docker.sock`); prototype gate status unverified on current `HEAD` (15 commits past `demo-final-v2`).
5. **Cross-artifact number drift** — “26 logged decisions” vs 19 `DECISIONS.md` entries; review-queue score band disagrees across docs; `FIGURES-CARD` screenshot paths point at missing files.

### Environment blockers (this audit)

```text
$ make up
unable to get image 'et-hackathon-backend': failed to connect to the docker API at unix:///var/run/docker.sock

$ make demo-gate / make audit-norm
(not run — require compose DB + backend container)

$ cd backend && .venv/bin/pytest -q -m "not slow and not destructive and not llm"
45 passed, 20 failed, 7 errors — failures are sqlalchemy OperationalError (no local Postgres on :5432)
```

---

## Section A — Expected deliverables

| # | Deliverable | Status | Evidence | Gap / action |
|---|-------------|--------|----------|--------------|
| **A1** | Working prototype | **PARTIAL** | Fresh-clone path: `README.md` L16–30 (`git clone`, `make dataset/up/seed/ingest`). Tag exists: `git tag -l` → `demo-final-v2` at `76fd6e0` (2026-07-08). **HEAD is ahead:** `0fb48d7` (+15 commits, 33 files vs tag). `Makefile` L56–57 `demo-gate` → `scripts/demo_gate.sh`. | **Gate not run** (Docker down). Re-run `make demo-gate` on a warm stack before submission; consider re-tagging if `HEAD` is the demo truth. |
| **A2** | Architecture diagram | **MISSING** | No `docs/architecture/`. Glob: zero `*.c4`, zero architecture PNGs. Closest: `ArchitecturePrinciples.md`, `TDD.md`, `PRD.md`. | Produce C4 L1–L4 + PNG exports; spot-check 5 named elements against code after creation. |
| **A3** | Presentation deck | **MISSING** | Glob: no `OCE-pitch-deck.pptx` in repo or at `demo-final-v2` (`git ls-tree -r demo-final-v2`). | Add deck; extract-text audit vs `docs/FIGURES-CARD.md` (blocked until file exists). |
| **A4** | Demo video | **MISSING** | No `.mp4`/hosted link in repo. Plan only: `docs/demo-checklist.md` L172–175 (“Dry-run 3 recorded as backup video”). | **Top deliverable:** 3–4 min screen recording + voiceover per problem statement; host per portal rules (unknown — see Human decisions). |

**Submission logistics:** Not documented in repo (grep: no portal URL, deadline time, file-size limits, video hosting). **HUMAN:** Obtain from organizers and record in checklist.

---

## Section B — Evaluation focus

| # | Focus | Status | Evidence | Gap / action |
|---|-------|--------|----------|--------------|
| **B1** | Entity-extraction accuracy | **PARTIAL** | **Firewall:** `backend/tests/test_truth_isolation.py` — only audit may reference `work_orders_truth.csv`. **Audit module:** `backend/tests/audits/normalization_audit.py` (accuracy ≥0.90, guard FP ≤1, planted WOs). **Doc types:** PDF (`pdf_parser.py`), OCR fallback (`pytesseract`, SOP-001 `dataset/design/meridian.yaml` L1588–1608 `scanned_page: true`; `render_sops.py` L4–6), CSV WO ingest (`render_wo.py`). **`make audit-norm` not run** (Docker). | Paste live audit output before demo; expect **96.6% / 32 queue / 55 routine** per `FIGURES-CARD.md` if substrate unchanged. |
| **B2** | Domain-expert benchmark Q&A | **PARTIAL** | **Golden:** 12 scenarios × 4 invariant tests = 48 (`scenarios.yaml`, `test_scenarios.py`); +11 demo-event tests (`test_demo_event_context.py`); +2 assembler +3 lexical = **64 slow-marked checks**. **LLM smokes:** 4 tests in `test_llm_reasoning.py` (SSE, cited chat, refusal, trace). | **No artifact titled “domain-expert benchmark”.** HUMAN: add ~8–10 expert-phrased Q&A pairs + one-paragraph benchmark description (small pre-freeze exception). |
| **B3** | Knowledge-graph linkage completeness | **PARTIAL** | **D-004:** typed relational graph in Postgres (`DECISIONS.md` L54–61). **Design-time:** 40/40 assets have ≥1 document via class/asset ownership (`catalogue.all_documents` + `meridian.yaml` assets; script output **100%**). **Truth corpus:** 445 failure rows / 500 WOs (`work_orders_truth.csv`). **FR-12:** `scripts/seed.py` `_pattern_query_check` → 3 / 22mo / 41.0h. **Chunk resolve:** `test_e2e_deterministic.py::test_cited_chunk_resolves_to_source_with_page`. | **Linkage % not in `FIGURES-CARD.md`** (requested but absent). **Live DB metrics not computed** (no compose). HUMAN: run SQL on seeded DB and add row to FIGURES-CARD. |
| **B4** | Time-to-answer vs traditional search | **PARTIAL** | **90s narrative:** `docs/storyline.md` L39, L85. **Gate timing:** `FIGURES-CARD.md` L50 → **37.8s** T→analysis (WARN band 38–48s); `demo_gate_timing.py` thresholds wall **<60s**, analysis **<30s**. **2–4h baseline:** `PRD.md` L36, `storyline.md` L15 (McKinsey / problem framing). | Reconcile “90s time-to-context” vs gate’s **37.8s** / **<60s wall** in deck talk-track. No fresh gate log on current `HEAD`. |
| **B5** | Compliance gap detection | **DELIBERATELY-OUT** | **Roadmap (not deck):** `storyline.md` L97 — “compliance intelligence mapping regulations…” as H3. **Epilogue vision:** same. **DEMO-SCRIPT Q&A:** only normalization queue (`DEMO-SCRIPT.md` L33–34) — **no compliance-out defense**. **Deck s6:** N/A (deck missing). | Add explicit “out of MVP / H3” line to deck roadmap slide, `DEMO-SCRIPT.md` Q&A, and keep epilogue — **2 of 3 judge surfaces missing**. |
| **B6** | Cross-functional knowledge discovery | **PARTIAL** | **FR-12 numbers enforced in tests:** `test_demo_event_context.py` L42–58 (3/22/41.0h); `test_e2e_deterministic.py` L117–120 (both pattern modes). **UI:** `PatternPanel.tsx` L60–68 renders ₹ via `formatInrImpact` (`impact.test.ts` L7–14). | **No live UI screenshot** at audit time (stack down). Capture pattern panel with ₹1.8Cr / ₹4.5Cr before submission. |
| **B7** | Real industrial document validation | **PARTIAL** | **Synthetic honesty:** `storyline.md` L75–79 (“synthetic by design”, planted pattern disclosed). **D-010:** `DECISIONS.md` L120–127. **Demo script Act 3:** `DEMO-SCRIPT.md` L3–4 references Act 3 but **no synthetic-disclosure Q&A #5**. | HUMAN: optional practitioner quote or spot-validation on one real doc; add Q&A #5 to demo script. |

---

## Section C — Challenge statement & suggested-tech alignment

| # | Topic | Status | Evidence |
|---|-------|--------|----------|
| **C1** | Heterogeneous ingestion | **Partial** | PDF ✅ `pdf_parser.py`; OCR ✅ SOP-001 scanned page; spreadsheets ✅ `spares.csv`, `pm_schedule.csv`, WO CSV. **Email archives:** not covered (no ingest path). |
| **C2** | Queryable / actionable / continuously updated | **Queryable ✅** dossier + chat (`dossiers.py` FR-9). **Actionable ✅** report export (`ReportView.tsx`). **Continuously updated:** **batch** `make seed` + `make ingest` (`README.md`); defense **D-011** adapters roadmap (`DECISIONS.md` L131–138, `storyline.md` L97). |
| **C3** | Across any device | **PARTIAL** (code review only) | `EventBoardContent.tsx` L63 `flex-col lg:flex-row` — filters stack on narrow viewports. `AppShell.tsx` L37 `nav hidden … md:flex` — **no mobile nav** below `md`. `DossierView.tsx` L142 `grid-cols-1 lg:grid-cols-12` — single column on phone. **390px browser test not run** (Vite EACCES on `node_modules/.vite`). | HUMAN: device-mode screenshots; expect **degraded** (usable read, weak navigation). |
| **C4** | Suggested technologies | **Mixed** | **RAG ✅** D-015 hybrid-lite. **KG/ontology ✅** D-004 + taxonomy (`failure_modes` + families D-017); claim in `storyline.md` L55. **CV/P&ID ❌ roadmap** — static PNGs, `render_registry.py` L4 “never parsed”; PRD §15 out. **OCR ✅** SOP-001 path above. **QMS ❌** not integrated. **Agentic ⚠️ deliberate linear graph** D-005/D-006 — **no standalone Q&A blurb** in demo materials (only ADR text). |

---

## Section D — Cross-artifact consistency audit

### Number matrix

| Metric | FIGURES-CARD | Deck | storyline.md | DEMO-SCRIPT | README | Live product | Match? |
|--------|--------------|------|--------------|-------------|--------|--------------|--------|
| Acute 3 / 22mo / 41.0h / ₹1.8Cr | ✅ L7–12 | *missing* | ✅ L45–46, L86 | ✅ L41 | — | Golden tests | ✅ docs agree |
| Chronic 18 / 71mo / 99.1h / ₹4.5Cr | ✅ L16–21 | *missing* | ✅ L47, L87 | ✅ L40 | — | Golden tests | ✅ docs agree |
| ₹4.5L/hr | ✅ L25 | *missing* | ✅ L88 | ✅ L43 | — | `config.py` D-021, `impact.test.ts` | ✅ |
| 96.6% (93.7% prior) | ✅ L31 | *missing* | ✅ L71, L89 | ✅ L8, L22 | — | audit-norm (not re-run) | ⚠️ unverified live |
| 90s time-to-context | — | *missing* | ✅ L39, L85 | — | — | gate 37.8s T→analysis | ⚠️ see B4 |
| Queue 32 / routine 55 | ✅ L32–33 | *missing* | ✅ L71, L91 | ✅ L28–29 | — | audit-norm (not re-run) | ⚠️ unverified live |
| 100% cited or Hypothesis | — | *missing* | ✅ L90 | — | — | `groundedness_audit.py` | ✅ mechanism exists |
| “26 logged decisions” | — | *missing* | ✅ L53 | — | — | **19** `## D-` entries in `DECISIONS.md` | ❌ **MISMATCH** |

### Other consistency / hygiene grep

| Check | Result |
|-------|--------|
| Stale `demo-final` (v2 intended) | Only `demo-final-v2` in `docs/demo-checklist.md` L1 — OK |
| Old Render URL in human-facing docs | None (`onrender`/`render.com` grep clean); Render archived under `docs/deploy-alternatives/render/` |
| `[team]` placeholder | Not found |
| TODO / TBD in docs | Not found in markdown deliverables |
| Leaked secret-like strings | `.env` contains `OPENROUTER_API_KEY` (gitignored per `.gitignore` L1); **not committed** — ensure never staged |
| `README.md` clone URL | Placeholder `<repo-url>` L18 — minor |
| Review-queue score band | `demo-checklist.md` **0.51–0.57** vs `DEMO-SCRIPT.md` **0.57–0.65** — ❌ **MISMATCH** |
| Screenshot paths | `FIGURES-CARD.md` L72–73 → `docs/screenshots/m14/*.png` — **directory absent** (0 PNGs in repo) |
| D-018 / D-021 / D-025 / D-026 cited in code | Present in `PatternPanel.tsx`, `config.py`, `infra/azure/` — **not all logged in `DECISIONS.md`** (only 19 entries total) |

---

## Section E — Judging-criteria readiness

*No scores — exhibits and attack surfaces only.*

### Innovation (25%)

| Strengths | Attack surface |
|-----------|----------------|
| Dossier-first inversion (D-001) with retrieval-once substrate (D-005) | “Just another RAG chatbot” if judges only see chat |
| FR-12 pattern = SQL GROUP BY, tested (`test_demo_event_context.py`) | Planted synthetic pattern — must disclose (storyline does) |
| Self-debugging governance arc (93.7→96.6%, D-024) in storyline + Evals UI | Arc is narrative-heavy without deck/screenshots |

### Business Impact (25%)

| Strengths | Attack surface |
|-----------|----------------|
| Quantified ₹1.8Cr / ₹4.5Cr with explicit ₹4.5L/hr assumption | Assumption is configured, not market-validated |
| 2–4h → sub-minute context (storyline + PRD) | 90s claim vs 37.8s gate metric inconsistency |
| Retiring-engineer / knowledge-cliff framing (problem statement aligned) | Synthetic Meridian — no real plant ROI |

### Technical Excellence (20%)

| Strengths | Attack surface |
|-----------|----------------|
| Ground-truth firewall test (`test_truth_isolation.py`) | `make demo-gate` not green-verified on current commit |
| Golden suite (64 checks) + groundedness walker | CI on `main` **failing** (last 3 runs failed per `gh run list`) |
| LangGraph 4-node graph + in-DB tracing (D-016) | Mypy `continue-on-error: true` in CI |

### Scalability (15%)

| Strengths | Attack surface |
|-----------|----------------|
| Single Postgres + pgvector deliberate choice (D-004) | No multi-tenant, no streaming ingest |
| Azure/CD path documented (`infra/azure/README.md`) | Hosted path not required for hackathon prototype |
| Dataset generator P10 (`meridian.yaml` → rendered) | Tier-2/3 assets thin by design (D-013) |

### User Experience (15%)

| Strengths | Attack surface |
|-----------|----------------|
| Fixed dossier section order (TDD §10); evidence chips → PDF page | **Mobile nav hidden** below `md` (`AppShell.tsx`) |
| Chat refusal path tested (`test_llm_reasoning.py`) | No demo video showing happy path |
| Dark industrial UI + Pattern panel ₹ formatting | Event board filter sidebar at 390px unverified |

---

## Human decisions required

1. **B2** — Adopt a named “domain-expert benchmark” (~8–10 Q&A pairs) or accept golden + LLM smokes as sufficient.
2. **B7** — Pursue practitioner quote / one real-document spot check or stay synthetic-only with current honesty copy.
3. **Submission logistics** — Portal URL, deadline (date + time + TZ), max upload size, video hosting rules → record in repo.
4. **C3** — Mobile verdict: run 390px pass on Dossier + Event Board; decide whether to fix nav or narrate “desktop-first MVP”.
5. **A4** — Schedule demo video recording (3–4 min) before submission; use `docs/demo-checklist.md` walkthrough.
6. **A1 / tag** — Re-run `make demo-gate` on Docker host; retag `demo-final-v3` if `HEAD` is canonical.
7. **B3** — Add linkage metrics to `FIGURES-CARD.md` after live DB query.
8. **B5** — Add compliance-deliberately-out defense to deck + `DEMO-SCRIPT.md` Q&A.

---

## Appendix — Commands attempted

```bash
# Tag verification
git tag -l '*demo*'          # demo-candidate, demo-final, demo-final-v2
git rev-parse HEAD           # 0fb48d708c30d66e32fbaae29f9a724bb8b9c2b6
git rev-parse demo-final-v2  # 76fd6e0fcc957fad914d33ee769f10eb4d3af828

# Design-time linkage (host Python, no DB)
# assets_with_doc: 40/40 (100.0%); truth failure rows: 445/500; catalogue docs: 60; missing rendered: 0

# Unit tests without DB
cd backend && .venv/bin/pytest -q -m "not slow and not destructive and not llm"
# 45 passed, 20 failed, 7 errors (OperationalError — no Postgres)

cd frontend && npm test -- --run
# 18 passed, 2 failed (dossierStream access-password tests)
```

---

*End of report. Written during compliance-only pass; no code fixes applied.*
