from __future__ import annotations

import numpy as np


class CoulombCounter:
    def __init__(self, initial_soc: float, capacity_ah: float, efficiency: float, dt_s: float):
        self.soc = float(np.clip(initial_soc, 0.0, 1.0))
        self.capacity_ah = float(capacity_ah)
        self.efficiency = float(efficiency)
        self.dt_s = float(dt_s)

    def step(self, current_a: float) -> float:
        self.soc -= self.efficiency * current_a * self.dt_s / (3600.0 * self.capacity_ah)
        self.soc = float(np.clip(self.soc, 0.0, 1.0))
        return self.soc

    def run(self, current_a: np.ndarray) -> np.ndarray:
        result = np.empty(len(current_a), dtype=float)
        result[0] = self.soc
        for k in range(1, len(current_a)):
            result[k] = self.step(float(current_a[k - 1]))
        return result

