# Render deployment (superseded)

**Superseded by Azure — D-026.** See [`infra/azure/README.md`](../../../infra/azure/README.md).

These files are kept for reference only. The hosted track now uses Azure Container Apps +
Azure Database for PostgreSQL + Azure Static Web Apps.

## Archived artifacts

| File | Purpose |
|------|---------|
| [`render.yaml`](render.yaml) | Render Blueprint (M15 / D-025) |
| [`Dockerfile`](Dockerfile) | Root Dockerfile shim for Render auto-detect |

Local demo (`docker compose up`, `make demo-gate`) never used these paths.
