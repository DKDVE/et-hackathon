#!/usr/bin/env bash
# Bootstrap OCE backend on a new Azure subscription (frontend stays on GitHub Pages).
#
# Prereqs:
#   az login   # new account
#   export AZURE_SUBSCRIPTION_ID='<new-subscription-id>'
#
# Required env (same as deploy.sh):
#   AZURE_ACR_NAME, AZURE_PG_ADMIN_PASSWORD, AZURE_DEV_IP,
#   OPENROUTER_API_KEY, ACCESS_PASSWORD
#
# Optional:
#   TEARDOWN_OLD=1  — delete rg-oce-hackathon on the account currently logged in first
#   SKIP_OIDC=1     — skip GitHub OIDC setup (vars already updated)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RG="${AZURE_RESOURCE_GROUP:-rg-oce-hackathon}"

if [[ -n "${AZURE_SUBSCRIPTION_ID:-}" ]]; then
  az account set --subscription "$AZURE_SUBSCRIPTION_ID"
fi

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
echo "Using subscription ${SUBSCRIPTION_ID} ($(az account show --query name -o tsv))"

if [[ "${TEARDOWN_OLD:-0}" == "1" ]]; then
  echo "Deleting resource group ${RG} (async)…"
  az group delete --name "$RG" --yes --no-wait || true
fi

export FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-https://dkdve.github.io,http://localhost:5173}"
export SKIP_SWA=1
export SKIP_BUILD=1
# ponytail: student subs often block Container Apps in centralindia — eastasia works on UPES
export AZURE_CA_LOCATION="${AZURE_CA_LOCATION:-eastasia}"

"${ROOT}/infra/azure/deploy.sh"

if [[ "${SKIP_OIDC:-0}" != "1" ]]; then
  chmod +x "${ROOT}/infra/azure/setup-github-oidc.sh"
  "${ROOT}/infra/azure/setup-github-oidc.sh" "$RG"
fi

BACKEND_FQDN="$(az containerapp show -g "$RG" -n oce-backend --query properties.configuration.ingress.fqdn -o tsv)"
echo ""
echo "Backend (placeholder image until CI push): https://${BACKEND_FQDN}"
echo ""
echo "Next:"
echo "  1. gh workflow run deploy.yml -R DKDVE/et-hackathon   # push real image (~20 min)"
echo "  2. az containerapp job start -g $RG -n oce-seed"
echo "  3. az containerapp job update -g $RG -n oce-seed --set-env-vars SEED_PHASE=ingest"
echo "     az containerapp job start -g $RG -n oce-seed"
echo "  4. gh workflow run pages.yml -R DKDVE/et-hackathon      # refresh CORS + UI"
echo "  5. python3 scripts/simulate_event.py --api-url https://${BACKEND_FQDN} --access-password \"\$ACCESS_PASSWORD\""
