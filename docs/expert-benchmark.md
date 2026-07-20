# Domain-Expert Benchmark

Half-page summary for judges and maintainers.

## What it tests

Nine questions phrased the way a **plant reliability engineer** would ask during an abnormality response on pump **P-3401** (demo event). They span:

- OEM flush-plan and SOP isolation requirements (cited answers)
- Sister-asset failure-mode linkage
- Pattern-panel downtime figures (deterministic dossier context)
- Honest refusal when the assembled records do not contain the fact
- OCR-backed SOP content (SOP-001 scanned page path)

Assertions are **structural only**: cited vs refused, citation IDs ∈ evidence pool, coarse token presence — never exact wording.

## Current pass state

Run after `make up`, `make seed`, `make ingest`, and with `OPENROUTER_API_KEY` set:

```bash
make test-llm
```

The benchmark lives in `backend/tests/llm/test_expert_benchmark.py` (marker `llm`). A failure is a **finding** for the milestone report — do not change prompts or product logic to greenwash a fail during freeze.

## How to run (isolated)

```bash
cd backend && pytest -v -m llm tests/llm/test_expert_benchmark.py
```

Requires the compose Postgres substrate and a valid OpenRouter key (same gate as `test_llm_reasoning.py`).
