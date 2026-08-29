from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from battery_estimation.models.ecm import ECMParameters, SecondOrderThevenin


@dataclass
class SyntheticDataset:
    time_s: np.ndarray
    current_a: np.ndarray
    voltage_v: np.ndarray
    true_soc: np.ndarray
    clean_voltage_v: np.ndarray
    capacity_ah: float
    resistance_factor: float


def generate_dynamic_current(n_steps: int, dt_s: float, seed: int) -> np.ndarray:
    """Create a deterministic mixed pulse/drive current profile."""
    rng = np.random.default_rng(seed)
    current = np.zeros(n_steps, dtype=float)
    levels = np.array([-1.8, -0.8, 0.0, 0.7, 1.3, 2.1, 2.8])
    cursor = 0
    while cursor < n_steps:
        width = int(rng.integers(max(4, int(8 / dt_s)), max(8, int(45 / dt_s))))
        level = float(rng.choice(levels, p=[0.05, 0.06, 0.15, 0.18, 0.23, 0.20, 0.13]))
        end = min(n_steps, cursor + width)
        current[cursor:end] = level
        cursor = end
    t = np.arange(n_steps) * dt_s
    current += 0.18 * np.sin(2 * np.pi * t / 73.0) + 0.08 * np.sin(2 * np.pi * t / 19.0)
    return current


def simulate_dataset(
    params: ECMParameters,
    dt_s: float,
    duration_s: float,
    initial_soc: float,
    voltage_noise_std_v: float,
    current_noise_std_a: float,
    current_bias_a: float,
    seed: int,
    resistance_factor: float = 1.0,
) -> SyntheticDataset:
    n_steps = int(duration_s / dt_s) + 1
    rng = np.random.default_rng(seed)
    true_current = generate_dynamic_current(n_steps, dt_s, seed)
    measured_current = true_current + current_bias_a + rng.normal(0.0, current_noise_std_a, n_steps)
    model = SecondOrderThevenin(params, dt_s)
    state = np.array([initial_soc, 0.0, 0.0], dtype=float)
    soc = np.empty(n_steps)
    clean_voltage = np.empty(n_steps)
    for k in range(n_steps):
        soc[k] = state[0]
        clean_voltage[k] = model.terminal_voltage(state, true_current[k])
        if k + 1 < n_steps:
            state = model.transition(state, true_current[k])
    measured_voltage = clean_voltage + rng.normal(0.0, voltage_noise_std_v, n_steps)
    return SyntheticDataset(
        time_s=np.arange(n_steps, dtype=float) * dt_s,
        current_a=measured_current,
        voltage_v=measured_voltage,
        true_soc=soc,
        clean_voltage_v=clean_voltage,
        capacity_ah=params.capacity_ah,
        resistance_factor=resistance_factor,
    )

