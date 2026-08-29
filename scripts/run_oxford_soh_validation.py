from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.oxford import load_oxford_health_trajectory


def prediction_errors(cycle: np.ndarray, soh: np.ndarray, degree: int, train_fraction: float = 0.6) -> np.ndarray:
    split = max(degree + 2, int(len(cycle) * train_fraction))
    x_scale = max(float(cycle[split - 1]), 1.0)
    coefficients = np.polyfit(cycle[:split] / x_scale, soh[:split], degree)
    prediction = np.polyval(coefficients, cycle[split:] / x_scale)
    return prediction - soh[split:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate capacity fade and resistance growth on Oxford measured aging data")
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "raw" / "oxford" / "Oxford_Battery_Degradation_Dataset_1.mat")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    trajectories = [load_oxford_health_trajectory(args.data, cell) for cell in range(1, 9)]

    linear_errors = np.concatenate([prediction_errors(t.cycle, t.capacity_soh_pct, 1) for t in trajectories])
    quadratic_errors = np.concatenate([prediction_errors(t.cycle, t.capacity_soh_pct, 2) for t in trajectories])
    metrics = {
        "dataset": {
            "publisher": "University of Oxford",
            "doi": "10.5287/bodleian:KO2kdmYGg",
            "cells": 8,
            "rated_capacity_mah": 740,
            "temperature_c": 40,
            "characterization_interval_cycles": 100,
        },
        "capacity": {
            "initial_capacity_mah_mean": float(np.mean([t.capacity_mah[0] for t in trajectories])),
            "initial_capacity_mah_std": float(np.std([t.capacity_mah[0] for t in trajectories])),
            "final_soh_pct_mean": float(np.mean([t.capacity_soh_pct[-1] for t in trajectories])),
            "final_soh_pct_min": float(np.min([t.capacity_soh_pct[-1] for t in trajectories])),
            "final_soh_pct_max": float(np.max([t.capacity_soh_pct[-1] for t in trajectories])),
        },
        "resistance": {
            "initial_effective_resistance_ohm_mean": float(np.nanmean([t.effective_resistance_ohm[0] for t in trajectories])),
            "final_resistance_factor_mean": float(np.nanmean([t.effective_resistance_ohm[-1] / t.effective_resistance_ohm[0] for t in trajectories])),
        },
        "holdout_prediction": {
            "train_fraction": 0.6,
            "linear_rmse_pct": float(np.sqrt(np.mean(linear_errors**2))),
            "linear_mae_pct": float(np.mean(np.abs(linear_errors))),
            "quadratic_rmse_pct": float(np.sqrt(np.mean(quadratic_errors**2))),
            "quadratic_mae_pct": float(np.mean(np.abs(quadratic_errors))),
            "test_points": int(len(linear_errors)),
        },
        "cells": {},
    }
    for trajectory in trajectories:
        metrics["cells"][trajectory.cell] = {
            "measurements": int(len(trajectory.cycle)),
            "last_cycle": int(trajectory.cycle[-1]),
            "initial_capacity_mah": float(trajectory.capacity_mah[0]),
            "final_capacity_soh_pct": float(trajectory.capacity_soh_pct[-1]),
            "final_resistance_factor": float(trajectory.effective_resistance_ohm[-1] / trajectory.effective_resistance_ohm[0]),
        }

    metrics_dir = args.output_root / "metrics"
    figures_dir = args.output_root / "figures"
    reports_dir = args.output_root / "reports"
    processed_dir = ROOT / "data" / "processed"
    for directory in (metrics_dir, figures_dir, reports_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (metrics_dir / "oxford_soh_validation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (processed_dir / "oxford_health_trajectories.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cell", "cycle", "capacity_mah", "capacity_soh_pct", "effective_resistance_ohm", "resistance_soh_pct"])
        for t in trajectories:
            writer.writerows(zip([t.cell] * len(t.cycle), t.cycle, t.capacity_mah, t.capacity_soh_pct, t.effective_resistance_ohm, t.resistance_soh_pct))

    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=False)
    for t in trajectories:
        axes[0].plot(t.cycle, t.capacity_soh_pct, marker="o", ms=2, lw=1, label=t.cell)
        resistance_growth = 100.0 * t.effective_resistance_ohm / t.effective_resistance_ohm[0]
        axes[1].plot(t.cycle, resistance_growth, marker="o", ms=2, lw=1, label=t.cell)
    axes[0].axhline(80.0, color="black", ls="--", lw=1, label="80% SOH")
    axes[0].set_ylabel("Capacity SOH [%]")
    axes[0].set_xlabel("Equivalent full cycles")
    axes[0].grid(alpha=0.25)
    axes[0].legend(ncol=3)
    axes[1].set_ylabel("Effective resistance [% of initial]")
    axes[1].set_xlabel("Equivalent full cycles")
    axes[1].grid(alpha=0.25)
    axes[1].legend(ncol=4)
    fig.suptitle("Oxford Battery Degradation Dataset 1 - measured SOH indicators")
    fig.tight_layout()
    fig.savefig(figures_dir / "oxford_soh_validation.png", dpi=160)
    plt.close(fig)

    h = metrics["holdout_prediction"]
    lines = [
        "# Oxford Measured SOH Validation",
        "",
        "Eight 740 mAh pouch cells, characterized every 100 cycles at 40 C.",
        "",
        f"- Mean initial measured capacity: {metrics['capacity']['initial_capacity_mah_mean']:.2f} mAh",
        f"- Mean final capacity SOH: {metrics['capacity']['final_soh_pct_mean']:.2f}%",
        f"- Mean final resistance factor: {metrics['resistance']['final_resistance_factor_mean']:.3f}x",
        f"- Linear 60/40 holdout RMSE: {h['linear_rmse_pct']:.3f} percentage points",
        f"- Quadratic 60/40 holdout RMSE: {h['quadratic_rmse_pct']:.3f} percentage points",
        "",
        "Capacity is measured from the 1C discharge characterization. Effective resistance is estimated from the voltage difference between aligned 1C and pseudo-OCV discharge curves over 20-80% depth of discharge.",
        "",
    ]
    (reports_dir / "oxford_soh_validation.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()

