from __future__ import annotations

import numpy as np


def identify_ohmic_resistance(delta_voltage_v: float, delta_current_a: float) -> float:
    if abs(delta_current_a) < 1e-12:
        raise ValueError("Current step must be non-zero")
    return abs(delta_voltage_v / delta_current_a)


def identify_relaxation_grid(time_s: np.ndarray, polarization_v: np.ndarray) -> dict[str, float]:
    """Fit V(t)=A1*exp(-t/tau1)+A2*exp(-t/tau2) using a NumPy-only grid search."""
    t = np.asarray(time_s, dtype=float)
    y = np.asarray(polarization_v, dtype=float)
    if len(t) < 5 or len(t) != len(y):
        raise ValueError("At least five aligned relaxation samples are required")
    tau_grid = np.geomspace(max(1.0, np.diff(t).mean()), max(4.0, t[-1] * 2.0), 45)
    best: tuple[float, float, float, float, float] | None = None
    for i, tau1 in enumerate(tau_grid[:-1]):
        for tau2 in tau_grid[i + 1 :]:
            design = np.column_stack([np.exp(-t / tau1), np.exp(-t / tau2)])
            amplitudes, *_ = np.linalg.lstsq(design, y, rcond=None)
            prediction = design @ amplitudes
            mse = float(np.mean((prediction - y) ** 2))
            if best is None or mse < best[0]:
                best = (mse, tau1, tau2, float(amplitudes[0]), float(amplitudes[1]))
    if best is None:
        raise RuntimeError("Relaxation grid search produced no candidate fit")
    return {
        "mse": best[0],
        "tau1_s": best[1],
        "tau2_s": best[2],
        "amplitude1_v": best[3],
        "amplitude2_v": best[4],
    }
