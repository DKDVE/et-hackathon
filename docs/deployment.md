# Hosted deployment

**Current track:** Azure (M15A / D-026). See [`infra/azure/README.md`](../infra/azure/README.md).

**Superseded:** Render (M15 / D-025) — artifacts archived under
[`docs/deploy-alternatives/render/`](deploy-alternatives/render/).

## CI

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

- Backend: Postgres service (`pgvector/pgvector:pg16`), `alembic upgrade head`, ruff, mypy (`continue-on-error` — frozen substrate debt), pytest (`not slow and not destructive and not llm`). **No** `OPENROUTER_API_KEY` in CI.
- Frontend: `npm ci`, typecheck, lint, vitest, `npm run build`.
- Golden / ingest are **not** in CI (embedding model download — run `make golden` locally).

CD: [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) — runs after green CI on `main`.

## Demo-path safety

Changes are additive or config-gated (`ACCESS_PASSWORD`, prod Docker targets, `compose.prod.yaml`, `infra/azure/`). Default `docker compose up` / `make demo-gate` path is unchanged.

Compare against freeze tag:

```bash
git diff demo-final-v2..main -- docker-compose.yml Makefile scripts/demo_gate.sh frontend/docker-entrypoint.sh
```

Target: no modifications to demo-path files.

## Local prod-bundle smoke

Verifies nginx SPA + SSE + PDF viewer against the **built** frontend (dev compose untouched):

```bash
docker compose -f compose.prod.yaml up --build
# frontend http://localhost:8080  backend http://localhost:8000
```

Seed separately if the prod DB is empty (`docker compose -f compose.prod.yaml run --rm backend python /scripts/seed.py --phase structure`).
