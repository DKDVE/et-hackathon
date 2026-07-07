#!/usr/bin/env bash
# M9 night-before gate — one readable line per check, non-zero on any red.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GREEN='\033[32m'
RED='\033[31m'
NC='\033[0m'
FAIL=0

pass() { echo -e "${GREEN}PASS${NC} — $1"; }
fail() { echo -e "${RED}FAIL${NC} — $1"; FAIL=1; }

echo "=== demo-gate ==="

# 1 — default unit suite
if (cd backend && pytest -q -m "not slow and not destructive"); then
  pass "default test suite"
else
  fail "default test suite"
fi

# 2 — golden (needs seeded + ingested DB)
if (cd backend && pytest -q -m slow tests/golden tests/test_assembler_determinism.py tests/test_lexical_channel.py); then
  pass "golden suite"
else
  fail "golden suite"
fi

# 3 — destructive verify-seed (fixture restores structure + ingest on exit)
if docker compose exec -T backend pytest -q -m destructive tests/test_seed_verification.py; then
  pass "verify-seed (structure verified; ingest restored)"
else
  fail "verify-seed"
fi

# 4 — normalization audit (substrate-level; no dossier needed)
if docker compose exec -T backend python -m tests.audits.normalization_audit; then
  pass "normalization audit"
else
  fail "normalization audit"
fi

# 5 — fresh timed demo-event dossier (creates the dossier audits target)
set +e
TIMING_OUT="$(docker compose exec -T backend python /scripts/demo_gate_timing.py 2>&1)"
TIMING_RC=$?
set -e
if [ "$TIMING_RC" -eq 0 ]; then
  pass "timed demo-event dossier (wall <60s, analysis <30s)"
  echo "$TIMING_OUT"
else
  fail "timed demo-event dossier (wall <60s, analysis <30s)"
  echo "$TIMING_OUT" >&2
fi

DOSSIER_ID="$(echo "$TIMING_OUT" | sed -n 's/.*dossier=\([0-9][0-9]*\).*/\1/p' | tail -1)"
if [ -z "$DOSSIER_ID" ]; then
  DOSSIER_ID="$(docker compose exec -T backend python -c "
from sqlalchemy import select
from app.db.engine import SessionLocal
from app.db.models import Dossier
with SessionLocal() as s:
    d = s.scalar(select(Dossier).where(Dossier.sections.isnot(None)).order_by(Dossier.id.desc()))
    print(d.id if d else '')
" | tr -d '\r')"
fi

# 6 — groundedness + prose-ID on the timed dossier (verify-seed wipes prior rows)
if [ -z "$DOSSIER_ID" ]; then
  fail "groundedness walker (no complete dossier after timed run)"
  fail "prose-ID audit (no complete dossier after timed run)"
else
  if docker compose exec -T backend python -m tests.audits.groundedness_audit "$DOSSIER_ID"; then
    pass "groundedness walker (dossier $DOSSIER_ID)"
  else
    fail "groundedness walker (dossier $DOSSIER_ID)"
  fi
  if docker compose exec -T backend python -m tests.audits.prose_id_audit "$DOSSIER_ID"; then
    pass "prose-ID audit (dossier $DOSSIER_ID)"
  else
    fail "prose-ID audit (dossier $DOSSIER_ID)"
  fi
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo -e "${GREEN}DEMO-GATE: ALL GREEN${NC}"
else
  echo -e "${RED}DEMO-GATE: RED — see failures above${NC}"
fi
exit "$FAIL"
