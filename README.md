# Operational Context Engine (OCE)

Demo-ready operational context dossier for industrial reliability events. One
`docker compose` stack: Postgres + FastAPI backend + Vite/React frontend.

## Prerequisites

- **Docker** and **Docker Compose** v2
- **Git**
- **uv** (Python 3.12+) — only for `make dataset` on the host
- **OpenRouter API key** — required when `REASONING_ENABLED=true` (demo default)

## Quickstart (fresh laptop)

```bash
git clone <repo-url> et-hackathon && cd et-hackathon
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY=sk-or-...
```

Render dataset artifacts, start the stack, seed the database:

```bash
make dataset    # render PDFs/CSVs from dataset/design/meridian.yaml (~1 min)
make up         # db + backend + frontend — first build downloads ~3GB; allow 15–25 min
make seed       # structure phase: wipe → load → verify
make ingest     # chunk, embed, normalize (~3–5 min; BGE model cached in image after first build)
```

Wait for the backend log line **`Embedding model … ready`** before firing events
(cold embedder load can take 1–2 minutes).

Health check: http://localhost:8000/health → `{"status":"ok","db":"ok"}`

### URLs

| Service   | URL |
|-----------|-----|
| Event board | http://localhost:5173/events |
| API docs    | http://localhost:8000/docs |
| Health      | http://localhost:8000/health |

### Demo trigger (Act 2)

```bash
# Board dressing — 3 historical events on non-hero assets (run once before demo)
python3 scripts/simulate_event.py --background

# THE demo event — P-3401 seal leak, criticality A, open, newest
python3 scripts/simulate_event.py
```

The simulator prints the event id and dossier URL. Open the dossier to watch
deterministic sections render instantly, then AI reasoning stream in.

### Environment variables (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENROUTER_API_KEY` | *(empty)* | LLM access via OpenRouter (P7) |
| `REASONING_ENABLED` | `false` | Gate the reasoning layer (P5) |
| `DEMO_FALLBACK` | `0` | Replay cached SSE on LLM failure (P9) |
| `VITE_API_URL` | `http://localhost:8000` | Frontend → backend |

## Verification

```bash
make test           # default unit suite
make golden         # golden fixtures + assembler (needs seed + ingest)
make verify-seed    # destructive DB check (run in isolation)
make demo-gate      # night-before gate: tests + audits + timed demo run
make images-save    # tarball backend+frontend+db images for USB-stick cold start
make images-load    # load tarball on cold machine (then dataset/seed/ingest only)
```

See `docs/demo-checklist.md` for the full rehearsal script.

## Project layout

```
backend/     FastAPI + LangGraph reasoning + ingestion
frontend/    Vite/React dossier UI
dataset/     Meridian design yaml + rendered artifacts
scripts/     seed.py, simulate_event.py, demo_gate.sh
```

Architecture: `ArchitecturePrinciples.md`, `TDD.md`, `PRD.md`.
