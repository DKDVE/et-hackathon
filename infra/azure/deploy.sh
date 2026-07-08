#!/usr/bin/env bash
# Idempotent Azure bootstrap for OCE hosted demo (M15A / D-026).
# Config/infra only — local compose path untouched.
#
# Required env (secrets by NAME — never commit values):
#   AZURE_RESOURCE_GROUP   default: rg-oce-hackathon
#   AZURE_LOCATION         default: centralindia
#   AZURE_ACR_NAME         globally unique, e.g. ocehackathonacr
#   AZURE_PG_SERVER        globally unique, e.g. oce-pg-hackathon
#   AZURE_PG_ADMIN_USER    default: oceadmin
#   AZURE_PG_ADMIN_PASSWORD
#   AZURE_DEV_IP           your public /32 for PG firewall (curl -4 ifconfig.me)
#   DATABASE_URL           postgresql+psycopg://… (built if PG_* set; else required)
#   OPENROUTER_API_KEY
#   ACCESS_PASSWORD
#   FRONTEND_ORIGIN        SWA URL after SWA create (https://….azurestaticapps.net)
#
# Optional:
#   AZURE_CA_ENV           default: oce-env
#   AZURE_BACKEND_APP      default: oce-backend
#   AZURE_SEED_JOB         default: oce-seed
#   AZURE_IDENTITY_NAME    default: oce-aca-identity
#   IMAGE_TAG              default: latest
#   SKIP_PG=1              skip Postgres (reuse existing DATABASE_URL)
#   SKIP_SWA=1             skip Static Web App (deploy via GitHub Actions only)

set -euo pipefail

: "${AZURE_RESOURCE_GROUP:=rg-oce-hackathon}"
: "${AZURE_LOCATION:=centralindia}"
: "${AZURE_ACR_NAME:?AZURE_ACR_NAME required}"
: "${AZURE_PG_SERVER:=oce-pg-hackathon}"
: "${AZURE_PG_ADMIN_USER:=oceadmin}"
: "${AZURE_PG_ADMIN_PASSWORD:?AZURE_PG_ADMIN_PASSWORD required unless SKIP_PG=1}"
: "${AZURE_DEV_IP:?AZURE_DEV_IP required unless SKIP_PG=1}"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY required}"
: "${ACCESS_PASSWORD:?ACCESS_PASSWORD required}"
: "${AZURE_CA_ENV:=oce-env}"
: "${AZURE_BACKEND_APP:=oce-backend}"
: "${AZURE_SEED_JOB:=oce-seed}"
: "${AZURE_IDENTITY_NAME:=oce-aca-identity}"
: "${IMAGE_TAG:=latest}"
: "${SKIP_PG:=0}"
: "${SKIP_SWA:=0}"

log() { printf '==> %s\n' "$*"; }
need() { command -v "$1" >/dev/null || { echo "missing: $1" >&2; exit 1; }; }

need az
need docker

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
ACR_LOGIN_SERVER="${AZURE_ACR_NAME}.azurecr.io"
IMAGE="${ACR_LOGIN_SERVER}/oce-backend:${IMAGE_TAG}"

log "subscription ${SUBSCRIPTION_ID}"
az group create --name "${AZURE_RESOURCE_GROUP}" --location "${AZURE_LOCATION}" -o none

log "ACR ${AZURE_ACR_NAME} (admin disabled)"
if ! az acr show --name "${AZURE_ACR_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" &>/dev/null; then
  az acr create \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_ACR_NAME}" \
    --sku Basic \
    --admin-enabled false \
    -o none
fi

if [[ "${SKIP_PG}" != "1" ]]; then
  log "PostgreSQL Flexible Server ${AZURE_PG_SERVER}"
  if ! az postgres flexible-server show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AZURE_PG_SERVER}" &>/dev/null; then
    az postgres flexible-server create \
      --resource-group "${AZURE_RESOURCE_GROUP}" \
      --name "${AZURE_PG_SERVER}" \
      --location "${AZURE_LOCATION}" \
      --admin-user "${AZURE_PG_ADMIN_USER}" \
      --admin-password "${AZURE_PG_ADMIN_PASSWORD}" \
      --sku-name Standard_B1ms \
      --tier Burstable \
      --storage-size 32 \
      --version 16 \
      --public-access 0.0.0.0 \
      -o none
  fi

  log "pgvector extension + firewall"
  az postgres flexible-server parameter set \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --server-name "${AZURE_PG_SERVER}" \
    --name azure.extensions \
    --value VECTOR \
    -o none

  az postgres flexible-server firewall-rule create \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_PG_SERVER}" \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0 \
    -o none 2>/dev/null || true

  az postgres flexible-server firewall-rule create \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_PG_SERVER}" \
    --rule-name AllowDevIP \
    --start-ip-address "${AZURE_DEV_IP}" \
    --end-ip-address "${AZURE_DEV_IP}" \
    -o none 2>/dev/null || true

  if ! az postgres flexible-server db show \
      --resource-group "${AZURE_RESOURCE_GROUP}" \
      --server-name "${AZURE_PG_SERVER}" \
      --database-name oce &>/dev/null; then
    az postgres flexible-server db create \
      --resource-group "${AZURE_RESOURCE_GROUP}" \
      --server-name "${AZURE_PG_SERVER}" \
      --database-name oce \
      -o none
  fi

  PG_HOST="${AZURE_PG_SERVER}.postgres.database.azure.com"
  DATABASE_URL="postgresql+psycopg://${AZURE_PG_ADMIN_USER}:${AZURE_PG_ADMIN_PASSWORD}@${PG_HOST}:5432/oce?sslmode=require"
fi

: "${DATABASE_URL:?DATABASE_URL required}"

log "user-assigned identity ${AZURE_IDENTITY_NAME}"
IDENTITY_ID="$(az identity show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AZURE_IDENTITY_NAME}" --query id -o tsv 2>/dev/null || true)"
if [[ -z "${IDENTITY_ID}" ]]; then
  az identity create --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AZURE_IDENTITY_NAME}" -o none
  IDENTITY_ID="$(az identity show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AZURE_IDENTITY_NAME}" --query id -o tsv)"
fi
IDENTITY_PRINCIPAL="$(az identity show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AZURE_IDENTITY_NAME}" --query principalId -o tsv)"
ACR_ID="$(az acr show --name "${AZURE_ACR_NAME}" --resource-group "${AZURE_RESOURCE_GROUP}" --query id -o tsv)"
az role assignment create --assignee "${IDENTITY_PRINCIPAL}" --role AcrPull --scope "${ACR_ID}" -o none 2>/dev/null || true

log "build + push ${IMAGE} (expect ~4.5 GB; layer cache helps on reruns)"
az acr login --name "${AZURE_ACR_NAME}"
docker build -f backend/Dockerfile.prod -t "${IMAGE}" .
docker push "${IMAGE}"

log "Container Apps environment ${AZURE_CA_ENV}"
if ! az containerapp env show --name "${AZURE_CA_ENV}" --resource-group "${AZURE_RESOURCE_GROUP}" &>/dev/null; then
  az containerapp env create \
    --name "${AZURE_CA_ENV}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --location "${AZURE_LOCATION}" \
    -o none
fi
ENV_ID="$(az containerapp env show --name "${AZURE_CA_ENV}" --resource-group "${AZURE_RESOURCE_GROUP}" --query id -o tsv)"

: "${FRONTEND_ORIGIN:=https://placeholder.azurestaticapps.net}"

log "Container App ${AZURE_BACKEND_APP} (2 vCPU / 4 GiB, min=max=1)"
if az containerapp show --name "${AZURE_BACKEND_APP}" --resource-group "${AZURE_RESOURCE_GROUP}" &>/dev/null; then
  az containerapp secret set \
    --name "${AZURE_BACKEND_APP}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --secrets \
      database-url="${DATABASE_URL}" \
      openrouter-api-key="${OPENROUTER_API_KEY}" \
      access-password="${ACCESS_PASSWORD}" \
    -o none
  az containerapp update \
    --name "${AZURE_BACKEND_APP}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --image "${IMAGE}" \
    --set-env-vars \
      "DATABASE_URL=secretref:database-url" \
      "OPENROUTER_API_KEY=secretref:openrouter-api-key" \
      "ACCESS_PASSWORD=secretref:access-password" \
      "DEMO_FALLBACK=0" \
      "REASONING_ENABLED=true" \
      "FRONTEND_ORIGIN=${FRONTEND_ORIGIN}" \
      "GIT_REF=${IMAGE_TAG}" \
    -o none
else
  az containerapp create \
    --name "${AZURE_BACKEND_APP}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --environment "${AZURE_CA_ENV}" \
    --image "${IMAGE}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-identity "${IDENTITY_ID}" \
    --user-assigned "${IDENTITY_ID}" \
    --cpu 2 --memory 4Gi \
    --min-replicas 1 --max-replicas 1 \
    --ingress external --target-port 8000 --transport auto \
    --secrets \
      database-url="${DATABASE_URL}" \
      openrouter-api-key="${OPENROUTER_API_KEY}" \
      access-password="${ACCESS_PASSWORD}" \
    --env-vars \
      "DATABASE_URL=secretref:database-url" \
      "OPENROUTER_API_KEY=secretref:openrouter-api-key" \
      "ACCESS_PASSWORD=secretref:access-password" \
      "DEMO_FALLBACK=0" \
      "REASONING_ENABLED=true" \
      "FRONTEND_ORIGIN=${FRONTEND_ORIGIN}" \
      "GIT_REF=${IMAGE_TAG}" \
    -o none
fi

BACKEND_FQDN="$(az containerapp show --name "${AZURE_BACKEND_APP}" --resource-group "${AZURE_RESOURCE_GROUP}" --query properties.configuration.ingress.fqdn -o tsv)"
log "backend URL: https://${BACKEND_FQDN}"

log "Container Apps Job ${AZURE_SEED_JOB} (manual trigger)"
if az containerapp job show --name "${AZURE_SEED_JOB}" --resource-group "${AZURE_RESOURCE_GROUP}" &>/dev/null; then
  az containerapp job update \
    --name "${AZURE_SEED_JOB}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --image "${IMAGE}" \
    -o none
else
  az containerapp job create \
    --name "${AZURE_SEED_JOB}" \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --environment "${AZURE_CA_ENV}" \
    --trigger-type Manual \
    --replica-timeout 3600 \
    --replica-retry-limit 1 \
    --parallelism 1 \
    --replica-completion-count 1 \
    --image "${IMAGE}" \
    --registry-server "${ACR_LOGIN_SERVER}" \
    --registry-identity "${IDENTITY_ID}" \
    --cpu 2 --memory 4Gi \
    --secrets \
      database-url="${DATABASE_URL}" \
      openrouter-api-key="${OPENROUTER_API_KEY}" \
      access-password="${ACCESS_PASSWORD}" \
    --env-vars \
      "DATABASE_URL=secretref:database-url" \
      "OPENROUTER_API_KEY=secretref:openrouter-api-key" \
      "ACCESS_PASSWORD=secretref:access-password" \
      "DATASET_DIR=/dataset" \
    --command "python" "/scripts/seed.py" "--phase" "structure" \
    -o none
fi

if [[ "${SKIP_SWA}" != "1" ]]; then
  log "Static Web App oce-frontend (Free)"
  if ! az staticwebapp show --name oce-frontend --resource-group "${AZURE_RESOURCE_GROUP}" &>/dev/null; then
    az staticwebapp create \
      --name oce-frontend \
      --resource-group "${AZURE_RESOURCE_GROUP}" \
      --location "${AZURE_LOCATION}" \
      --sku Free \
      -o none
  fi
  SWA_HOST="$(az staticwebapp show --name oce-frontend --resource-group "${AZURE_RESOURCE_GROUP}" --query defaultHostname -o tsv)"
  log "SWA URL: https://${SWA_HOST}"
  log "Set FRONTEND_ORIGIN=https://${SWA_HOST} on backend, then redeploy frontend with VITE_API_URL=https://${BACKEND_FQDN}"
fi

cat <<EOF

Bootstrap complete.

Next steps:
  1. Seed structure:  az containerapp job start -g ${AZURE_RESOURCE_GROUP} -n ${AZURE_SEED_JOB}
  2. Seed ingest:     az containerapp job update -g ${AZURE_RESOURCE_GROUP} -n ${AZURE_SEED_JOB} --command "python" "/scripts/seed.py" "--phase" "ingest" && az containerapp job start -g ${AZURE_RESOURCE_GROUP} -n ${AZURE_SEED_JOB}
     Fallback if ingest OOMs: add dev IP to PG firewall, run ingest locally against DATABASE_URL.
  3. Smoke:           python3 scripts/simulate_event.py --api-url "https://${BACKEND_FQDN}"
  4. Wire GitHub OIDC + SWA deployment token (see infra/azure/README.md).

EOF
