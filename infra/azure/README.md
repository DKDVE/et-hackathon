# Azure deployment (M15A / D-026)

Hosted track for the OCE hackathon demo. **Local demo path is unchanged** —
`docker compose up`, `make demo-gate`, and `docker-compose.yml` are not touched by
this directory.

Cut-line (D-025/D-026): if Azure blocks for more than one cumulative day, stop and
report; the local demo is the primary path.

## Architecture

```
GitHub Actions (OIDC) ──push──► ACR ──pull──► Container App (oce-backend)
                                                    │
                                                    ▼
                                          PostgreSQL Flexible (pgvector)
                                                    ▲
Container Apps Job (oce-seed) ──manual──────────────┘

Static Web App (oce-frontend) ──VITE_API_URL──► ACA ingress (HTTPS)
```

| Component | Azure resource | Notes |
|-----------|----------------|-------|
| Backend API | Container App `oce-backend` | 2 vCPU / 4 GiB, `minReplicas=maxReplicas=1` (no scale-to-zero — 4.5 GB image cold start is minutes) |
| Database | PostgreSQL Flexible Server | Burstable B1ms, `azure.extensions=VECTOR`, DB `oce` |
| Registry | ACR Basic | Admin disabled; ACA pulls via user-assigned managed identity (`AcrPull`) |
| Seed | Container Apps Job `oce-seed` | Manual trigger; command override per phase |
| Frontend | Static Web App Free | `VITE_API_URL` baked at build time |

### Secrets (by NAME only — never commit values)

| Name | Where set | Purpose |
|------|-----------|---------|
| `DATABASE_URL` | ACA secret `database-url` | Postgres connection (`postgresql+psycopg://…`) |
| `OPENROUTER_API_KEY` | ACA secret `openrouter-api-key` | LLM reasoning |
| `ACCESS_PASSWORD` | ACA secret `access-password` | HTTP Basic gate (closing slide only) |
| `AZURE_PG_ADMIN_PASSWORD` | One-time `deploy.sh` input | Postgres admin (bootstrap only) |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | GitHub secret | SWA deploy action (only GitHub-stored secret) |

Enterprise upgrade path: move ACA secrets → **Azure Key Vault** references (out of scope this week).

## One-time bootstrap

```bash
# Human confirms subscription + region
az login
az account set --subscription "<subscription-id>"

export AZURE_ACR_NAME="ocehackathonacr"          # globally unique
export AZURE_PG_SERVER="oce-pg-hackathon"          # globally unique
export AZURE_PG_ADMIN_PASSWORD='…'                 # password manager
export AZURE_DEV_IP="$(curl -4 -s ifconfig.me)"
export OPENROUTER_API_KEY='…'
export ACCESS_PASSWORD='…'                           # rotated value — portal only after bootstrap

chmod +x infra/azure/deploy.sh
./infra/azure/deploy.sh
```

Defaults: resource group `rg-oce-hackathon`, region `centralindia`.

## Seed procedure

After backend `/health` is OK:

```bash
RG=rg-oce-hackathon

# Phase 1 — structure (wipe → load → verify)
az containerapp job start -g "$RG" -n oce-seed

# Phase 2 — ingest (chunk, embed, normalize)
az containerapp job update -g "$RG" -n oce-seed \
  --command "python" "/scripts/seed.py" "--phase" "ingest"
az containerapp job start -g "$RG" -n oce-seed
```

**Ingest OOM fallback** (torch + BGE in 4 GiB): add your dev IP to the Postgres
firewall, then run ingest from a warm machine:

```bash
export DATABASE_URL='postgresql+psycopg://…'   # from portal — never commit
cd backend && uv run python ../scripts/seed.py --phase ingest
```

## Static Web App (Free) — region caveat

SWA is **not** available in `centralindia`. Default create location is `centralus`
(`AZURE_SWA_LOCATION`). **Azure for Students** subscriptions may block SWA entirely
(region policy). Workarounds:

1. **GitHub Actions / Azure Pipelines** — build `frontend/dist` locally in CI and serve via a second Container App (add `oce-frontend` ACA) or use the API docs URL for smoke.
2. **Local UI against hosted API** — set `VITE_API_URL` to the ACA backend FQDN; CORS: set `FRONTEND_ORIGIN=http://localhost:5173` on the backend until SWA exists.
3. **Azure DevOps** — `infra/azure/azure-pipelines.yml` (Microsoft-hosted agents have Docker; bypasses blocked ACR Tasks).

## Image build — student subscription caveat

`az acr build` (ACR Tasks) returns `TasksOperationsNotAllowed` on some student
subscriptions. **Do not rely on cloud build in `deploy.sh`.** Instead:

1. **GitHub Actions** — `.github/workflows/deploy.yml` (`workflow_dispatch` or post-CI); OIDC vars: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
2. **Azure Pipelines** — `infra/azure/azure-pipelines.yml`; service connection `Azure-OCE-Hackathon`.
3. **Local Docker** — start Docker Desktop, then `./infra/azure/deploy.sh` (full build path).

Bootstrap infra without image: `SKIP_BUILD=1 SKIP_PG=1 ./infra/azure/deploy.sh` (ACA placeholder until CI pushes).


One-time setup (replace placeholders):

```bash
APP_NAME=github-oce-deploy
RG=rg-oce-hackathon
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"

# App registration + service principal
APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
az ad sp create --id "$APP_ID" -o none

# Federated credential for main-branch deploys
az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-main",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:DKDVE/et-hackathon:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'

# RBAC on resource group (ACR push + ACA update)
SP_OID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"
az role assignment create --assignee "$SP_OID" --role Contributor --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}"

# GitHub repo variables (Settings → Secrets and variables → Actions)
#   AZURE_CLIENT_ID     = $APP_ID
#   AZURE_TENANT_ID     = $(az account show --query tenantId -o tsv)
#   AZURE_SUBSCRIPTION_ID = $SUBSCRIPTION_ID
# GitHub secret (only secret):
#   AZURE_STATIC_WEB_APPS_API_TOKEN — from SWA portal → Manage deployment token
```

Workflow: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)

- Triggers after CI passes on `main` (`workflow_run`).
- Builds `backend/Dockerfile.prod` (~4.5 GB with CPU torch + BGE cache).
- Pushes to ACR as `:sha` and `:latest` with GHA layer cache.
- Updates ACA image; SWA deploys frontend with `VITE_API_URL` = ACA FQDN.

**First full image push:** expect 15–25 min on conference Wi‑Fi; subsequent deploys
are faster when torch layers are cached.

## SSE / ingress

Reasoning streams via `text/event-stream` from the backend directly (not through SWA).
ACA ingress uses `--transport auto` (HTTP/1.1 compatible). The access gate is pure-ASGI
(no `BaseHTTPMiddleware` buffering).

Verify incrementally during smoke:

```bash
# Events should arrive over several seconds, not one blob at connection close
curl -N -u ":$ACCESS_PASSWORD" "https://<aca-fqdn>/api/dossiers/<id>/reasoning/stream"
```

If buffering appears, confirm ingress `transport` is `auto` or `http` (not forcing
HTTP/2-only edge buffering) and that no reverse proxy sits in front of ACA.

## Smoke checklist

```bash
API="https://<aca-fqdn>"
# Gate: 401 without creds, 200 with
curl -s -o /dev/null -w "%{http_code}" "$API/api/config"          # expect 401
curl -s -u ":$ACCESS_PASSWORD" -o /dev/null -w "%{http_code}" "$API/health"  # 200

python3 scripts/simulate_event.py --api-url "$API"
# Dossier: live reasoning SSE, evidence PDF deep-link, chat cited answer + refusal
# /ops, /memory, rate limit, fallback cache row on hosted DB
```

## Teardown

```bash
az group delete --name rg-oce-hackathon --yes --no-wait
```

Also delete the GitHub federated app registration if retiring the track entirely.

## Cost estimate (hackathon month)

| Resource | SKU | ~USD/mo |
|----------|-----|---------|
| Container App `oce-backend` | 2 vCPU / 4 GiB, always on | ~$55–70 |
| PostgreSQL Flexible | Burstable B1ms + 32 GB | ~$15–25 |
| ACR Basic | <10 GB stored | ~$5 |
| Static Web App | Free | $0 |
| Egress / misc | low demo traffic | ~$5 |
| **Total** | | **~$80–105** |

Credits: student / startup subscriptions often cover this for the demo window.
Delete the resource group after judging to stop spend.

## Render superseded

Render services (`oce-backend`, `oce-frontend`, `oce-db`) are suspended. Blueprint
artifacts live under [`docs/deploy-alternatives/render/`](../docs/deploy-alternatives/render/).
Free Render Postgres expires ~2026-08-07.
