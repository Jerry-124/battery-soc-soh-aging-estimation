from __future__ import annotations

import numpy as np

from battery_estimation.models.ecm import SecondOrderThevenin


class UnscentedKalmanFilter:
    def __init__(
        self,
        model: SecondOrderThevenin,
        initial_state: np.ndarray,
        initial_covariance: np.ndarray,
        process_covariance: np.ndarray,
        voltage_variance: float,
        alpha: float = 0.2,
        beta: float = 2.0,
        kappa: float = 0.0,
    ):
        self.model = model
        self.x = np.asarray(initial_state, dtype=float).copy()
        self.p = np.asarray(initial_covariance, dtype=float).copy()
        self.q = np.asarray(process_covariance, dtype=float).copy()
        self.r = float(voltage_variance)
        self.n = len(self.x)
        self.lambda_ = alpha**2 * (self.n + kappa) - self.n
        self.wm = np.full(2 * self.n + 1, 1.0 / (2.0 * (self.n + self.lambda_)))
        self.wc = self.wm.copy()
        self.wm[0] = self.lambda_ / (self.n + self.lambda_)
        self.wc[0] = self.wm[0] + (1.0 - alpha**2 + beta)

    def _sigma_points(self, mean: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        scaled = (self.n + self.lambda_) * covariance
        jitter = 1e-12
        for _ in range(6):
            try:
                root = np.linalg.cholesky(scaled + jitter * np.eye(self.n))
                break
            except np.linalg.LinAlgError:
                jitter *= 10.0
        else:
            values, vectors = np.linalg.eigh(scaled)
            root = vectors @ np.diag(np.sqrt(np.maximum(values, 1e-12)))
        points = np.empty((2 * self.n + 1, self.n), dtype=float)
        points[0] = mean
        for i in range(self.n):
            points[i + 1] = mean + root[:, i]
            points[self.n + i + 1] = mean - root[:, i]
        return points

    def step(self, current_a: float, voltage_v: float, measurement_current_a: float | None = None) -> np.ndarray:
        sigma = self._sigma_points(self.x, self.p)
        predicted_sigma = np.array([self.model.transition(point, current_a) for point in sigma])
        x_pred = np.sum(self.wm[:, None] * predicted_sigma, axis=0)
        dx = predicted_sigma - x_pred
        p_pred = np.einsum("i,ij,ik->jk", self.wc, dx, dx) + self.q
        measurement_current = current_a if measurement_current_a is None else measurement_current_a
        voltage_sigma = np.array([self.model.terminal_voltage(point, measurement_current) for point in predicted_sigma])
        voltage_pred = float(np.dot(self.wm, voltage_sigma))
        dz = voltage_sigma - voltage_pred
        s = float(np.dot(self.wc, dz * dz) + self.r)
        cross = np.einsum("i,ij,i->j", self.wc, dx, dz)
        gain = cross / max(s, 1e-12)
        self.x = x_pred + gain * (voltage_v - voltage_pred)
        self.x[0] = np.clip(self.x[0], 0.0, 1.0)
        self.p = p_pred - np.outer(gain, gain) * s
        self.p = 0.5 * (self.p + self.p.T) + 1e-12 * np.eye(self.n)
        return self.x.copy()

    def run(self, current_a: np.ndarray, voltage_v: np.ndarray) -> np.ndarray:
        states = np.empty((len(current_a), self.n), dtype=float)
        states[0] = self.x
        for k in range(1, len(current_a)):
            states[k] = self.step(float(current_a[k - 1]), float(voltage_v[k]), float(current_a[k]))
        return states
