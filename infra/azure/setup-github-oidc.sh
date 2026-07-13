#!/usr/bin/env bash
# One-time GitHub Actions OIDC for Azure deploy (new subscription / tenant).
# Usage: ./infra/azure/setup-github-oidc.sh [resource-group]
set -euo pipefail

RG="${1:-rg-oce-hackathon}"
APP_NAME="${GITHUB_OIDC_APP_NAME:-github-oce-deploy}"
REPO="${GITHUB_REPO:-DKDVE/et-hackathon}"
BRANCH_REF="${GITHUB_OIDC_REF:-refs/heads/main}"

SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"

echo "subscription: ${SUBSCRIPTION_ID}"
echo "tenant:       ${TENANT_ID}"
echo "resource grp: ${RG}"

APP_ID="$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv 2>/dev/null || true)"
if [[ -z "${APP_ID}" ]]; then
  APP_ID="$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)"
  az ad sp create --id "$APP_ID" -o none
  echo "created app registration ${APP_NAME}"
else
  echo "reusing app registration ${APP_NAME} (${APP_ID})"
fi

CRED_NAME="github-main"
if ! az ad app federated-credential show --id "$APP_ID" --federated-credential-id "$CRED_NAME" &>/dev/null; then
  az ad app federated-credential create --id "$APP_ID" --parameters "{
    \"name\": \"${CRED_NAME}\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${REPO}:ref:${BRANCH_REF}\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }"
  echo "created federated credential ${CRED_NAME}"
fi

SP_OID="$(az ad sp show --id "$APP_ID" --query id -o tsv)"
SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RG}"
if ! az role assignment list --assignee "$SP_OID" --scope "$SCOPE" --query "[?roleDefinitionName=='Contributor']" -o tsv | grep -q .; then
  az role assignment create --assignee "$SP_OID" --role Contributor --scope "$SCOPE"
  echo "Contributor on ${SCOPE}"
fi

echo ""
echo "Set GitHub repo variables (Settings → Secrets and variables → Actions):"
echo "  AZURE_CLIENT_ID=${APP_ID}"
echo "  AZURE_TENANT_ID=${TENANT_ID}"
echo "  AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}"
echo ""

if command -v gh &>/dev/null; then
  gh variable set AZURE_CLIENT_ID --body "$APP_ID" -R "$REPO"
  gh variable set AZURE_TENANT_ID --body "$TENANT_ID" -R "$REPO"
  gh variable set AZURE_SUBSCRIPTION_ID --body "$SUBSCRIPTION_ID" -R "$REPO"
  echo "Updated GitHub variables via gh CLI."
fi
