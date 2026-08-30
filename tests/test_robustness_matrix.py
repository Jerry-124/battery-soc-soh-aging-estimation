from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_robustness_matrix import (
    CATEGORIES,
    OBSERVERS,
    UNCERTAINTY_LEVELS,
    _summarize_rows,
    _uncertainty_matrix,
)


def _base_rows() -> list[dict]:
    rows = []
    for category_index, category in enumerate(CATEGORIES, start=1):
        for observer_index, observer in enumerate(OBSERVERS, start=1):
            rows.extend(
                [
                    {
                        "category": category,
                        "level": "a",
                        "observer": observer,
                        "post_300s_rmse_pct": float(category_index + observer_index),
                    },
                    {
                        "category": category,
                        "level": "b",
                        "observer": observer,
                        "post_300s_rmse_pct": float(category_index + observer_index + 2),
                    },
                ]
            )
    return rows


def test_summarize_rows_preserves_category_observer_aggregation() -> None:
    summary = _summarize_rows(_base_rows())

    assert set(summary) == set(CATEGORIES)
    assert set(summary["measurement_noise"]) == set(OBSERVERS)
    assert summary["initial_soc_error"]["ekf"]["mean_post_300s_rmse_pct"] == 3.0
    assert summary["initial_soc_error"]["ekf"]["worst_post_300s_rmse_pct"] == 4.0
    assert summary["parameter_uncertainty"]["ukf"]["mean_post_300s_rmse_pct"] == 6.0


def test_uncertainty_matrix_keeps_capacity_rows_and_resistance_columns() -> None:
    rows = []
    for i, capacity in enumerate(UNCERTAINTY_LEVELS):
        for j, resistance in enumerate(UNCERTAINTY_LEVELS):
            rows.append(
                {
                    "category": "parameter_uncertainty",
                    "level": f"C={capacity:.1f},R={resistance:.1f}",
                    "observer": "ekf",
                    "post_300s_rmse_pct": float(10 * i + j),
                }
            )

    matrix = _uncertainty_matrix(rows)

    assert matrix.shape == (5, 5)
    assert np.array_equal(matrix[0], np.arange(5, dtype=float))
    assert np.array_equal(matrix[:, 0], np.arange(0, 50, 10, dtype=float))
