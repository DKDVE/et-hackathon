"""Ensure work_orders_truth.csv is only referenced by the audit module."""

from __future__ import annotations

from pathlib import Path

TRUTH_NAME = "work_orders_truth.csv"
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "pgdata", "proc"}
_SKIP_SUFFIXES = {".pyc", ".png", ".pdf", ".whl"}


def _scan_roots() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [here.parents[1]]  # backend/
    repo = here.parents[2]
    for name in ("dataset", "scripts"):
        p = repo / name
        if p.is_dir():
            roots.append(p)
    for mount in (Path("/dataset"), Path("/scripts")):
        if mount.is_dir() and mount not in roots:
            roots.append(mount)
    return roots


def _allowed_paths() -> set[Path]:
    here = Path(__file__).resolve()
    repo = here.parents[2]
    return {
        (repo / "dataset/generators/render_wo.py").resolve(),
        (here.parent / "audits/normalization_audit.py").resolve(),
        (here.parent / "test_routine_guard.py").resolve(),
        Path("/dataset/generators/render_wo.py").resolve(),
        Path("/app/tests/audits/normalization_audit.py").resolve(),
    }


def test_truth_file_only_opened_by_audit() -> None:
    allowed = _allowed_paths()
    allowed.add(Path(__file__).resolve())
    offenders: list[Path] = []
    for root in _scan_roots():
        for path in root.rglob("*"):
            if any(p in _SKIP_DIRS for p in path.parts):
                continue
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            if path.suffix in _SKIP_SUFFIXES:
                continue
            if path.suffix not in {".py", ".md", ".yml", ".yaml", ".csv", ".toml"}:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if TRUTH_NAME in text and path.resolve() not in allowed:
                offenders.append(path)
    assert not offenders, f"unexpected references to {TRUTH_NAME}: {offenders}"
