from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
from openpyxl import load_workbook


@dataclass(frozen=True)
class CX2PulseRecord:
    source_file: str
    timestamp: datetime
    capacity_ah: float
    rest_to_half_c_resistance_ohm: float
    half_c_to_one_c_resistance_ohm: float


REQUIRED_COLUMNS = [
    "Date_Time",
    "Step_Time(s)",
    "Step_Index",
    "Cycle_Index",
    "Current(A)",
    "Voltage(V)",
    "Discharge_Capacity(Ah)",
]


def _process_cycle(rows: list[dict], source_file: str) -> CX2PulseRecord | None:
    by_step: dict[int, list[dict]] = {}
    for row in rows:
        try:
            by_step.setdefault(int(row["Step_Index"]), []).append(row)
        except (TypeError, ValueError):
            continue
    if not all(step in by_step for step in (4, 5, 8, 9, 10)):
        return None
    rest_before_discharge = by_step[4][-1]
    full_discharge_end = by_step[5][-1]
    pulse_rest = by_step[8][-1]
    half_c_first = by_step[9][0]
    half_c_last = by_step[9][-1]
    one_c_first = by_step[10][0]
    capacity = float(full_discharge_end["Discharge_Capacity(Ah)"] - rest_before_discharge["Discharge_Capacity(Ah)"])
    delta_i_rest = abs(float(half_c_first["Current(A)"]) - float(pulse_rest["Current(A)"]))
    delta_i_step = abs(float(one_c_first["Current(A)"]) - float(half_c_last["Current(A)"]))
    if delta_i_rest < 0.1 or delta_i_step < 0.1:
        return None
    rest_resistance = (float(pulse_rest["Voltage(V)"]) - float(half_c_first["Voltage(V)"])) / delta_i_rest
    step_resistance = (float(half_c_last["Voltage(V)"]) - float(one_c_first["Voltage(V)"])) / delta_i_step
    timestamp = half_c_first["Date_Time"]
    if not isinstance(timestamp, datetime):
        timestamp = pd.to_datetime(timestamp).to_pydatetime()
    if not (0.01 <= capacity <= 2.0 and 0.005 <= rest_resistance <= 1.0 and 0.005 <= step_resistance <= 1.0):
        return None
    return CX2PulseRecord(source_file, timestamp, capacity, rest_resistance, step_resistance)


def _records_from_xlsx(payload: bytes, source_file: str, max_cycles: int) -> list[CX2PulseRecord]:
    workbook = load_workbook(BytesIO(payload), read_only=True, data_only=True)
    sheets = [sheet for sheet in workbook.worksheets if sheet.title.lower() != "info"]
    if not sheets:
        workbook.close()
        return []
    sheet = sheets[0]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows)
    index = {str(name): i for i, name in enumerate(header) if name is not None}
    if any(column not in index for column in REQUIRED_COLUMNS):
        workbook.close()
        return []
    records: list[CX2PulseRecord] = []
    current_cycle = None
    cycle_rows: list[dict] = []
    for values in rows:
        cycle = values[index["Cycle_Index"]]
        if cycle is None:
            continue
        if current_cycle is None:
            current_cycle = cycle
        if cycle != current_cycle:
            record = _process_cycle(cycle_rows, source_file)
            if record is not None:
                records.append(record)
                if len(records) >= max_cycles:
                    break
            cycle_rows = []
            current_cycle = cycle
        cycle_rows.append({column: values[index[column]] for column in REQUIRED_COLUMNS})
    if len(records) < max_cycles and cycle_rows:
        record = _process_cycle(cycle_rows, source_file)
        if record is not None:
            records.append(record)
    workbook.close()
    return records


def extract_cx2_pulse_records(archive_path: str | Path, max_cycles_per_file: int = 25) -> pd.DataFrame:
    """Read representative complete pulse cycles from every XLSX export in the CX2-3 archive."""
    records: list[CX2PulseRecord] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".xlsx"))
        for name in names:
            records.extend(_records_from_xlsx(archive.read(name), name, max_cycles_per_file))
    if not records:
        raise ValueError("No complete CX2 pulse cycles were extracted")
    frame = pd.DataFrame([record.__dict__ for record in records])
    frame = frame.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
    return frame


def aggregate_cx2_by_file(records: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        records.groupby("source_file", as_index=False)
        .agg(
            timestamp=("timestamp", "median"),
            cycles_sampled=("capacity_ah", "size"),
            capacity_ah=("capacity_ah", "median"),
            pulse_resistance_ohm=("rest_to_half_c_resistance_ohm", "median"),
            incremental_resistance_ohm=("half_c_to_one_c_resistance_ohm", "median"),
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    grouped["elapsed_days"] = (grouped["timestamp"] - grouped["timestamp"].iloc[0]).dt.total_seconds() / 86400.0
    grouped["capacity_soh_pct"] = 100.0 * grouped["capacity_ah"] / grouped["capacity_ah"].iloc[0]
    grouped["resistance_factor"] = grouped["pulse_resistance_ohm"] / grouped["pulse_resistance_ohm"].iloc[0]
    return grouped
