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


@dataclass(frozen=True)
class _FitCandidate:
    rmse_v: float
    tau1_s: float
    tau2_s: float
    coefficients: np.ndarray


def _filtered_current(current: np.ndarray, dt_s: float, tau_s: float) -> np.ndarray:
    alpha = float(np.exp(-dt_s / tau_s))
    response = np.zeros(len(current), dtype=float)
    for k in range(1, len(current)):
        response[k] = alpha * response[k - 1] + (1.0 - alpha) * current[k - 1]
    return response


def _validate_inputs(
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    ocv_v: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    current = np.asarray(current_a, dtype=float)
    voltage = np.asarray(voltage_v, dtype=float)
    ocv = np.asarray(ocv_v, dtype=float)
    if not (len(current) == len(voltage) == len(ocv)) or len(current) < 100:
        raise ValueError(
            "Aligned current, voltage, and OCV arrays with >=100 samples are required"
        )
    return current, voltage, ocv


def _response_lookup(
    current: np.ndarray,
    dt_s: float,
    tau_grid: np.ndarray,
) -> dict[float, np.ndarray]:
    return {
        float(tau): _filtered_current(current, dt_s, float(tau))
        for tau in tau_grid
    }


def _physically_valid(coefficients: np.ndarray) -> bool:
    r0, r1, r2, _ = coefficients
    return bool(
        0.001 <= r0 <= 0.20
        and 0.0002 <= r1 <= 0.30
        and 0.0002 <= r2 <= 0.30
    )


def _evaluate_candidate(
    current: np.ndarray,
    target: np.ndarray,
    response1: np.ndarray,
    response2: np.ndarray,
    tau1: float,
    tau2: float,
) -> _FitCandidate | None:
    if tau2 <= 1.5 * tau1:
        return None
    design = np.column_stack(
        [current, response1, response2, np.ones(len(current))]
    )
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    if not _physically_valid(coefficients):
        return None
    prediction = design @ coefficients
    rmse = float(np.sqrt(np.mean((prediction - target) ** 2)))
    return _FitCandidate(rmse, tau1, tau2, coefficients)


def _best_candidate(
    current: np.ndarray,
    target: np.ndarray,
    tau1_grid: np.ndarray,
    tau2_grid: np.ndarray,
    response1: dict[float, np.ndarray],
    response2: dict[float, np.ndarray],
) -> _FitCandidate:
    best: _FitCandidate | None = None
    for tau1 in tau1_grid:
        tau1_value = float(tau1)
        for tau2 in tau2_grid:
            tau2_value = float(tau2)
            candidate = _evaluate_candidate(
                current,
                target,
                response1[tau1_value],
                response2[tau2_value],
                tau1_value,
                tau2_value,
            )
            if candidate is not None and (
                best is None or candidate.rmse_v < best.rmse_v
            ):
                best = candidate
    if best is None:
        raise RuntimeError("No physically valid 2-RC fit found")
    return best


def _to_result(candidate: _FitCandidate) -> ECMFitResult:
    r0, r1, r2, intercept = map(float, candidate.coefficients)
    return ECMFitResult(
        r0=r0,
        r1=r1,
        c1=candidate.tau1_s / r1,
        r2=r2,
        c2=candidate.tau2_s / r2,
        tau1_s=candidate.tau1_s,
        tau2_s=candidate.tau2_s,
        ocv_bias_v=-intercept,
        voltage_rmse_v=candidate.rmse_v,
    )


def fit_2rc_ecm(
    current_a: np.ndarray,
    voltage_v: np.ndarray,
    ocv_v: np.ndarray,
    dt_s: float,
    tau1_grid_s: np.ndarray | None = None,
    tau2_grid_s: np.ndarray | None = None,
) -> ECMFitResult:
    """Fit 2-RC parameters using a time-constant grid and linear least squares."""
    current, voltage, ocv = _validate_inputs(current_a, voltage_v, ocv_v)
    tau1_grid = (
        np.geomspace(2.0, 120.0, 22)
        if tau1_grid_s is None
        else np.asarray(tau1_grid_s, dtype=float)
    )
    tau2_grid = (
        np.geomspace(80.0, 1800.0, 24)
        if tau2_grid_s is None
        else np.asarray(tau2_grid_s, dtype=float)
    )
    response1 = _response_lookup(current, dt_s, tau1_grid)
    response2 = _response_lookup(current, dt_s, tau2_grid)
    candidate = _best_candidate(
        current,
        ocv - voltage,
        tau1_grid,
        tau2_grid,
        response1,
        response2,
    )
    return _to_result(candidate)
