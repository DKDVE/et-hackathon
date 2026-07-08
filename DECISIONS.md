# DECISIONS.md — Architecture & Product Decision Log

**Project:** Operational Context Engine (OCE) — ET AI Hackathon 2.0
**Convention:** Single living log (see D-000). Append-only; never rewrite history — supersede with a new entry referencing the old.
**Gate (do not log unless all three hold):** the decision is hard to reverse, would surprise a reader without context, and resolved a real trade-off between genuine alternatives. Routine choices don't belong here.
**Statuses:** Proposed → Accepted → Superseded by D-xxx.

---

## D-000 — Single-file decision log instead of per-ADR files

**Status:** Accepted
**Decision:** Maintain all ADRs in one `DECISIONS.md` at repo root, rather than `docs/adr/NNNN-*.md` per the workspace domain-modeling convention.
**Alternatives Considered:** One file per ADR in `docs/adr/` (workspace skill default); no ADR log at all.
**Rationale:** At hackathon scale (~15–25 decisions, 2–4 people, 48h), one file is scannable in a single read, trivially diffable, and easy to paste into Cursor context wholesale. Per-file ADRs earn their keep at team/repo scale we won't reach this weekend.
**Trade-offs:** Loses per-decision git history granularity; if the project graduates to a real product, the log should be split into `docs/adr/` files.
**Impact:** All contributors and all Cursor prompts reference this single file as decision context.

---

## D-001 — Product bet: asset-centric Operational Context Engine, not chat-first RAG

**Status:** Accepted
**Decision:** The core product is a Context Dossier automatically assembled around an asset when an Abnormality Event occurs. Chat exists only as a scoped drill-down inside a dossier.
**Alternatives Considered:** (a) Conversational RAG over plant documents; (b) enterprise semantic search; (c) multi-agent "AI team" showcase.
**Rationale:** The engineer's pain is context reconstruction at the moment of decision, not answering questions — asking a good question presupposes the context they lack. Chat-first also positions us identically to every other team in the room. Push-based, evidence-backed assembly is both the honest solution to the stated pain and the differentiation.
**Trade-offs:** Harder to build than a chatbot; the "no query" interaction must be explained in the demo or judges may miss what's novel; requires a trigger mechanism (see D-007).
**Impact:** UI is dossier-centric (Event Board → Dossier → Source Viewer); retrieval design is asset-scoped, not query-scoped; demo script is built around the assembly moment.

---

## D-002 — One persona, one workflow for MVP

**Status:** Accepted
**Decision:** Primary persona is the Reliability Engineer; the only MVP workflow is unexpected-abnormality response. All other personas/workflows are roadmap.
**Alternatives Considered:** Multi-persona platform demo; operator-first mobile flow; manager dashboard.
**Rationale:** A hackathon rewards one job done unforgettably over five done adequately. The reliability engineer owns the highest-stakes version of the pain and is the credibility bar ("would a plant engineer trust this?").
**Trade-offs:** Judges asking "what about operators/managers?" get a roadmap answer, not a demo; narrower surface area to impress on.
**Impact:** Every feature is evaluated against Priya's JTBD; secondary personas influence design details (safety-note prominence, quick-log speed) but never scope.

---

## D-003 — Evidence Strength tiers replace LLM Confidence Score

**Status:** Accepted (founder amendment incorporated)
**Decision:** Each probable cause displays a deterministic Evidence Strength tier (Strong/Moderate/Weak) computed from supporting-record count, recency, source-type diversity, and sister-asset corroboration. No LLM-emitted confidence percentages anywhere in the product. Internal components — evidence count, source diversity, recency, cross-asset corroboration — are computed and stored in the backend; UI shows tier only.
**Alternatives Considered:** (a) LLM self-reported confidence %; (b) logprob-derived scores; (c) no indicator at all.
**Rationale:** LLM confidence percentages are uncalibrated theater and the first target of a technical judge. Logprobs are unavailable/unstable across OpenRouter models and don't measure evidential support anyway. A deterministic tier is explainable in one sentence and reinforces the product thesis (intelligence in the substrate).
**Trade-offs:** Coarser than a percentage; tier thresholds are hand-tuned heuristics we must be able to state plainly if asked.
**Impact:** Evidence Strength computed in deterministic Python, not in any LangGraph node; components exposed via `GET /dossiers/{id}/evidence/{claim_ref}`; UI shows tier badges only; zero LLM-generated confidence values anywhere in UI; demo talk-track includes the one-sentence explanation.

---

## D-004 — PostgreSQL + pgvector only; no graph database in MVP

**Status:** Accepted
**Decision:** All storage — relational, vector, and relationship traversal (sister assets, asset↔document links, failure history) — lives in a single Postgres instance with pgvector. No Neo4j/graph DB.
**Alternatives Considered:** (a) Neo4j knowledge graph + separate vector store; (b) dedicated vector DB (Qdrant/Weaviate) + Postgres; (c) GraphRAG frameworks.
**Rationale:** At MVP scale (~30 assets, ~200 WOs, a few hundred chunks) every "graph" traversal is a two-join SQL query. A graph DB adds an ops surface, a query language, and a failure mode to the demo while adding zero capability the demo needs. Judges reward working depth, not architecture-diagram breadth. The relational schema *is* a knowledge graph in the ways that matter here: typed entities, typed relationships.
**Trade-offs:** Deep multi-hop connectivity queries (P&ID-derived topology, H2 roadmap) would eventually favor a graph store; we must present this as a deliberate scale-appropriate choice, not naïveté — this entry is the receipt.
**Impact:** One `docker compose` service for all data; sister-asset and history retrieval are plain SQL in the OCE service; roadmap slide names graph store as an H2 evolution triggered by P&ID topology, not before.

---

## D-005 — Retrieval-once Shared Context; LLM banned from retrieval and orchestration

**Status:** Accepted
**Decision:** A deterministic OCE service assembles the complete Shared Context (asset profile, histories, sister incidents, scoped chunks) exactly once per dossier. LangGraph reasoning nodes read this immutable context and never fetch, query, or call tools.
**Alternatives Considered:** (a) Agentic retrieval — nodes issue their own searches/tool calls as needed; (b) iterative retrieve-reason loops (e.g., self-RAG style).
**Rationale:** Agentic retrieval makes latency, cost, and output nondeterministic — fatal on a demo stage — and makes groundedness unauditable (you can't verify citations against a context you can't enumerate). Retrieval-once makes the groundedness audit (NFR-2) a simple set-membership check and makes dossier generation reproducible.
**Trade-offs:** If initial retrieval misses something, no node can recover it; mitigated by generous asset-scoped retrieval (recall over precision — the context window is not the constraint at this scale).
**Impact:** OCE is a plain Python service, not a graph node; Evidence Validation Node verifies claims by set-membership against Shared Context; contextual Q&A (FR-9) also answers only from the dossier's Shared Context.

---

## D-006 — Minimal 4-node LangGraph; nodes map to industrial reasoning responsibilities

**Status:** Accepted
**Decision:** The reasoning graph is Supervisor → Analysis → Recommendation → Evidence Validation → Report. A new node may be added only by naming the distinct industrial reasoning responsibility it owns.
**Alternatives Considered:** (a) Single mega-prompt, no graph; (b) larger multi-agent ensemble (planner, critic, researcher, etc.).
**Rationale:** Against (a): separating analysis, recommendation, and validation yields independently testable stages and lets validation act as an adversarial gate on the other two — structurally enforcing FR-6 rather than hoping a prompt behaves. Against (b): agent count is negatively correlated with demo reliability and adds no reasoning the four responsibilities don't cover.
**Trade-offs:** More LLM calls than a mega-prompt (latency/cost — mitigated by progressive streaming, NFR-1); the graph is intentionally boring, which we must frame as discipline, not lack of ambition.
**Impact:** Each node has its own prompt file, its own golden tests, and a single structured output schema; the Evidence Validation node is the enforcement point for the Hypothesis label.

---

## D-007 — Dual abnormality trigger: simulated event feed + 10-second manual quick-log

**Status:** Accepted (superseded in part by D-011)
**Decision:** MVP supports two event sources: a simulated condition-monitoring feed (drives the live demo) and a manual quick-log form (operator-credible product path). Production integration with historians/CMMS is narrated roadmap.
**Alternatives Considered:** (a) Manual-only; (b) simulated-feed-only; (c) building real anomaly detection on synthetic sensor data.
**Rationale:** Manual-only weakens the "system acts before you ask" wow. Feed-only invites "so who types the event in real life?" skepticism. Real anomaly detection is an entire second product and out of scope (PRD §15) — receiving events rather than detecting them is an honest, defensible boundary.
**Trade-offs:** Two intake paths is slightly more build; the simulation must be visibly labeled as simulated to keep the demo honest.
**Impact:** Event intake is one API endpoint with two clients (simulator script + form); demo script Act 2 opens with the feed firing live.

---

## D-008 — Failure-mode normalization at ingestion time against a curated taxonomy

**Status:** Accepted
**Decision:** Free-text work-order descriptions are mapped to a curated ~25-entry Failure Mode taxonomy (ISO 14224-inspired) at ingestion, via embedding similarity with a threshold; below threshold → `unclassified`, never force-fit. Query-time matching operates on normalized modes.
**Alternatives Considered:** (a) Query-time semantic matching of raw WO text; (b) regex/synonym dictionaries; (c) LLM classification of every WO at ingestion.
**Rationale:** Ingestion-time normalization makes the cross-asset pattern reveal (FR-12) a deterministic SQL GROUP BY — fast, explainable, and stable on stage. Query-time matching is slower, nondeterministic across runs, and unauditable. Regex fails on technician vocabulary drift (the exact problem). Full-LLM classification works but costs more and is harder to audit than embedding-vs-taxonomy similarity with a stated threshold; may be revisited for low-margin cases.
**Trade-offs:** Curating the taxonomy is manual domain work; threshold tuning risks both silent misclassification and a large unclassified bucket — mitigated by the normalization audit (PRD §17) and by surfacing the unclassified rate rather than hiding it.
**Impact:** `work_orders.failure_mode_id` + `normalization_score` columns; taxonomy is seed data with its own embeddings; FR-12 is a plain SQL query — and is cited in the demo as proof of the deterministic-substrate thesis.

---

## D-009 — OpenRouter as sole LLM gateway behind one internal interface

**Status:** Accepted
**Decision:** All model calls go through a single internal `LLMClient` wrapping OpenRouter. Model choice per node is configuration. No business logic imports any model SDK directly.
**Alternatives Considered:** Direct per-provider SDKs; LiteLLM or similar self-hosted gateway.
**Rationale:** Model quality/pricing shifts weekly; the abstraction lets us swap models per node (cheap model for summarization, strong model for analysis) without code change, and lets a rate-limit or outage be rerouted mid-hackathon.
**Trade-offs:** OpenRouter itself is a single external dependency and point of failure on stage — mitigated by the cached fallback dossier (NFR-7).
**Impact:** One client module with retry/timeout policy; model IDs live in config; the demo-fallback path is part of the client, not an afterthought.

---

## D-010 — Synthetic "Meridian Specialty Chemicals" dataset with a planted cross-asset pattern

**Status:** Accepted (founder expansion incorporated; execution constrained by D-013)
**Decision:** Author a synthetic but domain-credible plant dataset (~30 assets, ~200 messy work orders over 6 synthetic years, real/faithful OEM manual, SOPs) with a deliberately planted repeat seal-failure pattern across sister pumps, quantified in downtime hours and ₹. A named owner spends the first half-day on it.
**Alternatives Considered:** (a) Public maintenance datasets (NASA bearing sets etc. — sensor-centric, no documents/WOs, wrong shape); (b) organizer-provided data (unconfirmed, can't be relied on); (c) thin ad-hoc data made during development.
**Rationale:** The demo's Act 3 reveal exists only if the pattern exists in data credible enough that a domain judge nods. Data authored as an afterthought reads as fake and kills trust — the product's entire currency.
**Trade-offs:** Half a day of scarce build time on data, not code; synthetic data must be disclosed as synthetic (we will — it's a strength: zero data-sensitivity risk).
**Impact:** Seed script is a first-class deliverable (NFR-6); demo numbers (3 incidents / 22 months / 41 hrs / ₹ figure) are authored into the data and rehearsed; domain-credibility review is a checklist item before freeze.

---

## D-011 — Operational Event as canonical, source-agnostic intake entity

**Status:** Accepted
**Decision:** Every workflow begins with an `Operational Event` (asset, source, symptom, criticality, timestamp). Source is an enum (`manual`, `simulated`, `integration`); the OCE never branches on it. Intake is one API contract; all producers — quick-log UI, simulator, future SCADA/SAP/CMMS — are adapters.
**Alternatives Considered:** Separate intake paths per source (original D-007 shape); source-specific event schemas.
**Rationale:** Founder direction. Decouples the engine from event provenance, making future integrations adapters rather than surgery, and strengthens the enterprise narrative ("your historian plugs in here") with near-zero MVP cost.
**Trade-offs:** The enum will eventually need richer source metadata (integration payloads); acceptable — extend with a nullable `source_metadata JSONB` when H2 arrives.
**Impact:** Table renamed `operational_events`; PRD term "Abnormality Event" is superseded in the glossary by "Operational Event"; Architecture Principle P6 encodes this permanently.

---

## D-012 — Operational Memory Layer / Operational Context Engine split

**Status:** Accepted
**Decision:** The system is conceptually two layers: the **Operational Memory Layer** (ingestion + storage substrate; accumulates organizational engineering knowledge monotonically) and the **Operational Context Engine** (runtime; reconstructs the event-relevant slice of memory). Enforced as a module boundary: `backend/app/memory/` vs `backend/app/context/`.
**Alternatives Considered:** Single undifferentiated "OCE" naming for everything (previous state).
**Rationale:** Founder direction. Sharpens both the enterprise vision (memory compounds — the moat) and the narrative, and gives the codebase a boundary that prevents retrieval logic from leaking into reasoning or vice versa. Zero change to MVP scope or behavior.
**Trade-offs:** Two names to keep straight in demo and docs; mitigated by one talk-track line: "memory accumulates, context is reconstructed."
**Impact:** Repo structure, Architecture Principle P11, demo narrative Act 3 close, and the roadmap framing (H3 = other applications reading the same memory).

---

## D-013 — Tiered dataset fidelity within the full Meridian relational design

**Status:** Accepted (founder veto window open)
**Decision:** The full Meridian relational design (2 plants, 4 units, ~40 assets, ~500 WOs, incidents, docs metadata, PM schedule, spares) is authored completely in `dataset/design/meridian.yaml` — but rendered document depth is tiered: **Tier 1** (hero pump class): full OEM manual, SOPs, inspection + incident reports; **Tier 2/3** (everything else): registry-complete, document-thin. P&IDs reduced from 5 to 2 static reference images. All documents are generated from the design file (P10), never hand-written.
**Alternatives Considered:** (a) Full-fidelity documents for all 40 assets and 10 manuals (founder's original expansion, ~2 days of authoring); (b) hero-asset-only dataset (original D-010, weaker digital-twin feel).
**Rationale:** The demo camera only ever points at the hero class; breadth must exist (the registry, the pattern, the plant hierarchy make it feel like an organization) but depth off-camera is unrecoverable time inside a 48-hour window. Design-first generation means Tier 2/3 can be deepened post-hackathon by running generators, not by re-authoring.
**Trade-offs:** A judge free-browsing a Tier 3 asset finds thin documents; mitigated by honest framing ("seeded subset of the memory layer") and by the registry being complete.
**Impact:** Dataset workstream fits in ~half a day + generator scripting; TDD §11; demo browsing paths steered to Tier 1 assets.

---

## D-015 — Hybrid-lite retrieval: deterministic lexical channel unioned with vector top-k

**Status:** Accepted
**Decision:** M4's assembler retrieves chunks via (a) pgvector cosine top-k on the enriched event query and (b) a deterministic lexical channel — chunks containing exact identifiers/tokens from the event text (asset tags, SOP/part codes, quoted phrases like "flush plan Y") via Postgres ILIKE/full-text — unioned and deduplicated, each chunk tagged with its retrieval channel.
**Alternatives Considered:** Pure semantic (misses exact-identifier matches endemic to industrial text); full BM25 + reciprocal-rank fusion (tuning surface and complexity unjustified at dozens-of-chunks-per-asset scale); LLM query rewriting (violates P1/P2).
**Rationale:** Exact-token recall is the one systematic weakness of embedding retrieval in this domain; a union at our corpus size costs ~30 lines and stays fully explainable ("this chunk is here because it contains 'flush plan Y'").
**Trade-offs:** Slightly larger Shared Context (acceptable — D-005: recall over precision); naive ILIKE would degrade at production corpus scale — H2 revisits with proper full-text indexing.
**Impact:** Assembler design (M4); evidence chips can display retrieval provenance; demo Q&A answer for "what about keyword search?"

---

## D-016 — In-database reasoning-run tracing instead of an external observability stack

**Status:** Accepted
**Decision:** Every reasoning node execution writes a `reasoning_runs` record (dossier_id, node, model, prompt_version, latency_ms, token counts, output digest, status) — new table via migration 0002 in M6. Structured JSON logging with dossier_id correlation across backend. No LangSmith/OTel/external tracing in MVP.
**Alternatives Considered:** LangSmith (external network dependency — violates P9 posture at demo time — plus setup cost); OpenTelemetry stack (collector + backend = two more services against D-004's spirit); print-logging only (no queryable trace for Q&A).
**Rationale:** A judge asking "what did the model actually do?" gets a live, queryable, per-dossier trace from our own database — observability as demo material. Zero new services, zero network.
**Trade-offs:** Not distributed tracing; no fancy UI (SQL/endpoint is enough this weekend). H2: export to a real stack.
**Impact:** Migration 0002 (M6); LLMClient records usage; timing middleware (M5) shares the correlation-ID scheme; the "harness" story in Q&A.

---

## D-017 — Hierarchical failure-mode families; margin rule applies cross-family only
**Status:** Accepted (family mapping itself pending human ratification from M3.2 report)
**Decision:** Failure modes carry a `family` attribute (yaml + DB column, migration 0002). Normalization assigns the top mode when it clears the score threshold AND either clears the margin OR the runner-up belongs to the same family. Margin becomes exclusively a cross-family confusion guard.
**Alternatives Considered:** (a) Further per-mode description tuning — demonstrated brittle (one tweak flipped the pattern query 3→1); leaves demo-critical rows on knife edges. (b) Lowering the margin globally — weakens the guard exactly where it's valuable (unrelated-mode confusion). (c) Editing planted WO texts — legitimate authorship lever, held in reserve; doesn't fix the 40+ non-planted stranded rows.
**Rationale:** Adjacent modes are a property of any honest industrial taxonomy (ISO 14224 is hierarchical); near-ties within a family are expected, not suspicious. The fix encodes domain structure instead of tuning around its absence — explainable in one Q&A sentence: "margins guard against cross-family confusion; within a family, best match wins."
**Trade-offs:** Within-family mis-assignment is no longer margin-blocked — guarded instead by the ≥0.90 accuracy gate and a new cross-family-error ≤2 gate, with error-split reporting in the audit. Family assignment is a curation judgment (human-ratified).
**Impact:** Migration 0002 (family column; reasoning_runs shifts to 0003); normalizer rule change + tests; audit reporting; taxonomy yaml; demo Q&A talk-track. Pattern-panel scoping (FR-12) still groups by mode, not family — families exist for normalization robustness, not display.

---

*Next entries will be appended as ready-to-paste blocks in chat whenever a qualifying decision is made — including during TDD, schema design, and any mid-build pivots. Superseding is allowed; deleting is not.*

---

## D-023 — Human-override provenance on work-order classification

**Status:** Accepted
**Decision:** Human review of normalization writes **only** `human_failure_mode_id`, `human_verdict`, and `human_reviewed_at`. Auto columns (`failure_mode_id`, `normalization_score`) are written exclusively by the ingester and never mutated by review, APIs, or UI. Effective mode for downstream queries is `human_failure_mode_id` when `human_verdict IN (confirmed, corrected)`; `unclassifiable` forces NULL regardless of auto. No re-review/undo endpoint pre-auth — irreversibility without identity is safer than mutable-without-auth.
**Alternatives Considered:** (a) Overwrite auto columns on review (loses audit trail); (b) Re-review/undo without auth (mutable anonymous state); (c) Full taxonomy editing in Memory UI (post-auth scope).
**Rationale:** Normalization accuracy math and the planted pattern substrate must remain byte-stable under human judgment. Separating auto vs human columns makes provenance auditable in one SQL diff. The review queue is the product's first mutation — provenance rules are constitutional.
**Trade-offs:** Accidental review on demo WOs requires `make seed` + `make ingest` to reset; no bulk actions or threshold tuning in MVP.
**Impact:** Migration 0005; `effective_failure_mode()` helper; Memory layer UI; normalization audit gains human-override summary line while accuracy stays on auto columns only.

---

## D-024 — Routine-closure guard: deterministic pre-embedding disposition

**Status:** Accepted
**Decision:** Before embedding similarity, apply a curated regex pattern list (~10–15 high-precision patterns from M12 band readout) to work-order descriptions. Match → `disposition=routine`, `failure_mode_id=NULL`, `normalization_score=NULL`. Failure-history, sister-incident, pattern-stat queries, and the review queue exclude `routine` rows. Audit gates guard false positives (routine ∧ true=real mode) ≤ 1 absolute.
**Alternatives Considered:** (a) LLM classification of routineness at ingestion (rejected — unauditable, violates P2); (b) Lowering norm threshold to absorb routine noise (rejected — one variable, D-017); (c) Human-only review-queue pruning (insufficient — 13 FPs were polluting accuracy).
**Rationale:** M12 showed 13 designed-routine rows misclassified as real modes (lubrication_degradation / impeller_damage) while sitting in the low-margin review band. A conservative deterministic guard removes them from the failure substrate without touching threshold/margin tuning. Conservatism is explicit: missed routine = queue noise; false routine on real failure = data loss (hard-gated).
**Trade-offs:** Pattern list requires human ratification like family mapping; recall over designed-routine rows is informational only. Unclassified-rate band is computed on failure-disposition rows only post-guard.
**Impact:** Migration 0006; `routine_closure_patterns.yaml`; `wo_normalizer.py` pre-pass; repository exclusions; normalization audit guard section; Memory overview split counts.

---