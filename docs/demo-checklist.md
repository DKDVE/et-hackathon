# Demo Checklist — M14 freeze (`demo-final-v2`)

Rehearsal script for the Operational Context Engine demo. Everything below
assumes `REASONING_ENABLED=true` and a valid `OPENROUTER_API_KEY` unless you are
explicitly testing the fallback path (P9/NFR-7).

**Plan B bookmark (final board state, M14):** http://localhost:5173/events/25

## Pre-demo timeline

### T−2h — `make demo-gate`

Run the night-before gate. **Functional checks must be green** (any red blocks the
demo). **Timing checks are yellow WARN** — exit code stays 0; follow the printed
action if you see a timing WARN.

```bash
make demo-gate
```

This runs, in order: default test suite → golden → verify-seed (restores ingest)
→ normalization audit → a fresh timed demo-event dossier (wall <60s, analysis
<30s; timing failures are WARN not red) → groundedness + prose-ID audit on that
dossier → fallback replay cache check.

### T−30m — stack warm + board dressed + plan B cache

```bash
make up
# Confirm backend log: "Embedding model … ready" (wait if cold)
python scripts/simulate_event.py --background   # 3 historical events, non-hero assets
```

**One live reasoning run on FINAL board state** (hero P-3401 event after
`simulate_event.py` without flags). Open the dossier in the browser (SSE stream
required — POST alone does not run reasoning). Confirm the fallback cache key is
written (`reasoning_fallback_cache` row with current `analysis-v4` prompt).
**Bookmark that dossier URL as plan B** — currently
http://localhost:5173/events/25 (regenerate each rehearsal).

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

First `make up` downloads ~3GB (PyTorch + BGE embedder baked into backend image);
allow **15–25 minutes** on a typical conference Wi‑Fi. If the network is hostile,
use the USB-stick path: on a warm machine run `make images-save`, copy
`docker-images.tar` (~1.5 GB) to USB, on the cold machine `make images-load`
(~2 min) then `make dataset && make up && make seed && make ingest` (skips image
rebuild; allow **~12–15 min** total after load).

Stack services **≥2 min before demo**; confirm embedder-ready log before firing
the simulator. Frontend installs its own `node_modules` inside the container on
first boot — no host `npm ci` required.

**Migrations:** backend runs `alembic upgrade head` on start (0001–0006 including
routine-guard disposition). No manual migration step.

**Nav surfaces:** confirm http://localhost:5173/ops (Runs, Evals, Guardrails) and
http://localhost:5173/memory (five tabs) load before Act 2 — both are deterministic
and survive provider outage.

**`.env` rule:** env changes require `docker compose up -d --force-recreate backend`
— **restart is NOT enough** (reload does not re-read env_file).

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

With stack healthy and v4 fallback cache present (regenerated at T−30m):

1. Set invalid `OPENROUTER_API_KEY` + `DEMO_FALLBACK=1` in `.env`
2. `docker compose up -d --force-recreate backend`
3. `python scripts/simulate_event.py` → open dossier in UI (SSE stream)
4. Confirm: deterministic sections live; full reasoning replay with cached badges;
   chat degrades quietly; **Report** view without summary still shows Executive
   facts block; `/ops` and `/memory` fully functional
5. Restore valid key, `DEMO_FALLBACK=0`, `docker compose up -d --force-recreate backend`
6. Re-open a dossier — confirm live reasoning (no cached badges) recovers

## Memory layer (M12 / M13)

- [ ] **Post-guard figures (M13, D-024):** after `make ingest`, expect **55 routine
      closures**, review queue **32** (genuinely ambiguous failure rows in the
      0.51–0.57 score band), failure-row unclassified rate **7.2%** (32/445).
      Accuracy rises to **96.6%** with **0** routine false positives. Re-run
      `make audit-norm` before demo if substrate changes.
- [ ] **Do not action Review Queue items on hero-class WOs during rehearsals.** The three
      planted seal-failure WOs (`WO-2024-0117`, `WO-2025-0289`, `WO-2026-0034`) must keep
      auto-only classification for the FR-12 pattern reveal. If reviewed accidentally,
      re-run `make seed` + `make ingest` — this wipes human columns (`human_verdict`,
      `human_failure_mode_id`, `human_reviewed_at`) along with re-normalizing auto columns,
      then regenerate the fallback cache at T−30m.
- [ ] Browse **Memory** → all five tabs (Overview, Assets, Documents, Taxonomy, Review Queue).
- [ ] **Coverage tier footnote** visible on Assets tab.

## Founder script

See `docs/DEMO-SCRIPT.md` (governance beat) and `docs/FIGURES-CARD.md` (stage numbers).

## Automated proof

```bash
make test        # default unit suite
make golden      # M4 golden + assembler/lexical (needs seed + ingest)
make demo-gate   # full M9 gate (includes verify-seed + timed LLM run)
make audit-ground DOSSIER_ID=<id>
make audit-prose DOSSIER_ID=<id>
make audit-norm
```

## Dry-run recording (human task)

- [ ] **Dry-run 3** recorded as the **backup video** (full Act 2→3 flow, including
      fallback narration if rehearsed). Store offline on demo laptop.

## Contingency table

| Symptom | Likely cause | Operator action |
|---------|--------------|-----------------|
| Dossier stuck on "Assembling…" | Embedder not warm | Check backend logs for `Embedding model … ready`; wait 1–2 min |
| AI sections empty, deterministic OK | `REASONING_ENABLED=false` or bad key | Check `.env`; `docker compose up -d --force-recreate backend` |
| AI sections empty during outage | `DEMO_FALLBACK=0` or no cache | Set `DEMO_FALLBACK=1`; ensure T−30m run cached SSE |
| Chat throws errors | OpenRouter down (expected) | Narrate: "chat has no cache"; show disabled state |
| Event board empty | Seed not run | `make seed && make ingest` |
| Frontend blank / module errors | Stale node_modules volume | `docker compose down` then remove frontend volume and `make up` |
| `make demo-gate` timing WARN | Cold embedder or slow provider | Follow printed WARN action; regenerate cache at T−30m; bookmark plan B dossier |
| `make demo-gate` red (functional) | Test/audit failure | Fix before demo; do not proceed |
| Fresh laptop build timeout | Network flake on pip/torch | Use `make images-load` from USB tarball |
| verify-seed fails | Dataset not rendered | `make dataset` then retry |
