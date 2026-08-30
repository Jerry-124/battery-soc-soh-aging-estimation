from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

import numpy as np


def ocv_from_soc(soc: np.ndarray | float) -> np.ndarray | float:
    """Smooth monotonic synthetic NMC-like OCV curve used by the demo."""
    z = np.asarray(soc, dtype=float)
    value = 3.05 + 1.02 * z + 0.10 * np.tanh(8.0 * (z - 0.12)) + 0.05 * np.tanh(10.0 * (z - 0.88))
    return float(value) if value.ndim == 0 else value


def docv_dsoc(soc: np.ndarray | float) -> np.ndarray | float:
    z = np.asarray(soc, dtype=float)
    value = 1.02 + 0.8 / np.cosh(8.0 * (z - 0.12)) ** 2 + 0.5 / np.cosh(10.0 * (z - 0.88)) ** 2
    return float(value) if value.ndim == 0 else value


@dataclass(frozen=True)
class ECMParameters:
    capacity_ah: float = 2.30
    coulombic_efficiency: float = 0.995
    r0: float = 0.018
    r1: float = 0.012
    c1: float = 2400.0
    r2: float = 0.025
    c2: float = 12000.0

    def aged(self, capacity_factor: float, resistance_factor: float) -> ECMParameters:
        return replace(
            self,
            capacity_ah=self.capacity_ah * capacity_factor,
            r0=self.r0 * resistance_factor,
            r1=self.r1 * resistance_factor,
            r2=self.r2 * resistance_factor,
        )


class SecondOrderThevenin:
    """Discrete 2-RC Thevenin ECM with discharge-positive current."""

    def __init__(
        self,
        params: ECMParameters,
        dt_s: float,
        ocv_function: Callable[[np.ndarray | float], np.ndarray | float] = ocv_from_soc,
        docv_function: Callable[[np.ndarray | float], np.ndarray | float] = docv_dsoc,
    ):
        if dt_s <= 0:
            raise ValueError("dt_s must be positive")
        self.params = params
        self.dt_s = float(dt_s)
        self.ocv_function = ocv_function
        self.docv_function = docv_function

    def transition(self, state: np.ndarray, current_a: float) -> np.ndarray:
        p = self.params
        soc, v1, v2 = np.asarray(state, dtype=float)
        a1 = np.exp(-self.dt_s / (p.r1 * p.c1))
        a2 = np.exp(-self.dt_s / (p.r2 * p.c2))
        next_soc = soc - p.coulombic_efficiency * current_a * self.dt_s / (3600.0 * p.capacity_ah)
        next_v1 = a1 * v1 + p.r1 * (1.0 - a1) * current_a
        next_v2 = a2 * v2 + p.r2 * (1.0 - a2) * current_a
        return np.array([np.clip(next_soc, 0.0, 1.0), next_v1, next_v2], dtype=float)

    def terminal_voltage(self, state: np.ndarray, current_a: float) -> float:
        soc, v1, v2 = np.asarray(state, dtype=float)
        return float(self.ocv_function(soc) - current_a * self.params.r0 - v1 - v2)

    def state_jacobian(self) -> np.ndarray:
        p = self.params
        return np.diag([
            1.0,
            np.exp(-self.dt_s / (p.r1 * p.c1)),
            np.exp(-self.dt_s / (p.r2 * p.c2)),
        ])

    def measurement_jacobian(self, state: np.ndarray) -> np.ndarray:
        return np.array([[self.docv_function(float(state[0])), -1.0, -1.0]], dtype=float)
