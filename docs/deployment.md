# Hosted deployment (M15 / D-025)

The July 22 demo runs **local** (P9). This track is optional bonus: GitHub Actions
CI on `main` plus a Render-hosted instance behind an HTTP Basic gate.

## CI

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

- Backend: Postgres service (`pgvector/pgvector:pg16`), `alembic upgrade head`, ruff, mypy, pytest (`not slow and not destructive and not llm`). **No** `OPENROUTER_API_KEY` in CI.
- Frontend: `npm ci`, typecheck, lint, vitest, `npm run build`.
- Golden / ingest are **not** in CI (embedding model download — run `make golden` locally).

## Render blueprint

File: [`render.yaml`](../render.yaml) at repo root.

| Service | Type | Plan (indicative) |
|---------|------|-------------------|
| `oce-backend` | Docker web | Pro — 4 GB RAM ($85/mo) |
| `oce-frontend` | Static site | Included with web |
| `oce-db` | Managed Postgres | Basic 256 MB ($6–19/mo tier) |

**Estimated total:** ~$110–120/mo (backend Pro + small Postgres + static frontend). Scale down or delete after the hackathon.

Backend auto-deploys on `main` with **wait for CI** (`autoDeployTrigger: checksPass`).

### Secrets (Render dashboard — never commit)

| Secret | Purpose |
|--------|---------|
| `OPENROUTER_API_KEY` | LLM reasoning on hosted instance |
| `ACCESS_PASSWORD` | HTTP Basic gate (any username / this password) |

Set `FRONTEND_ORIGIN` / `VITE_API_URL` via blueprint service linking (see `render.yaml`).

### Access gate

When `ACCESS_PASSWORD` is set on the backend, all routes except `/health` require HTTP Basic auth. Unset locally → middleware inert. Put the password on the **closing slide**, not in the repo.

### One-off database seed (hosted)

After first deploy and healthy `/health`:

```bash
# Option A — Render one-off job / shell on oce-backend (4 GB plan; ingest may take ~5 min)
python /scripts/seed.py --phase structure
python /scripts/seed.py --phase ingest
```

If ingest OOMs on 4 GB, run ingest from a warm machine against the remote DB:

```bash
export DATABASE_URL='postgresql+psycopg://…'  # from Render DB dashboard (External URL)
cd backend && uv run python ../scripts/seed.py --phase ingest
```

Then smoke the hosted API:

```bash
python3 scripts/simulate_event.py --api-url "https://oce-backend.onrender.com"
# curl -u ":$ACCESS_PASSWORD" https://oce-backend.onrender.com/health
```

Run one live dossier with reasoning; confirm `reasoning_fallback_cache` row exists if you exercised fallback.

### Local prod-bundle smoke

Verifies nginx SPA + SSE + PDF viewer against the **built** frontend (dev compose untouched):

```bash
docker compose -f compose.prod.yaml up --build
# frontend http://localhost:8080  backend http://localhost:8000
```

Seed separately if the prod DB is empty (`docker compose -f compose.prod.yaml run --rm backend python /scripts/seed.py --phase structure`).

## Demo-path safety

Changes are additive or config-gated (`ACCESS_PASSWORD`, prod Docker targets, `compose.prod.yaml`). Default `docker compose up` / `make demo-gate` path is unchanged.

Compare against freeze tag:

```bash
git diff demo-final-v2..main -- docker-compose.yml Makefile scripts/demo_gate.sh frontend/docker-entrypoint.sh
```

Target: no modifications to demo-path files.
