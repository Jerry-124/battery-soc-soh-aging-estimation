from __future__ import annotations

from datetime import datetime

import pytest

from battery_estimation.data.calce_cx2 import _process_cycle


def _row(
    step: int,
    *,
    current: float,
    voltage: float,
    discharge_capacity: float,
    timestamp: str = "2026-01-02 03:04:05",
) -> dict:
    return {
        "Date_Time": timestamp,
        "Step_Time(s)": 0.0,
        "Step_Index": step,
        "Cycle_Index": 1,
        "Current(A)": current,
        "Voltage(V)": voltage,
        "Discharge_Capacity(Ah)": discharge_capacity,
    }


def _valid_cycle() -> list[dict]:
    return [
        _row(4, current=0.0, voltage=4.1, discharge_capacity=0.10),
        _row(5, current=-1.0, voltage=3.5, discharge_capacity=1.10),
        _row(8, current=0.0, voltage=3.90, discharge_capacity=1.10),
        _row(9, current=-0.5, voltage=3.85, discharge_capacity=1.10),
        _row(9, current=-0.5, voltage=3.84, discharge_capacity=1.10),
        _row(10, current=-1.0, voltage=3.80, discharge_capacity=1.10),
    ]


def test_process_cycle_preserves_capacity_resistance_and_timestamp_semantics() -> None:
    record = _process_cycle(_valid_cycle(), "sample.xlsx")

    assert record is not None
    assert record.source_file == "sample.xlsx"
    assert record.timestamp == datetime(2026, 1, 2, 3, 4, 5)  # noqa: DTZ001
    assert record.capacity_ah == pytest.approx(1.0)
    assert record.rest_to_half_c_resistance_ohm == pytest.approx(0.10)
    assert record.half_c_to_one_c_resistance_ohm == pytest.approx(0.08)


def test_process_cycle_rejects_missing_required_step() -> None:
    rows = [row for row in _valid_cycle() if row["Step_Index"] != 10]

    assert _process_cycle(rows, "sample.xlsx") is None


def test_process_cycle_rejects_too_small_current_step() -> None:
    rows = _valid_cycle()
    rows[-1]["Current(A)"] = -0.55

    assert _process_cycle(rows, "sample.xlsx") is None
