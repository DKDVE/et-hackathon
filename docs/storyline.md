# The Operational Context Engine - Full MVP Storyline

*ET AI Hackathon 2.0 · AI for Industrial Knowledge Intelligence: Unified Asset & Operations Brain*

**Logline:** When industrial equipment misbehaves at 3am, the answer already exists - scattered across five systems and one retiring engineer's memory. We built the plant's operational memory: a system that assembles the complete, evidence-backed picture in 90 seconds, cites every claim to its source, admits what it doesn't know, and gets measurably smarter with use.

---

## Act 0 - The World: A Problem Hiding in Plain Sight

The numbers come from the hackathon's own problem statement. Professionals in asset-intensive industries spend **35% of their working hours** searching for information that already exists somewhere in the organisation (McKinsey, 2024). The average large Indian plant runs **7–12 disconnected document systems** - drawings in one place, work orders in another, procedures in a third (NASSCOM–EY). This fragmentation contributes to **18–22% of unplanned downtime** in Indian heavy industry (BIS Research). And the cliff: **25% of India's experienced industrial engineers retire within a decade**, taking undocumented operational knowledge with them. Once gone, it cannot be recovered.

Now make it a person. **Priya**, 32, is a Reliability Engineer at Meridian Specialty Chemicals. She owns the rotating equipment of one production unit - about 120 assets. Her senior colleague **Ramesh** has 31 years at this plant and retires in eight months. Priya is competent, skeptical of AI, and trusts nothing without a source. Her bar for any tool: *"Show me the work order number."*

At 3am, **Pump P-3401** - hot molten ester at 185 °C - starts dripping at its mechanical seal. To decide what to do, Priya needs five things: the pump's maintenance history, the OEM manual, the right isolation SOP, whether this happened on the sister pumps, and ideally Ramesh's memory. Those five things live in five different systems. Assembling them takes 2–4 hours. The decision is needed in minutes.

Here is the insight most AI products miss: **the pain is not missing information. It is unassembled context at the moment of decision.** Everyone has seen AI answer questions about documents. But asking a good question presupposes exactly the context Priya lacks. A chatbot cannot save her, because she doesn't yet know what to ask.

## Act 1 - The Inversion

The **Operational Context Engine (OCE)** does not wait to be asked. Every workflow begins with a canonical **Operational Event** - a seal leak logged by an operator in ten seconds, a simulated condition-monitoring signal, or (in production) a trigger from a historian or CMMS, all arriving through one source-agnostic contract. The moment the event exists, the system reconstructs the operational context around that **asset** - not around a query, not around documents. The chatbot is only one interface. The product is operational decision intelligence.

Underneath sit two layers with one sentence between them: **memory accumulates; context is reconstructed.** The *Operational Memory Layer* ingests and grows monotonically - manuals parsed and OCR'd, SOPs chunked to the clause, five hundred messy work orders normalized against a hierarchical failure-mode taxonomy. The *Operational Context Engine* is the runtime that carves out the event-relevant slice, deterministically, in about half a second.

## Act 2 - Ninety Seconds, Witnessed

The event lands on the board: *P-3401 · Seal Leak · Criticality A.* Priya opens it. No search box appears. Instead, the **Context Dossier** assembles before her eyes:

First, instantly and without any AI: the asset profile with its P&ID reference drawing, thirty work orders of failure history, eleven incidents on sister pumps - same model, same duty, found even though three technicians described the same failure in three different vocabularies - the OEM manual and SOP extracts already open to the relevant clauses, and the fleet's failure patterns, quantified in hours and rupees.

Then, streamed in as it reasons: **probable causes** - the headline: *chronic flush-line blockage has starved the seal of cooling, driving the current leak* - each cause carrying evidence chips and a deterministic **Evidence Strength tier** (Strong / Moderate / Weak, computed from evidence count, recency, source diversity, and sister-asset corroboration - never a model-emitted confidence percentage, anywhere). **Recommended actions** a planner can execute tonight: isolate per SOP-001 §2, restore the API Plan 11 flush, replace the cartridge per manual §5.3 - the system even checked the spare part is in stores. **Safety notes**, every one cited to an SOP or the manual; any safety note that fails validation is *deleted, never guessed*.

Priya clicks a chip. The OEM manual opens **at page 31, section 6 - Troubleshooting**, the exact row. Every claim in the product resolves like that, or it wears an explicit *Hypothesis* label. There is no third state.

She drills down in chat: *"What flush plan does the OEM specify?"* - a cited answer. Then, deliberately: *"What's the winding insulation class of motor M-1101?"* The system replies that this is **not in the plant records assembled for this event** - no speculation, no general knowledge. It refuses. A system that knows what it doesn't know is the only kind an engineer trusts at 3am; the refusal is a feature we demonstrate on purpose.

One more click produces the shareable incident report - executive facts, validated causes with their evidence appendix, actions, patterns - print-ready for the safety auditor.

**Time-to-context: ninety seconds, against a 2–4 hour manual baseline.**

## Act 3 - The Reveal: What It Found in 500 Messy Work Orders

The dossier's Pattern Panel holds the moment the demo is built around. Two patterns across the sister fleet, discovered, connected, and quantified:

**The acute:** three mechanical seal failures across three sister pumps in 22 months - 41.0 hours of downtime, ≈ ₹1.8 crore. Read the phrasings verbatim: *"seal weeping at gland" · "leakage at gland follower" · "mech seal gone."* Three technicians, three vocabularies, one failure mode. No keyword search connects these; taxonomy normalization at ingestion does.

**The chronic cause:** flush-line blockage on the same pump class - recorded **eighteen times over six years**, 99.1 hours, ≈ ₹4.5 crore. The plant's CMMS wrote this problem down eighteen times, and no human ever read across five hundred work orders to connect the chronic pattern to the acute failures it was causing. The system did - and cited the OEM manual page that explains the mechanism.

And the part we are proudest of as engineers: **this discovery is not a language model being clever. It is a database query** - a GROUP BY over a knowledge substrate that normalized messy technician language against a proper failure-mode taxonomy. The AI reasons over evidence. The intelligence is in the substrate.

## The Engineering Story - Boring on Purpose

The architecture is deliberately unexciting, and every boring choice is a written-down decision (27 of them, logged with alternatives and trade-offs in `DECISIONS.md`):

**One datastore.** Postgres + pgvector. At this scale, every "knowledge graph traversal" is a two-join SQL query; typed entities and typed relationships in a relational schema *is* a knowledge graph in the ways that matter. The revisit trigger (P&ID-derived topology) is written into the decision.

**Retrieval happens exactly once.** A deterministic assembler builds the Shared Context - profile, histories, sister incidents, manual/SOP chunks via hybrid semantic + exact-token retrieval - freezes it with a content hash, and enumerates the evidence pool. Reasoning nodes read that frozen context and can never fetch. This makes every dossier reproducible and every citation auditable by set membership.

**AI only where it reasons.** Three model calls (analysis on Sonnet; recommendation and validation on Haiku via a per-node model map) produce causes, actions, and a claim-by-claim support check. Everything else - retrieval, filtering, scoring, pattern statistics, Evidence Strength - is code with a correct answer. No LLM ever performs deterministic work, and no LLM-emitted number ever reaches the UI.

**Two-stage validation, then a deterministic report step.** Stage one is code: any citation ID that doesn't exist in the frozen evidence pool is stripped; claims left with nothing become labeled hypotheses. Stage two is a model judging whether the surviving citations actually support each claim. Then code assembles the dossier, deletes unsupported safety notes, attaches Strength tiers, and persists everything - sections, evidence links, and per-dossier guardrail statistics.

**It survives the loss of the network.** Embeddings run locally (bge-large, baked into the image); the dataset is seeded by one script; and every successful reasoning run is cached as a full replayable event sequence. Kill the API key on stage and the dossier replays - honestly badged *"cached"* - in under two seconds. The demo's disaster plan is a tested code path.

## The Story Inside the Story - A System That Debugged Itself

The best subplot happened by accident, and we kept the receipts.

Early calibration left a known blemish: thirteen routine PM work orders ("topped up oil, running fine") were being over-classified as failures. We logged it as a known issue with a reserved fix, and moved on. Weeks later we built the **Review Queue** - the Memory Layer page where the system surfaces work orders it's uncertain about for human judgment, every verdict stored *beside* the machine's answer with full provenance, never over it. The queue's very first human walk-through surfaced exactly those thirteen rows, ten-for-ten, and recommended exactly the reserved fix: a deterministic routine-closure guard at ingestion.

We pulled the lever under a full re-verification protocol. Classification accuracy rose from **93.7% to 96.6%** - measured by our own audit against ground-truth labels that are firewalled from the database, so the audit cannot cheat and neither can we. The review queue shrank from 87 noisy rows to 32 genuinely ambiguous ones. That arc - *known issue → measurement tool → the tool independently rediscovers the issue → the reserved fix ships → the improvement shows up as a curve on the product's own Evals tab* - is the learning loop, demonstrated rather than promised.

Which is also why the governance surfaces exist in the product, not on a slide: an **Ops panel** with per-node traces, token costs, and eval history; **guardrail counters** per dossier (citations stripped, hypotheses labeled, safety notes deleted); and the human-review provenance model. *The system learns - and shows its work.*

## The Dataset - A Miniature Digital Twin, Honestly Rigged

Meridian Specialty Chemicals is synthetic by design: two plants, four units, forty assets, five hundred work orders over six simulated years, a 41-page OEM manual, ten SOPs (one page deliberately scanned, to prove the OCR path live), inspection and incident reports, P&IDs, a spares catalogue. Data was designed first; every document is a deterministic rendering of the relational truth - no fact exists in a PDF that is absent from the design file.

The demo pattern is planted - and we say so, because the *honesty engineering* around it is the point: the ground-truth labels never enter the database (a test enforces that only the audit may read them); a red-herring misalignment failure on the fourth sister pump exists so the demo shows discrimination, not just aggregation; roughly a tenth of the work orders are written so that "unclassified" is the *correct* answer, giving the audit honest negatives; and a generation-time validator makes the dataset refuse to build if the demo spec ever drifts. Zero data-sensitivity risk, full reproducibility: one seed script, fresh laptop.

## The Numbers (as they appear on stage)

| Measure | Value |
|---|---|
| Time-to-context | **90 s** vs 2–4 hr manual baseline |
| Acute pattern | 3 seal failures · 3 sisters · 22 mo · 41.0 h · ≈ ₹1.8 Cr |
| Chronic pattern | 18 flush blockages · 71 mo · 99.1 h · ≈ ₹4.5 Cr |
| Impact assumption | ₹4.5 L per downtime hour (configured, footnoted) |
| Entity-extraction accuracy | **96.6%** (audited vs firewalled ground truth; 93.7% pre-guard) |
| Claim traceability | 100% cited or explicitly labeled Hypothesis - enforced, measured per dossier |
| Review queue | 32 genuinely ambiguous records (was 87 before the guard) |
| Full reasoning wall time | p95 < 60 s, streamed progressively; deterministic sections in < 2 s |
| Reproducibility | `git clone` → seed → demo, on a fresh laptop; network-loss fallback tested |

## Epilogue - The Vision

Today, one workflow executed completely: abnormality to evidence-backed decision. But what was actually built underneath is the **Operational Memory Layer** - and memory compounds. Every work order ingested makes it smarter; every future application reads the same memory: CMMS and SCADA adapters snapping into the canonical event contract, P&ID drawings becoming an asset-topology graph, compliance intelligence mapping regulations against the same records, Entra SSO and RBAC unlocking managed multi-plant operations.

And Ramesh's 31 years? They stop walking out the door.

*The system learns and shows its work.*

---

*Team DKDVE · ET AI Hackathon 2.0 · Operational Context Engine*

