# Demo Checklist — M9 (demo-candidate)

Rehearsal script for the Operational Context Engine demo. Everything below
assumes `REASONING_ENABLED=true` and a valid `OPENROUTER_API_KEY` unless you are
explicitly testing the fallback path (P9/NFR-7).

## Pre-demo timeline

### T−2h — `make demo-gate`

Run the night-before gate. Every line must be green; any red blocks the demo.

```bash
make demo-gate
```

This runs, in order: default test suite → golden → verify-seed (restores ingest)
→ groundedness + prose-ID audit on the latest complete dossier → normalization
audit → a fresh timed demo-event dossier (wall <60s, analysis <30s).

### T−30m — stack warm + board dressed

```bash
make up
# Confirm backend log: "Embedding model … ready" (wait if cold)
python scripts/simulate_event.py --background   # 3 historical events, non-hero assets
```

Stage browser tabs:

- Event board: http://localhost:5173/events (zoom ~110%, filters cleared)
- Dossier tab ready (do not open hero event yet)

### T−5m — dry fire on a throwaway event

```bash
python scripts/simulate_event.py --scenario m1101_thin
# Open dossier, confirm it assembles, then delete the event row or ignore it.
# Do NOT use the hero P-3401 seal-leak event for the dry fire.
```

Immediately before showtime:

```bash
python scripts/simulate_event.py    # THE demo event — must be newest + open + A
```

## Cold-start (fresh laptop, NFR-6)

Follow **only** `README.md`:

```bash
git clone <repo> && cd et-hackathon
cp .env.example .env   # add OPENROUTER_API_KEY
make dataset && make up && make seed && make ingest
```

Stack services **≥2 min before demo**; confirm embedder-ready log before firing
the simulator. Frontend installs its own `node_modules` inside the container on
first boot — no host `npm ci` required.

Health: http://localhost:8000/health → `{"status":"ok","db":"ok"}`.

## Act 2 — the trigger (D-007)

```bash
python scripts/simulate_event.py          # THE demo event: P-3401 / seal_leak
# or: python scripts/simulate_event.py --scenario p3402_overheating
# or: python scripts/simulate_event.py --list
```

Prints the created event id + board URL. The live demo event must remain
visually dominant: **open**, criticality **A**, **newest** on the board.

## Manual walkthrough (narrate each step, with timings)

- [ ] **Simulator fires** → prints `event <id>` and the board URL.
- [ ] **Event Board** shows the new event within the 5s auto-refresh, criticality
      badge (A = red) and `open` status chip. Background events show closed/reviewed.
- [ ] **Open the event** → DossierView. Deterministic sections render in **<2s**.
- [ ] **Header** shows asset P-3401, seal-leak symptom, criticality A.
- [ ] **Failure history** timeline renders (newest first).
- [ ] **Similar Incidents** shows sister WOs with `WO-…` chips.
- [ ] **Pattern Panel** shows **both** rows (D-018), downtime-sorted:
      `seal_flush_line_blockage — 18 occ / 99.1h` on top, and the planted
      `mechanical_seal_leakage — 3 occ / 22 mo / 41.0h` row.
- [ ] **Manual / SOP / Report** extract cards show `section_ref` + page + chip.
- [ ] **Click a `CH-…` chip** → SourceViewer opens the PDF at the cited page.
- [ ] **Click a `WO-…` chip** → WO record modal.
- [ ] **AI sections** stream in (safety → causes → actions). Under fallback:
      badge **"Cached reasoning replay"** on each AI block (`cached: true`).
- [ ] **Chat drawer** — ask a flush-plan question (cited answer) and one
      unanswerable question (honest refusal). On network-kill rehearsal: chat shows
      **"Reasoning service unavailable"** with input disabled (no cache for chat).
- [ ] **Thin asset** (`--scenario m1101_thin`) → honest empty state, no crash.
- [ ] **SSE**: DevTools → `context_ready` then reasoning events; kill stream →
      polling fallback on `GET /api/dossiers/{id}`.

## Network-kill rehearsal (P9 / NFR-7)

With stack healthy and v3 fallback cache present (key prefix `9bdda9…`):

1. Set invalid `OPENROUTER_API_KEY` + `DEMO_FALLBACK=1` in `.env`
2. `docker compose restart backend`
3. `python scripts/simulate_event.py` → open dossier in UI
4. Confirm: deterministic sections live; full reasoning replay with cached badges;
   chat degrades quietly
5. Restore valid key, `DEMO_FALLBACK=0`, restart backend → normal operation

## Automated proof

```bash
make test        # default unit suite
make golden      # M4 golden + assembler/lexical (needs seed + ingest)
make demo-gate   # full M9 gate (includes verify-seed + timed LLM run)
make audit-ground DOSSIER_ID=<id>
make audit-prose DOSSIER_ID=<id>
make audit-norm
```

## Contingency table

| Symptom | Likely cause | Operator action |
|---------|--------------|-----------------|
| Dossier stuck on "Assembling…" | Embedder not warm | Check backend logs for `Embedding model … ready`; wait 1–2 min |
| AI sections empty, deterministic OK | `REASONING_ENABLED=false` or bad key | Check `.env`; restart backend |
| AI sections empty during outage | `DEMO_FALLBACK=0` or no cache | Set `DEMO_FALLBACK=1`; ensure prior successful run cached SSE |
| Chat throws errors | OpenRouter down (expected) | Narrate: "chat has no cache"; show disabled state |
| Event board empty | Seed not run | `make seed && make ingest` |
| Frontend blank / module errors | Stale node_modules volume | `docker compose down` then remove frontend volume and `make up` |
| `make demo-gate` red on timing | Cold embedder or network | Re-run after warm-up; check OpenRouter status |
| verify-seed fails | Dataset not rendered | `make dataset` then retry |
