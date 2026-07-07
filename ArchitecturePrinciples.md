# ARCHITECTURE PRINCIPLES — Operational Context Engine

**Status: Ratified. These principles are the engineering constitution.**
Every implementation decision, every Cursor prompt, and every code review must comply. A violation requires either fixing the code or amending this document via a DECISIONS.md entry — never silent drift. When a principle and a deadline conflict, cut scope, not principles.

---

**P1 — Retrieval occurs exactly once per reasoning session.**
The OCE service assembles Shared Context deterministically before any LLM reasoning begins. No node, tool, or prompt may fetch data mid-reasoning. *(Guarantees reproducibility, auditable groundedness, bounded latency.)*

**P2 — AI never performs deterministic work.**
Filtering, joins, traversal, ranking arithmetic, scoring, pagination, and retrieval are code. LLMs do reasoning, synthesis, and explanation only. If a task has a correct answer computable by a function, a function computes it. *(The intelligence is in the substrate; the LLM reasons over it.)*

**P3 — Every generated claim is traceable to Evidence, or is labeled a Hypothesis.**
No third state exists. Evidence links resolve to a real work order or an exact document location. Uncited-and-unlabeled output is a defect, not a style issue. *(Trust is the product.)*

**P4 — Shared Context is immutable during a reasoning session.**
All nodes read the same frozen context. Nothing appends to it mid-run. *(Validation by set-membership; no node can launder unsourced facts into context.)*

**P5 — Operational Context is assembled before AI reasoning, never by it.**
The dossier's factual skeleton (asset profile, histories, incidents, chunks) exists and can render before the first token is generated. *(The product works — degraded but honest — even if the LLM doesn't.)*

**P6 — Every workflow begins with an Operational Event; the engine never knows the source.**
Manual report, simulator, future SCADA/SAP/CMMS — all produce the same canonical entity through the same intake contract. *(Source-agnostic core; integrations become adapters, not surgery.)*

**P7 — Business logic is independent of the LLM provider and model.**
All model calls pass through one internal client; model choice is per-node configuration. No module outside that client imports a model SDK. *(Swap models by config; survive outages by rerouting.)*

**P8 — Every score shown to a user is computable by hand.**
Evidence Strength and any future metric derive from a stated deterministic formula over enumerable inputs. No LLM-emitted numbers appear in the UI. *(Explainability over magic; defensible in one sentence.)*

**P9 — The demo must survive the loss of the network.**
All data is local and seeded by script; a cached dossier path exists for LLM-API failure. External dependencies at demo time: at most one (OpenRouter), and it is optional. *(A demo that can die on stage eventually will.)*

**P10 — Data is designed before documents are written.**
The relational truth (assets, events, work orders, relationships) exists first; every PDF, SOP, and report is a rendering of it. Documents never contain facts absent from the data model. *(The dataset is a miniature digital twin, not a folder of files.)*

**P11 — Memory accumulates; context is reconstructed.**
The Operational Memory Layer (ingestion + storage substrate) grows monotonically with organizational knowledge. The Operational Context Engine reconstructs the event-relevant slice at runtime. Neither absorbs the other's job. *(The platform vision, enforced as a module boundary.)*

**P12 — Every feature justifies itself against the MVP, every decision against this document.**
New scope answers: does it improve the demo, the evidence chain, or the decision quality — this weekend? Architectural choices that are hard to reverse, surprising, or trade-off-laden are recorded in DECISIONS.md, append-only. *(Protect the MVP; remember why.)*