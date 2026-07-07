# Demo Checklist — Checkpoint α (M5)

The deterministic product, before the first LLM token (P5). Everything below runs
with `REASONING_ENABLED=false` (the default).

## Cold-start (fresh laptop)

```bash
make up            # db + backend + frontend
make dataset       # render PDFs/CSVs from meridian.yaml (if not already rendered)
make seed          # structure phase: wipe -> load -> verify
make ingest        # chunk + embed + normalize (loads local embedding model)
make verify-seed   # optional: destructive DB verification, run in isolation
```

Health: open http://localhost:8000/health → `{"status":"ok","db":"ok"}`.

## Act 2 — the trigger (D-007)

```bash
python scripts/simulate_event.py          # THE demo event: P-3401 / seal_leak
# or: python scripts/simulate_event.py --scenario p3402_overheating
# or: python scripts/simulate_event.py --list
```

Prints the created event id + board URL.

## Manual walkthrough (narrate each step, with timings)

- [ ] **Simulator fires** → prints `event <id>` and the board URL.
- [ ] **Event Board** (http://localhost:5173/events) shows the new event within
      the 5s auto-refresh, with its criticality badge (A = red) and `open` status chip.
- [ ] **Open the event** → DossierView. The deterministic sections render in **< 2s**
      (assembler is ~349ms warm; the rest is network + paint).
- [ ] **Header** shows asset P-3401, the seal-leak symptom, criticality A.
- [ ] **Failure history** timeline renders (newest first).
- [ ] **Similar Incidents** shows sister WOs with `WO-…` chips.
- [ ] **Pattern Panel** shows **both** rows (D-018), downtime-sorted:
      `seal_flush_line_blockage — 18 occ / 99.1h` on top, and the planted
      `mechanical_seal_leakage — 3 occ / 22 mo / 41.0h` row, phrasings verbatim,
      asset tags shown.
- [ ] **Manual / SOP / Report** extract cards show `section_ref` + page + a chip.
- [ ] **Click a `CH-…` chip on a manual extract** → SourceViewer opens the PDF
      **at the cited page** (e.g. p31 "6 Troubleshooting"), section_ref shown.
- [ ] **Click a `CH-…` chip on an SOP extract** → PDF opens at the cited SOP page.
- [ ] **Click a `WO-…` chip** → WO record modal (asset, dates, description, actions).
- [ ] **AI-dependent sections** (Safety Notes, Probable Causes, Recommended Actions,
      chat) show a single collapsed **"Reasoning layer: not enabled"** row — never
      fake content, never a blank gap.
- [ ] **Thin asset** (e.g. simulate `--scenario m1101_thin`) → honest empty state
      ("No prior failures recorded for this asset"), no crash.
- [ ] **SSE**: DevTools → the stream yields `context_ready` then
      `degraded{reasoning_disabled}`. Kill the stream → the view falls back to
      polling `GET /api/dossiers/{id}` (TDD §12).

## Automated proof

```bash
make test        # default unit suite (excludes slow + destructive), any order
make golden      # M4 golden + assembler/lexical (needs seed + ingest)
docker compose exec -T backend pytest -m slow tests/test_e2e_deterministic.py
```
