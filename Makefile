.PHONY: up down dataset seed ingest test test-all golden verify-seed types lint typecheck audit-norm

up:
	docker compose up -d

down:
	docker compose down

# Render all dataset artifacts from dataset/design/meridian.yaml (P10).
# Deterministic; regenerates dataset/rendered/. Uses uv with the dataset deps.
DATASET_RUN = uv run --no-project --python 3.12 --with fpdf2 --with pyyaml --with pillow python
dataset:
	$(DATASET_RUN) dataset/generators/render_wo.py
	$(DATASET_RUN) dataset/generators/render_manual.py
	$(DATASET_RUN) dataset/generators/render_sops.py
	$(DATASET_RUN) dataset/generators/render_reports.py
	$(DATASET_RUN) dataset/generators/render_registry.py
	$(DATASET_RUN) dataset/generators/validate_design.py

# Structure-phase seed (wipe -> load -> verify) in the one-shot compose service.
seed:
	docker compose run --rm seed

# M3 ingest phase (chunk, embed, normalize) — requires structure phase first.
ingest:
	docker compose run --rm seed python /scripts/seed.py --phase ingest

test:
	cd backend && pytest -v -m "not slow and not destructive"

test-all:
	cd backend && pytest -v -m "not destructive"

# Destructive DB verification (TRUNCATE + reseed structure phase). Run in
# isolation — it wipes the substrate, so keep it out of the default suite.
verify-seed:
	docker compose exec -T backend pytest -v -m destructive tests/test_seed_verification.py

# M4 golden suite + slow assembler/lexical tests. Requires seed + ingest first
# (loads the local embedding model, hits the compose DB).
golden:
	cd backend && pytest -v -m slow tests/golden tests/test_assembler_determinism.py tests/test_lexical_channel.py

audit-norm:
	cd backend && python -m tests.audits.normalization_audit

# Generate frontend API types from the backend OpenAPI schema (Task 5). The
# backend must be up (`make up`); types land in frontend/src/lib/api-types.ts.
types:
	cd frontend && npm run gen:types

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck
