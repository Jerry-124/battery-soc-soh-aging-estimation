from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OCVCurve:
    soc: np.ndarray
    voltage_v: np.ndarray
    voltage_bias_v: float = 0.0

    def __call__(self, soc: np.ndarray | float) -> np.ndarray | float:
        z = np.asarray(soc, dtype=float)
        value = (
            np.interp(
                np.clip(z, self.soc[0], self.soc[-1]),
                self.soc,
                self.voltage_v,
            )
            + self.voltage_bias_v
        )
        return float(value) if value.ndim == 0 else value

    def derivative(self, soc: np.ndarray | float) -> np.ndarray | float:
        slopes = np.gradient(self.voltage_v, self.soc)
        # A small positive floor avoids an unobservable/unstable EKF Jacobian.
        slopes = np.maximum(slopes, 0.02)
        z = np.asarray(soc, dtype=float)
        value = np.interp(
            np.clip(z, self.soc[0], self.soc[-1]),
            self.soc,
            slopes,
        )
        return float(value) if value.ndim == 0 else value

    def with_bias(self, voltage_bias_v: float) -> OCVCurve:
        return OCVCurve(
            self.soc.copy(),
            self.voltage_v.copy(),
            float(voltage_bias_v),
        )


@dataclass(frozen=True)
class MeasuredProfile:
    time_s: np.ndarray
    current_a: np.ndarray
    voltage_v: np.ndarray
    reference_soc: np.ndarray
    initial_soc: float
    capacity_ah: float
    source_path: str


def read_arbin_workbook(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    book = pd.ExcelFile(path)
    sheets = [sheet for sheet in book.sheet_names if sheet.lower() != "info"]
    if not sheets:
        raise ValueError(f"No Arbin data sheet found in {path}")
    frames = [pd.read_excel(path, sheet_name=sheet) for sheet in sheets]
    frame = pd.concat(frames, ignore_index=True)
    required = {
        "Data_Point",
        "Test_Time(s)",
        "Step_Index",
        "Cycle_Index",
        "Current(A)",
        "Voltage(V)",
        "Charge_Capacity(Ah)",
        "Discharge_Capacity(Ah)",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing columns in {path}: {sorted(missing)}")
    frame = (
        frame.drop_duplicates(subset="Data_Point")
        .sort_values("Test_Time(s)")
        .reset_index(drop=True)
    )
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["Test_Time(s)", "Current(A)", "Voltage(V)"])


def load_capacity_ah(path: str | Path) -> float:
    data = read_arbin_workbook(path)
    capacity = float(data["Discharge_Capacity(Ah)"].max())
    if capacity <= 0:
        raise ValueError("Measured discharge capacity must be positive")
    return capacity


def _is_discharge_rest(cycle: float, step: float) -> bool:
    return bool(
        (step == 4 and cycle == 1)
        or step == 6
        or (step == 8 and cycle == 10)
    )


def _relaxed_ocv_point(
    group: pd.DataFrame,
    *,
    cycle: float,
    step: float,
    capacity_ah: float,
) -> tuple[float, float] | None:
    if not _is_discharge_rest(cycle, step):
        return None
    duration = float(
        group["Test_Time(s)"].iloc[-1] - group["Test_Time(s)"].iloc[0]
    )
    current_mean = float(group["Current(A)"].abs().mean())
    if duration <= 1000.0 or current_mean >= 1e-3:
        return None
    discharged = float(group["Discharge_Capacity(Ah)"].iloc[-1])
    soc = float(np.clip(1.0 - discharged / capacity_ah, 0.0, 1.0))
    voltage = float(group["Voltage(V)"].tail(min(60, len(group))).median())
    return soc, voltage


def _collect_relaxed_ocv_points(
    data: pd.DataFrame,
    capacity_ah: float,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    groups = data.groupby(["Cycle_Index", "Step_Index"], sort=False)
    for (cycle, step), group in groups:
        point = _relaxed_ocv_point(
            group,
            cycle=float(cycle),
            step=float(step),
            capacity_ah=capacity_ah,
        )
        if point is not None:
            points.append(point)
    return points


def _build_ocv_curve(points: list[tuple[float, float]]) -> OCVCurve:
    if len(points) < 8:
        raise ValueError(
            f"Expected at least 8 relaxed discharge OCV points, found {len(points)}"
        )
    ordered = sorted(points)
    soc = np.array([point[0] for point in ordered])
    voltage = np.array([point[1] for point in ordered])
    unique_soc, unique_index = np.unique(soc, return_index=True)
    voltage = voltage[unique_index]
    # Measurement noise can create tiny non-monotonic steps; enforce the physical trend.
    voltage = np.maximum.accumulate(voltage)
    return OCVCurve(unique_soc, voltage)


def load_incremental_ocv_curve(path: str | Path) -> OCVCurve:
    """Extract discharge-side relaxed OCV points from the CALCE incremental OCV test."""
    data = read_arbin_workbook(path)
    capacity = float(data["Discharge_Capacity(Ah)"].max())
    points = _collect_relaxed_ocv_points(data, capacity)
    return _build_ocv_curve(points)


def load_dynamic_profile(
    path: str | Path,
    capacity_ah: float,
    dt_s: float = 1.0,
) -> MeasuredProfile:
    """Load the dynamic portion (step 7 onward) and construct a Coulomb-integrated SOC reference."""
    data = read_arbin_workbook(path)
    dynamic_rows = data.index[data["Step_Index"] == 7]
    if len(dynamic_rows) == 0:
        raise ValueError(f"No dynamic step 7 found in {path}")
    start_index = int(dynamic_rows[0])
    start_time = float(data.loc[start_index, "Test_Time(s)"])
    end_time = float(data["Test_Time(s)"].max())
    before = data.loc[: start_index - 1]
    pre_discharge = float(before["Discharge_Capacity(Ah)"].max())
    # The test is fully charged before a controlled pre-discharge. Ignore the initial
    # full-charge counter and use only charge accumulated after dynamic testing begins.
    initial_soc = float(np.clip(1.0 - pre_discharge / capacity_ah, 0.0, 1.0))
    dynamic = data.loc[start_index:].copy()
    source_time = dynamic["Test_Time(s)"].to_numpy(float)
    grid = np.arange(start_time, end_time + 0.5 * dt_s, dt_s)
    arbin_current = np.interp(
        grid,
        source_time,
        dynamic["Current(A)"].to_numpy(float),
    )
    current = -arbin_current  # CALCE/Arbin: positive charge; model: positive discharge.
    voltage = np.interp(
        grid,
        source_time,
        dynamic["Voltage(V)"].to_numpy(float),
    )
    soc = np.empty(len(grid), dtype=float)
    soc[0] = initial_soc
    for k in range(1, len(grid)):
        soc[k] = soc[k - 1] - current[k - 1] * dt_s / (3600.0 * capacity_ah)
    soc = np.clip(soc, 0.0, 1.0)
    return MeasuredProfile(
        time_s=grid - grid[0],
        current_a=current,
        voltage_v=voltage,
        reference_soc=soc,
        initial_soc=initial_soc,
        capacity_ah=capacity_ah,
        source_path=str(Path(path)),
    )
