#!/usr/bin/env bash
# M9 night-before gate — functional checks are red; timing checks are yellow WARN.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
NC='\033[0m'
FAIL=0
TIMING_ACTION='WARN: provider slow today → at T-30m regenerate cache on final board state; rehearse long-assembly narration; bookmark cached dossier as plan B'

pass() { echo -e "${GREEN}PASS${NC} — $1"; }
warn() { echo -e "${YELLOW}WARN${NC} — $1"; echo "  → $TIMING_ACTION"; }
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
TIMING_WARN=0
if echo "$TIMING_OUT" | grep -q 'TIMING_WARN:'; then
  TIMING_WARN=1
fi
if [ "$TIMING_RC" -eq 0 ] && [ "$TIMING_WARN" -eq 0 ]; then
  pass "timed demo-event dossier (wall <60s, analysis <30s)"
  echo "$TIMING_OUT"
elif [ "$TIMING_RC" -eq 0 ] && [ "$TIMING_WARN" -eq 1 ]; then
  warn "timed demo-event dossier (wall <60s, analysis <30s)"
  echo "$TIMING_OUT"
else
  fail "timed demo-event dossier (functional failure)"
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

# 6 — groundedness + prose-ID on the timed dossier (after timed run, M9 order)
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

# 7 — fallback cache present for demo event fingerprint (P9 / NFR-7)
if docker compose exec -T backend python -c "
from sqlalchemy import select
from app.db.engine import SessionLocal
from app.db.models import ReasoningFallbackCache
from app.reasoning.prompts import analysis
with SessionLocal() as s:
    rows = s.scalars(select(ReasoningFallbackCache)).all()
    ok = any(
        (r.prompt_versions or {}).get('analysis') == analysis.PROMPT_VERSION and r.events
        for r in rows
    )
    if not ok:
        raise SystemExit(1)
    key = next(
        r.cache_key for r in rows
        if (r.prompt_versions or {}).get('analysis') == analysis.PROMPT_VERSION and r.events
    )
    print(f'cache_key={key[:8]}… prompt={analysis.PROMPT_VERSION}')
"; then
  pass "fallback replay cache (analysis prompt current)"
else
  fail "fallback replay cache (run live demo event to populate v4 cache)"
fi

echo ""
if [ "$FAIL" -eq 0 ]; then
  if [ "$TIMING_WARN" -eq 1 ]; then
    echo -e "${YELLOW}DEMO-GATE: GREEN with timing WARN — see yellow above${NC}"
  else
    echo -e "${GREEN}DEMO-GATE: ALL GREEN${NC}"
  fi
else
  echo -e "${RED}DEMO-GATE: RED — see failures above${NC}"
fi
exit "$FAIL"
