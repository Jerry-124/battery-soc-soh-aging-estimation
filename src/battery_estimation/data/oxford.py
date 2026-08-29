from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import numpy as np


@dataclass(frozen=True)
class OxfordHealthTrajectory:
    cell: str
    cycle: np.ndarray
    capacity_mah: np.ndarray
    capacity_soh_pct: np.ndarray
    effective_resistance_ohm: np.ndarray
    resistance_soh_pct: np.ndarray


def _median_current_a(segment: dict) -> float:
    time_days = np.asarray(segment["t"], dtype=float).reshape(-1)
    charge_mah = np.asarray(segment["q"], dtype=float).reshape(-1)
    dt_hours = np.diff(time_days) * 24.0
    dq_ah = np.diff(charge_mah) / 1000.0
    valid = np.abs(dt_hours) > 1e-10
    current = dq_ah[valid] / dt_hours[valid]
    current = current[np.isfinite(current)]
    if len(current) == 0:
        raise ValueError("Cannot derive current from time/charge arrays")
    return float(np.median(current))


def effective_resistance_from_segments(c1_discharge: dict, ocv_discharge: dict) -> float:
    """Estimate mid-SOC effective resistance from 1C and pseudo-OCV discharge curves."""
    q_load = np.abs(np.asarray(c1_discharge["q"], dtype=float).reshape(-1))
    v_load = np.asarray(c1_discharge["v"], dtype=float).reshape(-1)
    q_ocv = np.abs(np.asarray(ocv_discharge["q"], dtype=float).reshape(-1))
    v_ocv = np.asarray(ocv_discharge["v"], dtype=float).reshape(-1)
    if q_load.max() <= 0 or q_ocv.max() <= 0:
        raise ValueError("Discharge capacity must be positive")
    dod_load = q_load / q_load.max()
    dod_ocv = q_ocv / q_ocv.max()
    order = np.argsort(dod_ocv)
    v_ocv_at_load = np.interp(dod_load, dod_ocv[order], v_ocv[order])
    current_delta = abs(_median_current_a(c1_discharge) - _median_current_a(ocv_discharge))
    if current_delta < 0.05:
        raise ValueError("Current difference is too small for resistance estimation")
    region = (dod_load >= 0.2) & (dod_load <= 0.8) & np.isfinite(v_load) & np.isfinite(v_ocv_at_load)
    resistance = (v_ocv_at_load[region] - v_load[region]) / current_delta
    resistance = resistance[(resistance > 0.0) & (resistance < 1.0)]
    if len(resistance) < 20:
        raise ValueError("Insufficient valid points for effective resistance estimation")
    return float(np.median(resistance))


def load_oxford_health_trajectory(path: str | Path, cell_number: int) -> OxfordHealthTrajectory:
    if not 1 <= cell_number <= 8:
        raise ValueError("cell_number must be between 1 and 8")
    # The current Windows environment can over-subscribe BLAS threads during SciPy import.
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    from scipy.io import loadmat

    cell_name = f"Cell{cell_number}"
    cell = loadmat(Path(path), variable_names=[cell_name], simplify_cells=True)[cell_name]
    cycles: list[int] = []
    capacities: list[float] = []
    resistances: list[float] = []
    for key, characterization in cell.items():
        match = re.fullmatch(r"cyc(\d+)", key)
        if match is None or "C1dc" not in characterization or "OCVdc" not in characterization:
            continue
        c1_discharge = characterization["C1dc"]
        capacity = float(abs(np.nanmin(np.asarray(c1_discharge["q"], dtype=float))))
        if not np.isfinite(capacity) or capacity <= 0:
            continue
        try:
            resistance = effective_resistance_from_segments(c1_discharge, characterization["OCVdc"])
        except ValueError:
            resistance = float("nan")
        cycles.append(int(match.group(1)))
        capacities.append(capacity)
        resistances.append(resistance)
    order = np.argsort(cycles)
    cycle = np.asarray(cycles, dtype=int)[order]
    capacity_mah = np.asarray(capacities, dtype=float)[order]
    resistance = np.asarray(resistances, dtype=float)[order]
    capacity_soh = 100.0 * capacity_mah / capacity_mah[0]
    first_valid_resistance = resistance[np.isfinite(resistance)][0]
    resistance_soh = 100.0 * first_valid_resistance / resistance
    return OxfordHealthTrajectory(
        cell=cell_name,
        cycle=cycle,
        capacity_mah=capacity_mah,
        capacity_soh_pct=capacity_soh,
        effective_resistance_ohm=resistance,
        resistance_soh_pct=resistance_soh,
    )

