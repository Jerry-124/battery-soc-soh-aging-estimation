from __future__ import annotations

import numpy as np


def calculate_metrics(reference: np.ndarray, estimate: np.ndarray, dt_s: float) -> dict[str, float | None]:
    error = np.asarray(estimate) - np.asarray(reference)
    abs_error = np.abs(error)
    within = np.flatnonzero(abs_error <= 0.02)
    convergence_s = float(within[0] * dt_s) if len(within) else None
    return {
        "rmse_pct": float(100.0 * np.sqrt(np.mean(error**2))),
        "mae_pct": float(100.0 * np.mean(abs_error)),
        "max_error_pct": float(100.0 * np.max(abs_error)),
        "final_error_pct": float(100.0 * error[-1]),
        "convergence_s": convergence_s,
    }
