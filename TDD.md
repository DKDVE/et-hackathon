# Technical Design Document — Operational Context Engine

**Version:** 1.0 | **Traces to:** PRD v1.0, ARCHITECTURE-PRINCIPLES.md (P1–P12), DECISIONS.md (D-000–D-013)
**Rule:** any implementation detail not derivable from this document plus the PRD is a gap in this document — fix the document, then the code.

---

## 1. System Overview

Two conceptual layers (P11), five runtime components:

**Operational Memory Layer (accumulates):** Ingestion Pipeline + PostgreSQL/pgvector substrate.
**Operational Context Engine (reconstructs):** OCE Context Service + LangGraph Reasoning Graph + API/Frontend.

```
[Simulator script]──┐
[Quick-log UI]──────┤→ POST /api/events (canonical Operational Event, P6)
                    │
        FastAPI backend
        ├── Ingestion Pipeline (offline/seed-time): parse → chunk → embed → normalize WOs
        ├── OCE Context Service (deterministic, P1/P2): assembles Shared Context
        ├── Reasoning Graph (LangGraph): Analysis → Recommendation → Evidence Validation → Report
        ├── LLM Client (OpenRouter, P7) + cached-fallback store (P9)
        └── SSE streaming of dossier sections to frontend# Technical Design Document — Operational Context Engine

**Version:** 1.0 | **Traces to:** PRD v1.0, ARCHITECTURE-PRINCIPLES.md (P1–P12), DECISIONS.md (D-000–D-013)
**Rule:** any implementation detail not derivable from this document plus the PRD is a gap in this document — fix the document, then the code.

---

## 1. System Overview

Two conceptual layers (P11), five runtime components:

**Operational Memory Layer (accumulates):** Ingestion Pipeline + PostgreSQL/pgvector substrate.
**Operational Context Engine (reconstructs):** OCE Context Service + LangGraph Reasoning Graph + API/Frontend.

```
[Simulator script]──┐
[Quick-log UI]──────┤→ POST /api/events (canonical Operational Event, P6)
                    │
        FastAPI backend
        ├── Ingestion Pipeline (offline/seed-time): parse → chunk → embed → normalize WOs
        ├── OCE Context Service (deterministic, P1/P2): assembles Shared Context
        ├── Reasoning Graph (LangGraph): Analysis → Recommendation → Evidence Validation → Report
        ├── LLM Client (OpenRouter, P7) + cached-fallback store (P9)
        └── SSE streaming of dossier sections to frontend
                    │
        PostgreSQL 16 + pgvector (single instance, D-004)
                    │
        React/TS/Tailwind/ShadCN frontend (Vite)
```

Everything runs under one `docker-compose.yml`: `db`, `backend`, `frontend`, plus a one-shot `seed` service (NFR-6).

---

## 2. Repository Structure

```
oce/
├── ARCHITECTURE-PRINCIPLES.md, DECISIONS.md, docs/prd.md, docs/tdd.md, CONTEXT.md
├── docker-compose.yml, .env.example
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, routers, CORS
│   │   ├── config.py                # pydantic-settings; all env-derived config
│   │   ├── db/                      # engine, session, models (SQLAlchemy 2.0), migrations (alembic)
│   │   ├── domain/                  # pydantic domain schemas = ubiquitous language (CONTEXT.md)
│   │   ├── memory/                  # OPERATIONAL MEMORY LAYER (P11)
│   │   │   ├── ingestion/           # pdf_parser.py, chunker.py, embedder.py, wo_normalizer.py
│   │   │   └── repositories/        # SQL access: assets.py, work_orders.py, chunks.py, events.py
│   │   ├── context/                 # OCE runtime (P11)
│   │   │   ├── assembler.py         # build_shared_context(event) — THE deterministic service (P1)
│   │   │   └── evidence.py          # evidence pool enumeration + Evidence Strength calc (P8)
│   │   ├── reasoning/
│   │   │   ├── graph.py             # LangGraph wiring
│   │   │   ├── state.py             # DossierState schema
│   │   │   ├── nodes/               # analysis.py, recommendation.py, validation.py, report.py
│   │   │   └── prompts/             # one file per node, versioned
│   │   ├── llm/                     # client.py (OpenRouter), fallback_cache.py (P9)
│   │   └── api/                     # routers: events.py, dossiers.py, assets.py, sources.py, chat.py
│   └── tests/                       # unit/, golden/ (PRD §17), audits/ (groundedness, normalization)
├── frontend/src/
│   ├── routes/                      # EventBoard, DossierView, AssetRegistry
│   ├── components/dossier/          # SafetyNotes, CauseCard, EvidenceChip, Timeline, SimilarIncidents, PatternPanel, ChatDrawer
│   ├── components/source/           # SourceViewer (PDF page / WO record)
│   └── lib/                         # api client, SSE hook, types (generated from OpenAPI)
├── dataset/
│   ├── design/                      # THE RELATIONAL TRUTH (P10): meridian.yaml — plants, units, assets,
│   │                                #   classes, failure_modes, WOs, incidents, docs metadata, planted pattern
│   ├── generators/                  # render_wo.py, render_manual.py, render_sop.py, render_reports.py → PDFs/CSVs
│   └── rendered/                    # generated artifacts consumed by seed
└── scripts/seed.py                  # wipe → load design → run ingestion → verify counts; idempotent
```

---

## 3. Database Schema (physical; alembic migration 0001)

pgvector extension enabled. Embedding dim 1024 (config-driven; see §9 model choice).

```sql
asset_classes(id PK, manufacturer, model, class_name, description)
assets(id PK, tag UNIQUE, name, asset_class_id FK, plant, unit, area,
       service_duty, criticality ENUM(A,B,C), installed_on DATE)
failure_modes(id PK, code UNIQUE, name, description, embedding vector(1024))
work_orders(id PK, wo_number UNIQUE, asset_id FK, opened_on, closed_on,
       raw_description TEXT, actions_taken TEXT, downtime_hours NUMERIC,
       failure_mode_id FK NULL, normalization_score REAL NULL)   -- D-008
operational_events(id PK, asset_id FK, source ENUM(manual,simulated,integration),  -- D-011/P6
       symptom_category, note TEXT, criticality, status ENUM(open,reviewed,closed),
       occurred_at TIMESTAMPTZ, created_at)
documents(id PK, doc_type ENUM(oem_manual,sop,inspection_report,incident_report,pid_drawing,
       spares_catalogue,pm_schedule), title, file_path,
       asset_id FK NULL, asset_class_id FK NULL)                 -- owned by asset OR class
chunks(id PK, document_id FK, page INT, section_ref TEXT, content TEXT,
       embedding vector(1024))
       + INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
dossiers(id PK, event_id FK UNIQUE, status ENUM(assembling,reasoning,complete,failed),
       shared_context JSONB,          -- frozen snapshot, audit trail for P4
       sections JSONB,                -- validated node outputs
       created_at, completed_at)
evidence_links(id PK, dossier_id FK, claim_ref TEXT,             -- e.g. "cause:1"
       evidence_kind ENUM(work_order,chunk), work_order_id FK NULL, chunk_id FK NULL,
       CHECK (one of the two FKs is set))
```

Sister-asset queries are joins (D-004): same `asset_class_id`, or same `service_duty`. Pattern panel (FR-12) is `GROUP BY failure_mode_id` over sister WOs.

---

## 4. Canonical IDs — the Evidence contract

Every Shared Context item carries a stable citation ID: `WO-{wo_number}` and `CH-{chunk_id}`. Prompts present these IDs; nodes must cite them; validation is set-membership against the enumerated pool (P3/P4). This contract is the spine of the system — it appears in the assembler, every prompt, the validator, `evidence_links`, and the frontend EvidenceChip.

---

## 5. OCE Context Service (`context/assembler.py`) — deterministic, P1/P2

`build_shared_context(event_id) -> SharedContext` (pure function of DB state; no LLM):

1. **Asset profile:** asset + class + location + criticality (1 query).
2. **Failure history:** all WOs for this asset, newest first, capped 30.
3. **Sister incidents:** WOs on sister assets **filtered to failure modes plausible for the symptom category** via a small static symptom→failure-mode map in `domain/` (curated, ~1 screen of YAML; deterministic per P2), capped 20.
4. **Document chunks:** pgvector cosine search, query = symptom category + note text, **scoped** to documents owned by this asset or its class; top-12 manual chunks, top-8 SOP chunks, top-6 inspection/incident-report chunks. Recall over precision (D-005 mitigation).
5. **Pattern stats (FR-12):** deterministic aggregate — occurrences, span months, cumulative downtime, distinct raw phrasings — per failure mode across the sister set.
6. Freeze as `SharedContext` (pydantic, `model_config frozen=True`), snapshot into `dossiers.shared_context`, enumerate evidence pool IDs.

Target: <2s on seed data (NFR-1). Unit-tested against golden fixtures — same event, same context, byte-identical.

---

## 6. Reasoning Graph (LangGraph)

**State (`state.py`):** `{ shared_context: SharedContext (frozen), analysis: AnalysisOutput|None, recommendation: RecommendationOutput|None, validated: ValidatedDossier|None, report: DossierReport|None, errors: list }`. Nodes read `shared_context`, write only their own slot. Linear graph, supervisor = LangGraph entry wiring + failure routing (a node exception routes to degraded-report path, not a retry storm).

**Node contracts (all outputs = pydantic schemas via structured output / JSON mode):**

- **Analysis** → `probable_causes: [{statement, mechanism_explanation, evidence_ids: [str], asset_specific_notes}]` (3–5 causes). Prompt receives the full Shared Context with citation IDs and the instruction: *cite only listed IDs; if reasoning beyond evidence, leave evidence_ids empty.*
- **Recommendation** → `{safety_notes: [{text, evidence_ids}], actions: [{text, rationale, evidence_ids, sop_refs}]}`. Safety notes must cite SOP chunks or be dropped by validation — safety is never a hypothesis.
- **Evidence Validation** — two stages. *Stage 1 (deterministic code, P2, runs first):* strip citation IDs not in the pool; a claim with zero surviving IDs → provisional Hypothesis. *Stage 2 (LLM):* for each surviving claim, judge whether cited items actually support it; unsupported citations removed, claim relabeled Hypothesis if emptied. Safety notes that become Hypotheses are deleted, not labeled. Output: `ValidatedDossier` with `grounding: evidenced|hypothesis` per claim.
- **Report** → orders sections per PRD §9, computes nothing, formats `DossierReport` JSON for the frontend and persists `sections` + `evidence_links`.

**Evidence Strength (computed in `context/evidence.py`, after validation, never in a node — P8/D-003):** per cause, over its surviving evidence set:
`score = min(count,4)*1.0 + distinct_source_types*1.5 + (2.0 if newest_supporting_record < 24 months else 0.5) + min(distinct_sister_assets,3)*1.5` → **Strong ≥ 8, Moderate ≥ 4, else Weak.** Constants in `config.py`; full component breakdown stored alongside the tier (exposed via API for Q&A, only the tier renders in UI, per founder amendment to D-003).

---

## 7. API Design (FastAPI, OpenAPI-first; frontend types generated)

```
POST /api/events                       # canonical intake (P6): {asset_tag, source, symptom_category, note, criticality}
GET  /api/events?status=               # event board
GET  /api/events/{id}
POST /api/events/{id}/dossier          # idempotent: returns existing dossier if present
GET  /api/dossiers/{id}/stream         # SSE: section events (see below)
GET  /api/dossiers/{id}                # full dossier JSON (post-completion / refresh)
POST /api/dossiers/{id}/chat           # FR-9: {question} → cited answer or refusal; context = frozen shared_context only
GET  /api/sources/wo/{wo_number}       # WO record for SourceViewer
GET  /api/sources/chunk/{chunk_id}     # chunk + document file ref + page for PDF deep-link
GET  /api/assets, /api/assets/{tag}
GET  /api/dossiers/{id}/evidence/{claim_ref}  # Evidence Strength breakdown (backend explainability)
```

**SSE event sequence** (drives progressive rendering, NFR-1/P5): `context_ready` (asset profile, history, sister incidents, pattern stats — renderable instantly) → `analysis` → `recommendation` → `validated` (final grounding labels + strength tiers) → `report_complete` | `degraded` (context-only dossier + cached-fallback flag, P9). Frontend renders deterministic sections at `context_ready`; AI sections appear as they stream — the demo's "assembles before your eyes" moment is this event sequence.

---

## 8. Ingestion Pipeline (`memory/ingestion/`, seed-time for MVP)

1. **Documents:** pypdf text extraction; OCR fallback (tesseract) only if a page yields <30 chars — our generated PDFs are text-native, so OCR is an honest capability demo on 1–2 deliberately scanned pages, not a dependency. Chunking: structure-aware (split on section headings, ~800-token target, page + section_ref preserved — FR-3).
2. **Embeddings:** local `sentence-transformers/BAAI/bge-large-en-v1.5` via `llm/embeddings.py` (D-014) — batched, L2-normalized, config-driven; no network at ingest runtime.
3. **WO normalization (D-008):** embed `raw_description`, cosine vs `failure_modes.embedding`; assign if top score ≥ 0.60 *and* margin over runner-up ≥ 0.05, else `unclassified`. Thresholds in config; normalization audit (tests/audits) prints the confusion table and unclassified rate against `dataset/design` ground truth (the design file knows each WO's true mode — planted data gives us free labels).

---

## 9. LLM Client (`llm/`)

Single `LLMClient` over OpenRouter chat-completions API (P7). Per-node model map in config, e.g. `analysis: anthropic/claude-sonnet-4.6`, `validation: anthropic/claude-sonnet-4.6`, `report/chat: cheaper fast model`; embeddings via an OpenRouter-served embedding model, dim pinned in config and migration. Policies: 60s timeout, 2 retries with jitter, structured-output enforcement (schema in request; on parse failure, one repair round-trip, then node-failure path). **Fallback cache (P9):** `fallback_cache.py` records the full SSE event sequence per dossier; `DEMO_FALLBACK=1` + LLM failure → replay cached sequence for the demo event, UI badge "cached reasoning" (honesty on stage).

---

## 10. Frontend Design

Routes: `/events` (board), `/events/:id` (DossierView), `/assets`. DossierView = fixed section order (PRD §9): SafetyNotes (visually dominant, amber-on-dark) → CauseCards (statement, mechanism, EvidenceChips, StrengthBadge, Hypothesis styling = dashed border + explicit label) → Actions → History timeline → SimilarIncidents → **PatternPanel** (FR-12 — the reveal; render prominent, count + months + downtime ₹ + the distinct raw phrasings verbatim) → Manual/SOP extracts → ChatDrawer. SourceViewer: WO record view; PDF via `react-pdf` opened at cited page, section highlighted where section_ref present. SSE hook appends sections with subtle entrance transitions — cinematic but restrained (NFR-9: dark-first, industrial, ShadCN throughout). Stitch MCP may be used for initial component scaffolds; outputs must be normalized to the ShadCN token system before merge.

---

## 11. Dataset & Seed (D-010/D-013, P10)

`dataset/design/meridian.yaml` is the single source of truth: 2 plants, 4 units, ~40 assets, ~25 failure modes, ~500 WOs (each with `true_failure_mode` ground-truth label and authored raw text), incidents, document metadata, and the **planted pattern** (mech-seal failure: P-3401/P-3402/P-3105, 3 occurrences, 22 months, 41 downtime hours, three distinct phrasings). Generators render documents *from* the design (P10): hero asset class = Tier 1 (full OEM manual ~40pp, SOPs, inspection + incident reports); other classes = Tier 2/3 (registry-complete, thin docs). 2 static P&ID images referenced by documents table (set-dressing; not parsed — PRD §15). `scripts/seed.py`: idempotent, ends with count verification + one golden dossier smoke-assembly. Fresh-laptop test is a pre-demo checklist item (NFR-6).

---

## 12. Failure Modes & Degradation Paths

| Failure | Behavior |
|---|---|
| OpenRouter down/rate-limited | Retries → degraded dossier (deterministic sections only, P5) → demo event: cached replay (P9) |
| Node emits invalid JSON | One repair attempt → node-failure → degraded path; never a blank screen |
| Node cites unknown ID | Stage-1 validator strips silently; count logged for audit |
| Retrieval returns nothing (edge asset) | Dossier renders with honest empty-states ("No prior failures recorded for this asset") |
| SSE disconnect | Frontend falls back to polling `GET /api/dossiers/{id}` |

---

## 13. Testing (full strategy doc later; commitments now)

Unit: assembler determinism, Evidence Strength arithmetic, normalizer thresholds, Stage-1 validator. Golden (PRD §17): 15 scenarios with expected evidence IDs. Audits: groundedness walker (every claim evidenced or labeled — NFR-2, run in CI-ish pre-demo gate), normalization confusion table. Manual: 3 demo dry-runs incl. cold-start and network-kill.

## 14. Build Milestones (each = one Cursor prompt scope, D-006 discipline)

M1 repo scaffold + compose + migrations + config → M2 dataset design file + generators + seed → M3 ingestion pipeline + normalization audit → M4 OCE assembler + evidence module + golden fixtures → M5 API + SSE skeleton (deterministic dossier end-to-end, P5 demoable) → M6 LangGraph nodes + validation + fallback cache → M7 frontend Event Board + DossierView + SourceViewer → M8 chat drawer + pattern panel polish + report → M9 audits, dry-runs, demo hardening. **M5 is the safety milestone: if everything after it slips, we still demo an honest deterministic product.**
                    │
        PostgreSQL 16 + pgvector (single instance, D-004)
                    │
        React/TS/Tailwind/ShadCN frontend (Vite)
```

Everything runs under one `docker-compose.yml`: `db`, `backend`, `frontend`, plus a one-shot `seed` service (NFR-6).

---

## 2. Repository Structure

```
oce/
├── ARCHITECTURE-PRINCIPLES.md, DECISIONS.md, docs/prd.md, docs/tdd.md, CONTEXT.md
├── docker-compose.yml, .env.example
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, routers, CORS
│   │   ├── config.py                # pydantic-settings; all env-derived config
│   │   ├── db/                      # engine, session, models (SQLAlchemy 2.0), migrations (alembic)
│   │   ├── domain/                  # pydantic domain schemas = ubiquitous language (CONTEXT.md)
│   │   ├── memory/                  # OPERATIONAL MEMORY LAYER (P11)
│   │   │   ├── ingestion/           # pdf_parser.py, chunker.py, embedder.py, wo_normalizer.py
│   │   │   └── repositories/        # SQL access: assets.py, work_orders.py, chunks.py, events.py
│   │   ├── context/                 # OCE runtime (P11)
│   │   │   ├── assembler.py         # build_shared_context(event) — THE deterministic service (P1)
│   │   │   └── evidence.py          # evidence pool enumeration + Evidence Strength calc (P8)
│   │   ├── reasoning/
│   │   │   ├── graph.py             # LangGraph wiring
│   │   │   ├── state.py             # DossierState schema
│   │   │   ├── nodes/               # analysis.py, recommendation.py, validation.py, report.py
│   │   │   └── prompts/             # one file per node, versioned
│   │   ├── llm/                     # client.py (OpenRouter), fallback_cache.py (P9)
│   │   └── api/                     # routers: events.py, dossiers.py, assets.py, sources.py, chat.py
│   └── tests/                       # unit/, golden/ (PRD §17), audits/ (groundedness, normalization)
├── frontend/src/
│   ├── routes/                      # EventBoard, DossierView, AssetRegistry
│   ├── components/dossier/          # SafetyNotes, CauseCard, EvidenceChip, Timeline, SimilarIncidents, PatternPanel, ChatDrawer
│   ├── components/source/           # SourceViewer (PDF page / WO record)
│   └── lib/                         # api client, SSE hook, types (generated from OpenAPI)
├── dataset/
│   ├── design/                      # THE RELATIONAL TRUTH (P10): meridian.yaml — plants, units, assets,
│   │                                #   classes, failure_modes, WOs, incidents, docs metadata, planted pattern
│   ├── generators/                  # render_wo.py, render_manual.py, render_sop.py, render_reports.py → PDFs/CSVs
│   └── rendered/                    # generated artifacts consumed by seed
└── scripts/seed.py                  # wipe → load design → run ingestion → verify counts; idempotent
```

---

## 3. Database Schema (physical; alembic migration 0001)

pgvector extension enabled. Embedding dim 1024 (config-driven; see §9 model choice).

```sql
asset_classes(id PK, manufacturer, model, class_name, description)
assets(id PK, tag UNIQUE, name, asset_class_id FK, plant, unit, area,
       service_duty, criticality ENUM(A,B,C), installed_on DATE)
failure_modes(id PK, code UNIQUE, name, description, embedding vector(1024))
work_orders(id PK, wo_number UNIQUE, asset_id FK, opened_on, closed_on,
       raw_description TEXT, actions_taken TEXT, downtime_hours NUMERIC,
       failure_mode_id FK NULL, normalization_score REAL NULL)   -- D-008
operational_events(id PK, asset_id FK, source ENUM(manual,simulated,integration),  -- D-011/P6
       symptom_category, note TEXT, criticality, status ENUM(open,reviewed,closed),
       occurred_at TIMESTAMPTZ, created_at)
documents(id PK, doc_type ENUM(oem_manual,sop,inspection_report,incident_report,pid_drawing,
       spares_catalogue,pm_schedule), title, file_path,
       asset_id FK NULL, asset_class_id FK NULL)                 -- owned by asset OR class
chunks(id PK, document_id FK, page INT, section_ref TEXT, content TEXT,
       embedding vector(1024))
       + INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
dossiers(id PK, event_id FK UNIQUE, status ENUM(assembling,reasoning,complete,failed),
       shared_context JSONB,          -- frozen snapshot, audit trail for P4
       sections JSONB,                -- validated node outputs
       created_at, completed_at)
evidence_links(id PK, dossier_id FK, claim_ref TEXT,             -- e.g. "cause:1"
       evidence_kind ENUM(work_order,chunk), work_order_id FK NULL, chunk_id FK NULL,
       CHECK (one of the two FKs is set))
```

Sister-asset queries are joins (D-004): same `asset_class_id`, or same `service_duty`. Pattern panel (FR-12) is `GROUP BY failure_mode_id` over sister WOs.

---

## 4. Canonical IDs — the Evidence contract

Every Shared Context item carries a stable citation ID: `WO-{wo_number}` and `CH-{chunk_id}`. Prompts present these IDs; nodes must cite them; validation is set-membership against the enumerated pool (P3/P4). This contract is the spine of the system — it appears in the assembler, every prompt, the validator, `evidence_links`, and the frontend EvidenceChip.

---

## 5. OCE Context Service (`context/assembler.py`) — deterministic, P1/P2

`build_shared_context(event_id) -> SharedContext` (pure function of DB state; no LLM):

1. **Asset profile:** asset + class + location + criticality (1 query).
2. **Failure history:** all WOs for this asset, newest first, capped 30.
3. **Sister incidents:** WOs on sister assets **filtered to failure modes plausible for the symptom category** via a small static symptom→failure-mode map in `domain/` (curated, ~1 screen of YAML; deterministic per P2), capped 20.
4. **Document chunks:** pgvector cosine search, query = symptom category + note text, **scoped** to documents owned by this asset or its class; top-12 manual chunks, top-8 SOP chunks, top-6 inspection/incident-report chunks. Recall over precision (D-005 mitigation).
5. **Pattern stats (FR-12):** deterministic aggregate — occurrences, span months, cumulative downtime, distinct raw phrasings — per failure mode across the sister set.
6. Freeze as `SharedContext` (pydantic, `model_config frozen=True`), snapshot into `dossiers.shared_context`, enumerate evidence pool IDs.

Target: <2s on seed data (NFR-1). Unit-tested against golden fixtures — same event, same context, byte-identical.

---

## 6. Reasoning Graph (LangGraph)

**State (`state.py`):** `{ shared_context: SharedContext (frozen), analysis: AnalysisOutput|None, recommendation: RecommendationOutput|None, validated: ValidatedDossier|None, report: DossierReport|None, errors: list }`. Nodes read `shared_context`, write only their own slot. Linear graph, supervisor = LangGraph entry wiring + failure routing (a node exception routes to degraded-report path, not a retry storm).

**Node contracts (all outputs = pydantic schemas via structured output / JSON mode):**

- **Analysis** → `probable_causes: [{statement, mechanism_explanation, evidence_ids: [str], asset_specific_notes}]` (3–5 causes). Prompt receives the full Shared Context with citation IDs and the instruction: *cite only listed IDs; if reasoning beyond evidence, leave evidence_ids empty.*
- **Recommendation** → `{safety_notes: [{text, evidence_ids}], actions: [{text, rationale, evidence_ids, sop_refs}]}`. Safety notes must cite SOP chunks or be dropped by validation — safety is never a hypothesis.
- **Evidence Validation** — two stages. *Stage 1 (deterministic code, P2, runs first):* strip citation IDs not in the pool; a claim with zero surviving IDs → provisional Hypothesis. *Stage 2 (LLM):* for each surviving claim, judge whether cited items actually support it; unsupported citations removed, claim relabeled Hypothesis if emptied. Safety notes that become Hypotheses are deleted, not labeled. Output: `ValidatedDossier` with `grounding: evidenced|hypothesis` per claim.
- **Report** → orders sections per PRD §9, computes nothing, formats `DossierReport` JSON for the frontend and persists `sections` + `evidence_links`.

**Evidence Strength (computed in `context/evidence.py`, after validation, never in a node — P8/D-003):** per cause, over its surviving evidence set:
`score = min(count,4)*1.0 + distinct_source_types*1.5 + (2.0 if newest_supporting_record < 24 months else 0.5) + min(distinct_sister_assets,3)*1.5` → **Strong ≥ 8, Moderate ≥ 4, else Weak.** Constants in `config.py`; full component breakdown stored alongside the tier (exposed via API for Q&A, only the tier renders in UI, per founder amendment to D-003).

---

## 7. API Design (FastAPI, OpenAPI-first; frontend types generated)

```
POST /api/events                       # canonical intake (P6): {asset_tag, source, symptom_category, note, criticality}
GET  /api/events?status=               # event board
GET  /api/events/{id}
POST /api/events/{id}/dossier          # idempotent: returns existing dossier if present
GET  /api/dossiers/{id}/stream         # SSE: section events (see below)
GET  /api/dossiers/{id}                # full dossier JSON (post-completion / refresh)
POST /api/dossiers/{id}/chat           # FR-9: {question} → cited answer or refusal; context = frozen shared_context only
GET  /api/sources/wo/{wo_number}       # WO record for SourceViewer
GET  /api/sources/chunk/{chunk_id}     # chunk + document file ref + page for PDF deep-link
GET  /api/assets, /api/assets/{tag}
GET  /api/dossiers/{id}/evidence/{claim_ref}  # Evidence Strength breakdown (backend explainability)
```

**SSE event sequence** (drives progressive rendering, NFR-1/P5): `context_ready` (asset profile, history, sister incidents, pattern stats — renderable instantly) → `analysis` → `recommendation` → `validated` (final grounding labels + strength tiers) → `report_complete` | `degraded` (context-only dossier + cached-fallback flag, P9). Frontend renders deterministic sections at `context_ready`; AI sections appear as they stream — the demo's "assembles before your eyes" moment is this event sequence.

---

## 8. Ingestion Pipeline (`memory/ingestion/`, seed-time for MVP)

1. **Documents:** pypdf text extraction; OCR fallback (tesseract) only if a page yields <30 chars — our generated PDFs are text-native, so OCR is an honest capability demo on 1–2 deliberately scanned pages, not a dependency. Chunking: structure-aware (split on section headings, ~800-token target, page + section_ref preserved — FR-3).
2. **Embeddings:** local `sentence-transformers/BAAI/bge-large-en-v1.5` via `llm/embeddings.py` (D-014) — batched, L2-normalized, config-driven; no network at ingest runtime.
3. **WO normalization (D-008):** embed `raw_description`, cosine vs `failure_modes.embedding`; assign if top score ≥ 0.60 *and* margin over runner-up ≥ 0.05, else `unclassified`. Thresholds in config; normalization audit (tests/audits) prints the confusion table and unclassified rate against `dataset/design` ground truth (the design file knows each WO's true mode — planted data gives us free labels).

---

## 9. LLM Client (`llm/`)

Single `LLMClient` over OpenRouter chat-completions API (P7). Per-node model map in config, e.g. `analysis: anthropic/claude-sonnet-4.6`, `validation: anthropic/claude-sonnet-4.6`, `report/chat: cheaper fast model`; embeddings via an OpenRouter-served embedding model, dim pinned in config and migration. Policies: 60s timeout, 2 retries with jitter, structured-output enforcement (schema in request; on parse failure, one repair round-trip, then node-failure path). **Fallback cache (P9):** `fallback_cache.py` records the full SSE event sequence per dossier; `DEMO_FALLBACK=1` + LLM failure → replay cached sequence for the demo event, UI badge "cached reasoning" (honesty on stage).

---

## 10. Frontend Design

Routes: `/events` (board), `/events/:id` (DossierView), `/assets`. DossierView = fixed section order (PRD §9): SafetyNotes (visually dominant, amber-on-dark) → CauseCards (statement, mechanism, EvidenceChips, StrengthBadge, Hypothesis styling = dashed border + explicit label) → Actions → History timeline → SimilarIncidents → **PatternPanel** (FR-12 — the reveal; render prominent, count + months + downtime ₹ + the distinct raw phrasings verbatim) → Manual/SOP extracts → ChatDrawer. SourceViewer: WO record view; PDF via `react-pdf` opened at cited page, section highlighted where section_ref present. SSE hook appends sections with subtle entrance transitions — cinematic but restrained (NFR-9: dark-first, industrial, ShadCN throughout). Stitch MCP may be used for initial component scaffolds; outputs must be normalized to the ShadCN token system before merge.

---

## 11. Dataset & Seed (D-010/D-013, P10)

`dataset/design/meridian.yaml` is the single source of truth: 2 plants, 4 units, ~40 assets, ~25 failure modes, ~500 WOs (each with `true_failure_mode` ground-truth label and authored raw text), incidents, document metadata, and the **planted pattern** (mech-seal failure: P-3401/P-3402/P-3105, 3 occurrences, 22 months, 41 downtime hours, three distinct phrasings). Generators render documents *from* the design (P10): hero asset class = Tier 1 (full OEM manual ~40pp, SOPs, inspection + incident reports); other classes = Tier 2/3 (registry-complete, thin docs). 2 static P&ID images referenced by documents table (set-dressing; not parsed — PRD §15). `scripts/seed.py`: idempotent, ends with count verification + one golden dossier smoke-assembly. Fresh-laptop test is a pre-demo checklist item (NFR-6).

---

## 12. Failure Modes & Degradation Paths

| Failure | Behavior |
|---|---|
| OpenRouter down/rate-limited | Retries → degraded dossier (deterministic sections only, P5) → demo event: cached replay (P9) |
| Node emits invalid JSON | One repair attempt → node-failure → degraded path; never a blank screen |
| Node cites unknown ID | Stage-1 validator strips silently; count logged for audit |
| Retrieval returns nothing (edge asset) | Dossier renders with honest empty-states ("No prior failures recorded for this asset") |
| SSE disconnect | Frontend falls back to polling `GET /api/dossiers/{id}` |

---

## 13. Testing (full strategy doc later; commitments now)

Unit: assembler determinism, Evidence Strength arithmetic, normalizer thresholds, Stage-1 validator. Golden (PRD §17): 15 scenarios with expected evidence IDs. Audits: groundedness walker (every claim evidenced or labeled — NFR-2, run in CI-ish pre-demo gate), normalization confusion table. Manual: 3 demo dry-runs incl. cold-start and network-kill.

## 14. Build Milestones (each = one Cursor prompt scope, D-006 discipline)

M1 repo scaffold + compose + migrations + config → M2 dataset design file + generators + seed → M3 ingestion pipeline + normalization audit → M4 OCE assembler + evidence module + golden fixtures → M5 API + SSE skeleton (deterministic dossier end-to-end, P5 demoable) → M6 LangGraph nodes + validation + fallback cache → M7 frontend Event Board + DossierView + SourceViewer → M8 chat drawer + pattern panel polish + report → M9 audits, dry-runs, demo hardening. **M5 is the safety milestone: if everything after it slips, we still demo an honest deterministic product.**