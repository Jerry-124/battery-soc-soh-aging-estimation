from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ECMFitResult:
    r0: float
    r1: float
    c1: float
    r2: float
    c2: float
    tau1_s: float
    tau2_s: float
    ocv_bias_v: float
    voltage_rmse_v: float


def _filtered_current(current: np.ndarray, dt_s: float, tau_s: float) -> np.ndarray:
    alpha = float(np.exp(-dt_s / tau_s))
    response = np.zeros(len(current), dtype=float)
    for k in range(1, len(current)):
        response[k] = alpha * response[k - 1] + (1.0 - alpha) * current[k - 1]
    return response


def fit_2rc_ecm(
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    ocv_v: np.ndarray,
    dt_s: float,
    tau1_grid_s: np.ndarray | None = None,
    tau2_grid_s: np.ndarray | None = None,
) -> ECMFitResult:
    """Fit 2-RC parameters using a time-constant grid and linear least squares."""
    current = np.asarray(current_a, dtype=float)
    voltage = np.asarray(voltage_v, dtype=float)
    ocv = np.asarray(ocv_v, dtype=float)
    if not (len(current) == len(voltage) == len(ocv)) or len(current) < 100:
        raise ValueError("Aligned current, voltage, and OCV arrays with >=100 samples are required")
    tau1_grid = np.geomspace(2.0, 120.0, 22) if tau1_grid_s is None else np.asarray(tau1_grid_s)
    tau2_grid = np.geomspace(80.0, 1800.0, 24) if tau2_grid_s is None else np.asarray(tau2_grid_s)
    response1 = {float(tau): _filtered_current(current, dt_s, float(tau)) for tau in tau1_grid}
    response2 = {float(tau): _filtered_current(current, dt_s, float(tau)) for tau in tau2_grid}
    target = ocv - voltage
    best: tuple[float, float, float, np.ndarray] | None = None
    for tau1 in tau1_grid:
        for tau2 in tau2_grid:
            if tau2 <= 1.5 * tau1:
                continue
            # target = R0*I + R1*g1 + R2*g2 - OCV_bias
            design = np.column_stack([current, response1[float(tau1)], response2[float(tau2)], np.ones(len(current))])
            coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
            r0, r1, r2, intercept = coefficients
            if not (0.001 <= r0 <= 0.20 and 0.0002 <= r1 <= 0.30 and 0.0002 <= r2 <= 0.30):
                continue
            prediction = design @ coefficients
            rmse = float(np.sqrt(np.mean((prediction - target) ** 2)))
            if best is None or rmse < best[0]:
                best = (rmse, float(tau1), float(tau2), coefficients)
    if best is None:
        raise RuntimeError("No physically valid 2-RC fit found")
    rmse, tau1, tau2, coefficients = best
    r0, r1, r2, intercept = map(float, coefficients)
    return ECMFitResult(
        r0=r0,
        r1=r1,
        c1=tau1 / r1,
        r2=r2,
        c2=tau2 / r2,
        tau1_s=tau1,
        tau2_s=tau2,
        ocv_bias_v=-intercept,
        voltage_rmse_v=rmse,
    )

