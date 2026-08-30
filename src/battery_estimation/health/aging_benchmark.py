from __future__ import annotations

from dataclasses import replace

import numpy as np

from battery_estimation.estimators import ExtendedKalmanFilter, UnscentedKalmanFilter
from battery_estimation.models import ECMParameters, SecondOrderThevenin


def pulse_anchored_fresh_parameters(capacity_ah: float, resistance_5s_ohm: float) -> ECMParameters:
    """Construct a 2-RC model whose rest-to-pulse 5 s response matches the measurement."""
    fractions = np.array([0.50, 0.30, 0.20])
    tau1_s, tau2_s = 10.0, 150.0
    response = fractions[0] + fractions[1] * (1.0 - np.exp(-5.0 / tau1_s)) + fractions[2] * (1.0 - np.exp(-5.0 / tau2_s))
    total_r = resistance_5s_ohm / response
    r0, r1, r2 = fractions * total_r
    return ECMParameters(capacity_ah=capacity_ah, r0=r0, r1=r1, c1=tau1_s / r1, r2=r2, c2=tau2_s / r2)


def perturb_parameters(params: ECMParameters, capacity_multiplier: float, resistance_multiplier: float) -> ECMParameters:
    return replace(params, capacity_ah=params.capacity_ah * capacity_multiplier,
                   r0=params.r0 * resistance_multiplier, r1=params.r1 * resistance_multiplier,
                   r2=params.r2 * resistance_multiplier)


def run_kalman_observers(params: ECMParameters, dt_s: float, current_a: np.ndarray,
                         voltage_v: np.ndarray, initial_soc: float,
                         voltage_noise_std_v: float) -> dict[str, np.ndarray]:
    model = SecondOrderThevenin(params, dt_s)
    x0 = np.array([initial_soc, 0.0, 0.0])
    p0 = np.diag([0.04, 0.002, 0.002])
    q = np.diag([2e-7, 2e-6, 2e-6])
    r = max(voltage_noise_std_v**2, 1e-8)
    return {
        "ekf": ExtendedKalmanFilter(model, x0, p0.copy(), q, r).run(current_a, voltage_v)[:, 0],
        "ukf": UnscentedKalmanFilter(model, x0, p0.copy(), q, r).run(current_a, voltage_v)[:, 0],
    }
