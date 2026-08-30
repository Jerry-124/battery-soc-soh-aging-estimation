from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pandas as pd

from battery_estimation.data import calce


def _synthetic_relaxation_data() -> pd.DataFrame:
    rows: list[dict[str, float]] = []
    for index in range(8):
        cycle = float(index + 1)
        discharged = 0.2 * index
        voltage = 4.20 - 0.14 * index
        if index == 4:
            voltage += 0.03  # small measurement bump should be made monotonic after sorting
        start = 2000.0 * index
        for offset in (0.0, 1201.0):
            rows.append(
                {
                    "Cycle_Index": cycle,
                    "Step_Index": 6.0,
                    "Test_Time(s)": start + offset,
                    "Current(A)": 0.0,
                    "Voltage(V)": voltage,
                    "Discharge_Capacity(Ah)": discharged,
                }
            )
    return pd.DataFrame(rows)


def test_incremental_ocv_refactor_preserves_relaxed_point_extraction() -> None:
    data = _synthetic_relaxation_data()

    with patch.object(calce, "read_arbin_workbook", return_value=data):
        curve = calce.load_incremental_ocv_curve("ignored.xlsx")

    assert len(curve.soc) == 8
    assert np.all(np.diff(curve.soc) > 0.0)
    assert np.all(np.diff(curve.voltage_v) >= 0.0)
    assert curve.soc[0] == 0.0
    assert curve.soc[-1] == 1.0


def test_relaxed_ocv_point_rejects_short_or_loaded_rest() -> None:
    short = pd.DataFrame(
        {
            "Test_Time(s)": [0.0, 100.0],
            "Current(A)": [0.0, 0.0],
            "Voltage(V)": [4.0, 4.0],
            "Discharge_Capacity(Ah)": [0.2, 0.2],
        }
    )
    loaded = short.copy()
    loaded["Test_Time(s)"] = [0.0, 1201.0]
    loaded["Current(A)"] = [0.01, 0.01]

    assert calce._relaxed_ocv_point(short, cycle=2.0, step=6.0, capacity_ah=1.4) is None
    assert calce._relaxed_ocv_point(loaded, cycle=2.0, step=6.0, capacity_ah=1.4) is None
