# Figures Card — Stage Numbers (M14 freeze)

One page. Every number said on stage.

## Hero pattern (planted trio — P-3401)

| Metric | Value |
|--------|-------|
| Occurrences | **3** |
| Span | **22 months** |
| Cumulative downtime | **41.0 h** |
| Cost exposure (at ₹4.5L/hr) | **≈ ₹1.8 Cr** |

## Fleet pattern (sister seal-flush history)

| Metric | Value |
|--------|-------|
| Occurrences | **18** |
| Span | **71 months** |
| Cumulative downtime | **99.1 h** |
| Cost exposure (at ₹4.5L/hr) | **≈ ₹4.5 Cr** |

## Assumptions

- **Downtime cost:** ₹4.5L/hr (`DOWNTIME_COST_PER_HOUR_INR=450000` in `.env.example`)

## Memory / normalization (post-guard, D-024)

| Metric | Value |
|--------|-------|
| Normalization accuracy | **96.6%** (was **93.7%** pre-guard) |
| Review queue | **32** |
| Review queue score band (failure-unclassified rows) | **0.57–0.65** |
| Routine closures (guard) | **55** |
| Failure-row unclassified rate | **7.2%** (32/445) |

## Guardrail fleet totals (latest dossier)

| Counter | Value |
|---------|-------|
| stage1_stripped_citations | 0 |
| stage2_unsupported_removed | 9 |
| hypothesis_claims | 1 |
| safety_notes_deleted | 0 |
| chat_citations_stripped | 0 |

## Timing

| Metric | Value |
|--------|-------|
| T→analysis (demo-gate, M14) | **41.2s** (WARN band: expect **38–48s** on slow provider days; latest gate `attempts_used=1`) |
| Cold clone — first `make up` (no USB) | **15–25 min** (Wi‑Fi; ~3GB image pull) |
| Cold clone — USB `images-load` path | **~3–5 min** stack + **~1 min** dataset + **~4 min** seed + **~4 min** ingest |
| Embedder warm-up after `make up` | **1–2 min** |

## Eval suites (status line)

`normalization: pass · groundedness: pass · prose_id: pass · timing: warn · golden: pass (make evals only)`

Golden suite is **not gate-persisted** — `gate_persist.py` writes timing, normalization,
groundedness, and prose_id only; golden runs via `make evals` (~30s, embedding load).

## Plan B bookmark

After T−30m live run on final board state:

**http://localhost:5173/events/25** (regenerate each rehearsal; see `docs/demo-checklist.md`)

## Knowledge-graph linkage (live DB, post-ingest)

| Metric | Value |
|--------|-------|
| Assets with ≥1 linked document | **100%** (40/40) |
| Failure-row WOs normalized | **92.8%** (413/445) |
| Sister-relation coverage | **100%** (40/40 assets have ≥1 sister via class or duty) |

## Demo screenshots (M14)

| Artifact | Path |
|----------|------|
| Evals tab (93.7% → 96.6%) | `docs/screenshots/m14/ops-evals-accuracy.png` |
| Memory overview (55 routine / 32 queue) | `docs/screenshots/m14/memory-overview-post-guard.png` |
