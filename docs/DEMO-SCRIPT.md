# Demo Script — Founder Narration (M14 freeze)

Act 2 opens the simulator; Act 3 walks the dossier. Numbers below are the
**governance beat** — cite from `docs/FIGURES-CARD.md` on stage.

## Governance beat (post-guard, D-024)

After the guard, normalization accuracy is **96.6%** (was **93.7%** pre-guard).
The review queue is **32** rows — genuinely ambiguous failure phrasing in the
**0.57–0.65** score band. **Zero** routine PM noise. **55** routine closures
are excluded before embedding.

```
Fleet guardrail totals:
  stage1_stripped_citations: 0
  stage2_unsupported_removed: 9
  hypothesis_claims: 1
  safety_notes_deleted: 0
  chat_citations_stripped: 0

Eval suites (latest gate):
  normalization: pass (96.6%)
  groundedness: pass
  prose_id: pass
  timing: warn (provider-dependent)
  golden: pass (manual `make evals` — not gate-persisted)

Review queue size: 32
Routine closures (guard): 55
Failure-row unclassified: 32 (7.2% of 445 failure records)
```

**Back-pocket Q&A:** *"After the guard, the review queue is 32 rows — all
genuinely ambiguous failure phrasing. Zero routine PM noise."*

## Pattern panel (FR-12)

Narrate both rows (downtime-sorted):

1. `seal_flush_line_blockage` — **18** occurrences / **99.1h** / ≈**₹4.5Cr**
2. `mechanical_seal_leakage` (planted) — **3** / **22mo** / **41.0h** / ≈**₹1.8Cr**

Downtime cost assumption: **₹4.5L/hr** (`DOWNTIME_COST_PER_HOUR_INR`).

## Fallback narration (P9)

If provider is slow: badge **"Cached reasoning replay"** on AI blocks.
Chat has no cache — shows **"Reasoning service unavailable"** with input disabled.
