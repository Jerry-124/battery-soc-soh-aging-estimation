from __future__ import annotations

import numpy as np

from battery_estimation.models.ecm import SecondOrderThevenin


class ExtendedKalmanFilter:
    def __init__(
        self,
        model: SecondOrderThevenin,
        initial_state: np.ndarray,
        initial_covariance: np.ndarray,
        process_covariance: np.ndarray,
        voltage_variance: float,
    ):
        self.model = model
        self.x = np.asarray(initial_state, dtype=float).copy()
        self.p = np.asarray(initial_covariance, dtype=float).copy()
        self.q = np.asarray(process_covariance, dtype=float).copy()
        self.r = float(voltage_variance)

    def step(self, current_a: float, voltage_v: float, measurement_current_a: float | None = None) -> np.ndarray:
        f = self.model.state_jacobian()
        x_pred = self.model.transition(self.x, current_a)
        p_pred = f @ self.p @ f.T + self.q
        h = self.model.measurement_jacobian(x_pred)
        measurement_current = current_a if measurement_current_a is None else measurement_current_a
        predicted_voltage = self.model.terminal_voltage(x_pred, measurement_current)
        innovation = float(voltage_v - predicted_voltage)
        s = float((h @ p_pred @ h.T)[0, 0] + self.r)
        gain = (p_pred @ h.T) / max(s, 1e-12)
        self.x = x_pred + gain[:, 0] * innovation
        self.x[0] = np.clip(self.x[0], 0.0, 1.0)
        identity = np.eye(3)
        kh = gain @ h
        self.p = (identity - kh) @ p_pred @ (identity - kh).T + gain * self.r @ gain.T
        self.p = 0.5 * (self.p + self.p.T)
        return self.x.copy()

    def run(self, current_a: np.ndarray, voltage_v: np.ndarray) -> np.ndarray:
        states = np.empty((len(current_a), 3), dtype=float)
        states[0] = self.x
        for k in range(1, len(current_a)):
            states[k] = self.step(float(current_a[k - 1]), float(voltage_v[k]), float(current_a[k]))
        return states
