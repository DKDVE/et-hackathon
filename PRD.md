# Product Requirements Document — Operational Context Engine (OCE)

**Version:** 0.1 (Draft for founder review)
**Project:** ET AI Hackathon 2.0 — "AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain"
**Status:** Awaiting approval. This document is the single source of truth. All downstream artifacts (TDD, database design, Cursor prompts) must trace back to a requirement here.

---

## 0. Assumptions & Open Decisions

This PRD is written against explicit assumptions because hackathon constraints were not yet confirmed. Each assumption is cheap to revise now and expensive to revise after the TDD.

**A1 — Build window:** ~48 hours of effective build time, team of 2–4, Cursor Pro writing code.
**A2 — Dataset:** Organizers provide no usable industrial dataset. We build a synthetic plant dataset ourselves (see §12). If organizers *do* provide data, §12 adapts but the domain model does not.
**A3 — Demo format:** Live demo on our machine, 5–8 minutes, followed by Q&A.
**A4 — Judges:** Mixed technical/business panel; they will have seen 10+ RAG chatbots before us.

**Open decisions requiring founder sign-off (see §21):** OD-1 abnormality trigger source, OD-2 replacement of "confidence score" with deterministic Evidence Strength, OD-3 synthetic dataset as a first-class workstream.

---

## 1. Executive Summary

Industrial plants do not suffer from a lack of information. They suffer from a lack of *assembled context at the moment of decision*. When a critical pump starts vibrating at 3am, the answer to "what is wrong and what do I do" already exists — scattered across a CMMS, OEM manuals, SOP binders, inspection reports, and the memory of engineers who may have retired. Assembling it takes hours; the decision is needed in minutes.

The **Operational Context Engine (OCE)** inverts the interaction model of every document-AI product. The engineer does not search, and does not ask. When an abnormality occurs on an asset, OCE automatically reconstructs the complete operational context around that asset — its profile, failure history, sister-asset incidents, relevant OEM manual sections, applicable SOPs, probable causes, and recommended actions — every claim backed by traceable evidence. The output is a **Context Dossier**: the document a 30-year reliability veteran would assemble if they had four uninterrupted hours, delivered in under a minute.

The chatbot is one interface. The product is operational decision intelligence. The moat is the asset-centric knowledge substrate underneath it, which appreciates with every work order ingested.

---

## 2. Problem Definition

### 2.1 The core pain

A Reliability Engineer responding to an unexpected equipment abnormality must reconstruct context from at least five fragmented sources: the CMMS work-order history (structured but written in inconsistent technician shorthand), OEM manuals (hundreds of PDF pages, often scanned), SOPs and safety permits (document management system or paper), inspection/condition reports (shared drives), and tribal knowledge (people, who may be asleep, on leave, or retired). Industry interviews and published maintenance studies consistently place this reconstruction at 2–4 hours for a non-routine failure — during which the asset is down, the decision is delayed, or worse, the decision is made on incomplete context.

### 2.2 Why the pain persists

Each source system is individually fine. The failure is *integrative*: no system understands the **asset as an entity** with history, siblings, failure modes, and documentation. CMMS knows work orders; the DMS knows files; nobody knows "Pump P-3401."

### 2.3 Why existing solutions fail

Enterprise search and RAG chatbots retrieve *documents that match a query*. They fail on this problem for three structural reasons: (1) the engineer must know what to ask, which presumes the context they lack; (2) retrieval is text-similarity-based, so "seal weeping," "leakage at gland," and "mech seal gone" — the same failure in three technicians' vocabulary — never connect; (3) answers are generated, not evidenced, and no plant engineer stakes a shutdown decision on an uncited paragraph.

### 2.4 The consequence

Extended downtime (₹50L–₹2Cr/day for a mid-size process plant), repeat failures that were diagnosable from history, safety exposure from skipped SOP steps, and irreversible knowledge loss as senior engineers retire.

---

## 3. Product Vision

**One sentence:** OCE is the operational memory of the plant — it understands assets, not documents, and delivers decision-ready context the moment something goes wrong.

**Three horizons:**
- **H1 (MVP/hackathon):** One workflow — abnormality response — executed exceptionally well on one asset class, with full evidence traceability.
- **H2 (post-hackathon product):** Live CMMS/historian connectors, P&ID-derived asset connectivity, multi-plant, closed-loop learning (engineer feedback on dossiers improves ranking).
- **H3 (platform):** The industrial knowledge substrate other applications build on — planning, turnaround prep, onboarding, compliance audit — the "brain" the problem statement names.

**Anti-vision (explicitly not building):** a PDF chatbot, generic RAG, document search, or an agent showcase.

---

## 4. User Personas

### 4.1 Primary — Priya, Reliability Engineer
32, mechanical engineer, 7 years at Meridian Specialty Chemicals. Owns rotating-equipment reliability for one unit (~120 assets). Measured on unplanned downtime and MTBF. Her senior colleague Ramesh (31 years at the plant) retires in 8 months. She is competent, skeptical of AI, and trusts nothing without a source. **Her bar: "Show me the work order number."**

### 4.2 Secondary (design-aware, not design-driving)
- **Maintenance Engineer** — consumes the dossier's recommended actions and SOP references to plan the job.
- **Shift Engineer** — first responder at 3am; needs the safety-critical subset of the dossier fast, on whatever screen is nearby.
- **Plant Operator** — raises the abnormality; needs the reporting step to take seconds, not minutes.
- **Safety Officer** — audits that SOPs and permits surfaced by the system are current and were followed.

Everyone else (planners, managers, executives) is roadmap.

---

## 5. Jobs To Be Done

**Primary JTBD:** *When an asset I'm responsible for behaves abnormally, assemble the complete, evidence-backed operational picture for me before I finish walking to my desk, so I can decide with confidence instead of reconstructing context for hours.*

Supporting JTBDs the same capability serves:
- *When I suspect a failure is not the first of its kind, show me every similar incident across sister assets regardless of how the technician worded it.*
- *When I act on a recommendation, let me verify every claim against its source in one click, so I can defend the decision to my plant manager and the safety auditor.*
- *When a senior engineer retires, ensure what they knew about our assets remains queryable by whoever inherits them.*

---

## 6. User Journey (MVP workflow — the only workflow)

1. **Trigger.** An Abnormality Event is raised on asset P-3401 ("high vibration, DE bearing side"). Source: simulated condition-monitoring feed (demo path) or 10-second manual quick-log by operator/engineer (product path). See OD-1.
2. **Notification.** Priya sees the event on the OCE event board: asset, symptom, criticality, timestamp.
3. **Dossier assembly.** She opens the event. The Context Dossier assembles *progressively on screen* — asset profile first (instant, deterministic), then failure history, then similar incidents, then manual/SOP extracts, then AI-reasoned probable causes and recommended actions (streamed). No query typed.
4. **Verification.** Each probable cause carries Evidence chips (WO-2019-0847, OEM manual p.112, SOP-RP-014 §3). Clicking a chip opens the source at the exact location. Deterministic Evidence Strength indicator per cause (see OD-2).
5. **Drill-down (the one place chat appears).** Priya asks follow-ups *in the context of the dossier* — "was the seal flush plan changed after the 2023 failure?" — answered from the already-assembled context with citations.
6. **Action.** She marks the dossier reviewed, exports the shareable incident report for the maintenance planner, and (roadmap) her disposition feeds back into ranking.

**Time-to-context target: under 2 minutes, versus a 2–4 hour manual baseline.**

---

## 7. Functional Requirements

Numbered for traceability. MoSCoW-prioritized. Everything "Should/Could" is sacrificable to protect "Must."

**FR-1 (Must) — Abnormality Event intake.** Accept events via (a) simulated event feed and (b) manual quick-log form: asset picker, symptom category, free-text note, criticality. ≤10 seconds to submit.
**FR-2 (Must) — Asset registry.** Assets with tag, name, class (manufacturer/model), location hierarchy (plant→unit→area), service duty, criticality, install date. Sister assets derivable by shared Asset Class and by shared service duty.
**FR-3 (Must) — Document ingestion.** Ingest OEM manuals (PDF, incl. scanned→OCR), SOPs, inspection reports. Parse, chunk with structural awareness (section headers, page numbers preserved), embed, and link every document to one or more assets or asset classes.
**FR-4 (Must) — Work-order ingestion with failure-mode normalization.** Ingest historical work orders (CSV/JSON). At ingestion time, map free-text failure descriptions to a curated Failure Mode taxonomy (ISO 14224-inspired, ~25 modes for MVP) via embedding similarity + threshold; below threshold → "unclassified" (never force-fit). This is what makes "seal weeping" and "mech seal gone" the same event.
**FR-5 (Must) — Context Dossier generation.** On event open, deterministically assemble Shared Context (asset profile, WO history, sister-asset incidents with matching failure modes, top-k manual/SOP chunks scoped to the asset class and symptom), then run the reasoning graph to produce: probable causes (ranked), recommended actions, safety notes. Progressive rendering; hard requirement that retrieval happens once.
**FR-6 (Must) — Evidence traceability.** Every generated claim carries ≥1 evidence link resolving to a work order or a document location (page/section). Claims the model cannot ground must be rendered as *"Hypothesis — no direct evidence in plant records"* and visually distinct. Zero unlabeled uncited claims is an acceptance criterion, not an aspiration.
**FR-7 (Must) — Evidence Strength indicator.** Deterministic per-cause score from: supporting-record count, recency, source-type diversity (WO + manual > WO alone), and sister-asset corroboration. Displayed as tiered badge (Strong/Moderate/Weak), never as a fake percentage. (OD-2.)
**FR-8 (Must) — Source viewer.** Click any evidence chip → open the source document at the cited page/section, or the full work order record.
**FR-9 (Should) — Contextual Q&A.** Chat scoped to the dossier's Shared Context, citations mandatory, refusal ("not in plant records") when context lacks the answer.
**FR-10 (Should) — Incident report generation.** One-click shareable report (on-screen; PDF export is a stretch) summarizing event, findings, evidence, and recommended actions.
**FR-11 (Should) — Event board.** List of open/closed Abnormality Events with status.
**FR-12 (Could) — Cross-asset pattern panel.** "This failure mode has occurred N times across the asset class in M months" surfaced proactively on the dossier — the demo's emotional peak; technically a deterministic query over normalized failure modes, which is exactly the point we want judges to absorb.
**FR-13 (Won't/MVP) — see §15 Out of Scope.**

---

## 8. Non-Functional Requirements

**NFR-1 Latency:** Deterministic dossier sections render <2s; full dossier including AI reasoning p95 <60s, with progressive streaming so perceived wait ≈ 0.
**NFR-2 Groundedness:** 100% of claims cited or explicitly labeled hypothesis (audited, §18).
**NFR-3 Explainability:** Any judge question "why did it say that?" answerable live by clicking through to source.
**NFR-4 Model portability:** All LLM calls via OpenRouter behind one internal interface; swapping models is config, not code.
**NFR-5 Determinism boundary:** Retrieval, filtering, joins, traversal, scoring = deterministic code. LLM = reasoning, synthesis, explanation only. Enforced at code-review checklist level.
**NFR-6 Reproducibility:** `docker compose up` + one seed script → fully populated demo environment. The demo must survive a fresh laptop.
**NFR-7 Demo resilience:** Seeded dataset local; no dependency on external systems except OpenRouter; pre-generated fallback dossier cached in case of API outage on stage.
**NFR-8 Security (MVP-scoped):** Single-tenant, no auth in MVP (roadmap: SSO/RBAC); no real plant data, synthetic only — zero data-sensitivity risk by construction.
**NFR-9 Accessibility/UX:** Dark-mode-first industrial UI, legible at arm's length, ShadCN-consistent components; operator-grade information hierarchy (safety notes always visually dominant).

---

## 9. Information Architecture

Primary navigation (MVP): **Event Board → Context Dossier → Source Viewer.** Secondary: Asset Registry (browse), Ingestion status (admin-ish, minimal). The dossier is the home of the product; everything else feeds it.

Dossier layout (single screen, sections in fixed order): Header (asset, event, criticality) → Safety Notes → Probable Causes w/ Evidence Strength → Recommended Actions → Failure History timeline → Similar Incidents (sister assets) → Manual & SOP extracts → Contextual chat drawer.

---

## 10. Domain Model & Ubiquitous Language

This glossary is canonical. It becomes `CONTEXT.md` when the repo is scaffolded. Challenge any drift.

- **Asset** — a physical, tagged piece of equipment (P-3401). The atomic unit the product understands.
- **Asset Class** — manufacturer + model family (e.g., "Sulzer APT-41 centrifugal pump"). Basis for sister-asset and manual scoping.
- **Sister Asset** — another Asset sharing the Asset Class or the same service duty.
- **Abnormality Event** — a reported deviation on an Asset (symptom, criticality, timestamp, source). The trigger of the MVP workflow. *Not* the same as a Failure (an event may resolve benignly).
- **Work Order** — historical maintenance record: asset, date, free-text description, actions, downtime hours. Ingested, never authored, in MVP.
- **Failure Mode** — curated taxonomy entry (e.g., "mechanical seal leakage"). Work orders are *normalized to* failure modes at ingestion.
- **Document** — OEM manual, SOP, or inspection report; owned by an Asset or Asset Class.
- **Chunk** — retrievable unit of a Document with preserved structural location (page/section).
- **Shared Context** — the deterministic, retrieved-once bundle (asset profile + histories + chunks) that all reasoning nodes read. Immutable during a dossier run.
- **Context Dossier** — the product's core artifact: the assembled operational picture for one Abnormality Event.
- **Probable Cause / Recommended Action** — LLM-reasoned outputs, each bound to Evidence.
- **Evidence** — a link from a claim to a Work Order or Chunk. First-class entity, not a footnote.
- **Evidence Strength** — deterministic tier (Strong/Moderate/Weak) computed from evidence count, recency, diversity, corroboration.
- **Hypothesis** — a generated claim with zero Evidence; must be labeled as such.

Relationships: Asset —belongs to→ Asset Class; Asset —has many→ Work Orders, Abnormality Events, Documents; Work Order —normalized to→ Failure Mode; Dossier —built from→ Shared Context —composed of→ Evidence sources; Cause/Action —cites→ Evidence.

---

## 11. Data Model (logical; physical design belongs to the TDD)

Single PostgreSQL instance with pgvector. Logical tables: `asset_classes`, `assets`, `failure_modes`, `work_orders` (with `failure_mode_id` nullable, `normalization_score`), `abnormality_events`, `documents`, `chunks` (text, embedding vector, page, section, `document_id`), `dossiers` (event_id, status, generated sections as structured JSON), `evidence_links` (dossier_claim_ref → work_order_id | chunk_id). Embeddings live only on `chunks` and on `failure_modes` (for normalization). No graph database in MVP: sister-asset and history traversal are SQL joins — deliberately (see §13 AI philosophy).

---

## 12. Dataset Strategy (first-class workstream — OD-3)

The demo is only as convincing as the data. We author **Meridian Specialty Chemicals**, a synthetic but domain-credible plant:

- ~30 assets across 2 units; hero asset class: one centrifugal pump model with 4 installed sisters (P-3401, P-3402, P-3105, P-2210).
- ~200 work orders over 6 synthetic years, written in deliberately inconsistent technician language, embedding a **planted pattern**: the same mechanical-seal failure mode on three sister pumps, described three different ways, with quantified downtime — the demo reveal (FR-12).
- 1–2 real public OEM pump manuals (or a faithfully structured synthetic manual), 3–4 SOPs, a handful of inspection reports.
- A domain-review pass: would a plant engineer read this and nod? (Domain Expert persona owns sign-off.)

Effort budget: this is one person's first half-day and it is not optional.

---

## 13. AI Capabilities & Philosophy

**Where AI is used (and why nothing simpler suffices):**
- Failure-mode normalization of free-text WOs (embedding similarity; regex/synonym lists demonstrably fail on technician language).
- Probable-cause reasoning and recommended actions (synthesis across heterogeneous evidence — genuinely a reasoning task).
- Summarization within dossier sections and contextual Q&A.

**Where AI is explicitly banned:** retrieval orchestration, asset/sister lookups, history queries, filtering, ranking arithmetic, Evidence Strength computation, pagination. All deterministic.

**The one-liner for judges:** *the intelligence is in the substrate; the LLM only reasons over evidence the system already assembled deterministically.* This is our differentiation from every RAG chatbot in the room, and FR-12 (a plain SQL query producing the "wow") is its proof.

---

## 14. LangGraph Workflow

Supervisor → [deterministic **Operational Context Engine service** populates Shared State — *not a node, not an agent; a service invoked before reasoning begins*] → **Analysis Node** (interprets symptom against history & manuals; drafts probable causes with candidate evidence) → **Recommendation Node** (actions + safety notes, grounded in SOPs) → **Evidence Validation Node** (verifies every claim maps to a real Shared Context item; strips or relabels as Hypothesis anything that doesn't; computes nothing — Evidence Strength is computed in deterministic code) → **Report Node** (structures the dossier JSON for the frontend). Retrieval occurs exactly once. Nodes never fetch. Max graph = these four reasoning nodes; any proposal to add a node must name the industrial reasoning responsibility it owns.

---

## 15. MVP Scope & Out of Scope

**In:** FR-1..FR-8 (Must), FR-9..FR-11 (Should, cut in that reverse order under time pressure), FR-12 (Could, but demo-critical — treat as protected Could).

**Out (roadmap, stated in demo as vision, not apologized for):** live CMMS/DCS/historian integration; predictive/ML anomaly detection (we *receive* events, we don't detect them — honest and defensible); P&ID computer-vision parsing (asset connectivity is hand-curated in MVP; P&ID-derived graph is H2); multi-plant/multi-tenant; auth/RBAC/SSO; mobile app; work-order *authoring*; feedback-learning loop; notifications/paging integrations; knowledge-graph database (SQL suffices at MVP scale — ADR-worthy decision, to be recorded when repo exists).

---

## 16. Success Metrics

**Product metrics (demoable):** time-to-context <2 min vs. narrated 2–4 hr baseline; citation coverage 100%; planted cross-asset pattern surfaced with quantified downtime (₹ figure on screen); contextual Q&A refusal behaves correctly on an unanswerable question (we will show this — a system that knows what it doesn't know is trust, and trust is the product).
**Hackathon metrics:** honest self-scores ≥ Innovation 22/25, Business 23/25, Tech 17/20, Scalability 12/15, UX 13/15 before we go on stage; every judge question about a claim answerable by clicking evidence.

---

## 17. Evaluation Plan

- **Golden set:** 15 curated questions/scenarios against the seeded dataset with expected evidence; run after every significant change.
- **Groundedness audit:** script that walks a generated dossier and asserts every claim has ≥1 resolvable evidence link or Hypothesis label.
- **Normalization audit:** confusion check of failure-mode mapping on the 200 WOs; unclassified rate reported, never hidden.
- **Latency:** measured on demo hardware, not dev machines.
- **Demo dry-runs:** ≥3 full rehearsals, one on a cold environment (NFR-6), one with OpenRouter deliberately disconnected (NFR-7 fallback path).

---

## 18. Demo Story (v0 — Demo Director owns iteration)

**Act 1 — The 3am problem (60s).** Narrate Priya's reality: vibration alarm, five systems, four hours, Ramesh retiring in 8 months. One slide of the fragmented mess. No product yet.
**Act 2 — The dossier (3 min).** Simulated event fires live on the Event Board. Open it. The dossier assembles progressively — visible, cinematic, no typing. Click an evidence chip → manual opens at page 112. Ask one contextual question, get a cited answer; ask one unanswerable question, get an honest refusal.
**Act 3 — The reveal (90s).** The pattern panel: *"Mechanical seal failure — 3 occurrences across sister pumps in 22 months — 41 hours cumulative downtime — described as 'seal weeping', 'leakage at gland', 'mech seal gone'."* Beat. *"No human ever read across these 200 work orders. The system did, because it understands assets, not documents."* Close: the platform vision (H2/H3) and the retiring-brain line — OCE is where Ramesh's 31 years stop walking out the door.

---

## 19. User Stories (traceability backlog seed)

1. As a Plant Operator, I want to log an abnormality on an asset in under 10 seconds, so that reporting friction never suppresses reporting. (FR-1)
2. As a Reliability Engineer, I want a dossier assembled automatically when I open an event, so that I never reconstruct context manually. (FR-5)
3. As a Reliability Engineer, I want every probable cause linked to work orders and manual pages, so that I can verify before I act. (FR-6, FR-8)
4. As a Reliability Engineer, I want incidents on sister assets surfaced even when technicians described them differently, so that repeat failures become visible. (FR-4, FR-12)
5. As a Reliability Engineer, I want ungrounded model claims explicitly labeled as hypotheses, so that I can calibrate my trust. (FR-6)
6. As a Reliability Engineer, I want an Evidence Strength tier per cause, so that I can prioritize investigation without decoding a fake percentage. (FR-7)
7. As a Shift Engineer, I want safety notes visually dominant at the top of the dossier, so that critical precautions are unmissable under pressure. (NFR-9)
8. As a Maintenance Engineer, I want a shareable incident report from the dossier, so that job planning starts from the same evidence. (FR-10)
9. As a Safety Officer, I want SOP references in dossiers to point at exact sections, so that compliance is auditable. (FR-6, FR-8)
10. As a Reliability Engineer, I want to ask follow-up questions scoped to the dossier and get cited answers or honest refusals, so that drill-down doesn't reopen the fragmentation problem. (FR-9)
11. As the demo team, I want the full environment reproducible with one command and a seed script, so that the demo survives any laptop. (NFR-6)
12. As the demo team, I want a cached fallback dossier, so that an API outage on stage does not kill the demo. (NFR-7)

(Backlog to be expanded and decomposed into tracker issues at the to-issues stage.)

---

## 20. Future Roadmap (told as vision, built never-in-MVP)

**H2 (0–6 mo):** CMMS (SAP PM / Maximo) and historian connectors; P&ID parsing → asset connectivity graph; feedback loop on dossier dispositions; RBAC/SSO; mobile shift-engineer view. **H3 (6–24 mo):** turnaround planning intelligence; onboarding copilot over the same substrate; fleet benchmarking across plants; the substrate exposed as an API — the "brain" other industrial software calls.

---

## 21. Open Decisions for Founder Sign-off

**OD-1 — Trigger source.** Recommendation: build both the simulated feed (demo path) and the 10-second quick-log (product credibility path); demo uses the feed. Cost of both is low; narrative value is high ("in production this event comes from your historian — today we simulate it, honestly").
**OD-2 — Kill the confidence score.** Your brief specifies a "Confidence Score." Recommendation: replace with deterministic Evidence Strength tiers. An LLM-emitted percentage is unfalsifiable theater and the first thing a technical judge will attack; a deterministic tier is defensible in one sentence.
**OD-3 — Dataset as workstream.** Recommendation: budget a half-day and a named owner for the Meridian dataset including the planted pattern. Without it, Act 3 doesn't exist.

Approve, amend, or veto these three, plus the assumptions in §0 — then this PRD freezes at v1.0 and we proceed to the Technical Design Document.