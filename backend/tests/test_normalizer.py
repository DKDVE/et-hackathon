"""Normalizer threshold/margin logic with synthetic vectors — no model load."""

from __future__ import annotations

import numpy as np

from app.memory.ingestion.wo_normalizer import classify_vector


def _unit(v: list[float]) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    return a / np.linalg.norm(a)


def test_classifies_when_above_threshold_and_margin() -> None:
    modes = np.stack([_unit([1, 0, 0]), _unit([0, 1, 0]), _unit([0, 0, 1])])
    query = _unit([0.95, 0.1, 0.0])
    idx, score = classify_vector(query, modes, threshold=0.60, margin=0.05)
    assert idx == 0
    assert score > 0.60


def test_unclassified_when_margin_too_small() -> None:
    modes = np.stack([_unit([1, 0, 0]), _unit([0.98, 0.2, 0])])
    modes[1] = modes[1] / np.linalg.norm(modes[1])
    query = _unit([0.99, 0.15, 0])
    idx, score = classify_vector(query, modes, threshold=0.60, margin=0.05)
    assert idx is None
    assert score > 0.60


def test_unclassified_when_below_threshold() -> None:
    modes = np.stack([_unit([1, 0]), _unit([0, 1])])
    query = _unit([0.5, 0.5])
    idx, score = classify_vector(query, modes, threshold=0.80, margin=0.05)
    assert idx is None
    assert score < 0.80


def _near_tie_case() -> tuple[np.ndarray, np.ndarray]:
    """Two near-parallel modes + a query that scores just above both, with a
    top-vs-runner margin below any realistic margin threshold."""
    modes = np.stack([_unit([1.0, 0.0, 0.0]), _unit([0.985, 0.173, 0.0])])
    query = _unit([0.997, 0.078, 0.0])
    return query, modes


def test_same_family_near_tie_assigns() -> None:
    """D-017: within a family, a sub-margin near-tie still assigns the top mode."""
    query, modes = _near_tie_case()
    idx, score = classify_vector(
        query, modes, threshold=0.60, margin=0.05, families=["sealing", "sealing"]
    )
    assert idx == 0
    assert score >= 0.60
    # sanity: the margin really is below the threshold (else the test is vacuous)
    scores = modes @ query
    assert float(scores[0] - scores[1]) < 0.05


def test_cross_family_near_tie_does_not_assign() -> None:
    """D-017: the same sub-margin near-tie across families is rejected."""
    query, modes = _near_tie_case()
    idx, _score = classify_vector(
        query, modes, threshold=0.60, margin=0.05, families=["sealing", "hydraulic"]
    )
    assert idx is None


def test_threshold_still_binds_within_family() -> None:
    """D-017: family membership never overrides the score threshold."""
    query, modes = _near_tie_case()
    idx, score = classify_vector(
        query, modes, threshold=0.999, margin=0.05, families=["sealing", "sealing"]
    )
    assert idx is None
    assert score < 0.999
