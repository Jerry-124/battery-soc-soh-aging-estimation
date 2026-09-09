from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

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


def prediction_errors(
    cycle: np.ndarray,
    soh: np.ndarray,
    degree: int,
    train_fraction: float = 0.6,
) -> np.ndarray:
    split = max(degree + 2, int(len(cycle) * train_fraction))
    x_scale = max(float(cycle[split - 1]), 1.0)
    coefficients = np.polyfit(cycle[:split] / x_scale, soh[:split], degree)
    prediction = np.polyval(coefficients, cycle[split:] / x_scale)
    return prediction - soh[split:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate capacity fade and resistance growth on Oxford measured aging data"
        )
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT
        / "data"
        / "raw"
        / "oxford"
        / "Oxford_Battery_Degradation_Dataset_1.mat",
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    return parser.parse_args()


def output_directories(output_root: Path) -> dict[str, Path]:
    """Return all experiment outputs under one isolated root."""
    processed = (
        ROOT / "data" / "processed"
        if output_root.resolve() == (ROOT / "results").resolve()
        else output_root / "data" / "processed"
    )
    return {
        "metrics": output_root / "metrics",
        "figures": output_root / "figures",
        "reports": output_root / "reports",
        "processed": processed,
    }


def _prediction_summary(trajectories) -> dict[str, float | int]:
    linear_errors = np.concatenate(
        [prediction_errors(t.cycle, t.capacity_retention_pct, 1) for t in trajectories]
    )
    quadratic_errors = np.concatenate(
        [prediction_errors(t.cycle, t.capacity_retention_pct, 2) for t in trajectories]
    )
    return {
        "train_fraction": 0.6,
        "linear_rmse_pct": float(np.sqrt(np.mean(linear_errors**2))),
        "linear_mae_pct": float(np.mean(np.abs(linear_errors))),
        "quadratic_rmse_pct": float(np.sqrt(np.mean(quadratic_errors**2))),
        "quadratic_mae_pct": float(np.mean(np.abs(quadratic_errors))),
        "test_points": len(linear_errors),
    }


def build_metrics(trajectories) -> dict:
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
            "initial_capacity_mah_mean": float(
                np.mean([t.capacity_mah[0] for t in trajectories])
            ),
            "initial_capacity_mah_std": float(
                np.std([t.capacity_mah[0] for t in trajectories])
            ),
            "final_capacity_retention_pct_mean": float(
                np.mean([t.capacity_retention_pct[-1] for t in trajectories])
            ),
            "final_capacity_retention_pct_min": float(
                np.min([t.capacity_retention_pct[-1] for t in trajectories])
            ),
            "final_capacity_retention_pct_max": float(
                np.max([t.capacity_retention_pct[-1] for t in trajectories])
            ),
            "final_rated_capacity_soh_pct_mean": float(
                np.mean([t.rated_capacity_soh_pct[-1] for t in trajectories])
            ),
            "final_rated_capacity_soh_pct_min": float(
                np.min([t.rated_capacity_soh_pct[-1] for t in trajectories])
            ),
            "final_rated_capacity_soh_pct_max": float(
                np.max([t.rated_capacity_soh_pct[-1] for t in trajectories])
            ),
        },
        "resistance": {
            "initial_effective_resistance_ohm_mean": float(
                np.nanmean([t.effective_resistance_ohm[0] for t in trajectories])
            ),
            "final_resistance_factor_mean": float(
                np.nanmean(
                    [
                        t.effective_resistance_ohm[-1] / t.effective_resistance_ohm[0]
                        for t in trajectories
                    ]
                )
            ),
        },
        "holdout_prediction": _prediction_summary(trajectories),
        "cells": {},
    }
    for trajectory in trajectories:
        metrics["cells"][trajectory.cell] = {
            "measurements": len(trajectory.cycle),
            "last_cycle": int(trajectory.cycle[-1]),
            "initial_capacity_mah": float(trajectory.capacity_mah[0]),
            "final_capacity_retention_pct": float(
                trajectory.capacity_retention_pct[-1]
            ),
            "final_rated_capacity_soh_pct": float(
                trajectory.rated_capacity_soh_pct[-1]
            ),
            "final_resistance_factor": float(
                trajectory.effective_resistance_ohm[-1]
                / trajectory.effective_resistance_ohm[0]
            ),
        }
    return metrics


def write_metrics_and_data(
    metrics: dict,
    trajectories,
    directories: dict[str, Path],
) -> None:
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    (directories["metrics"] / "oxford_soh_validation.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    output = directories["processed"] / "oxford_health_trajectories.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "cell",
                "cycle",
                "capacity_mah",
                "capacity_retention_pct",
                "rated_capacity_soh_pct",
                "effective_resistance_ohm",
                "resistance_soh_pct",
            ]
        )
        for trajectory in trajectories:
            writer.writerows(
                zip(
                    [trajectory.cell] * len(trajectory.cycle),
                    trajectory.cycle,
                    trajectory.capacity_mah,
                    trajectory.capacity_retention_pct,
                    trajectory.rated_capacity_soh_pct,
                    trajectory.effective_resistance_ohm,
                    trajectory.resistance_soh_pct,
                    strict=True,
                )
            )


def plot_validation(trajectories, output_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 9), sharex=False)
    for trajectory in trajectories:
        axes[0].plot(
            trajectory.cycle,
            trajectory.capacity_retention_pct,
            marker="o",
            ms=2,
            lw=1,
            label=trajectory.cell,
        )
        resistance_growth = (
            100.0
            * trajectory.effective_resistance_ohm
            / trajectory.effective_resistance_ohm[0]
        )
        axes[1].plot(
            trajectory.cycle,
            resistance_growth,
            marker="o",
            ms=2,
            lw=1,
            label=trajectory.cell,
        )
    axes[0].axhline(80.0, color="black", ls="--", lw=1, label="80% retention")
    axes[0].set_ylabel("Capacity retention [% of initial]")
    axes[0].set_xlabel("Equivalent full cycles")
    axes[0].grid(alpha=0.25)
    axes[0].legend(ncol=3)
    axes[1].set_ylabel("Effective resistance [% of initial]")
    axes[1].set_xlabel("Equivalent full cycles")
    axes[1].grid(alpha=0.25)
    axes[1].legend(ncol=4)
    fig.suptitle("Oxford Battery Degradation Dataset 1 - measured SOH indicators")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def report_lines(metrics: dict) -> list[str]:
    holdout = metrics["holdout_prediction"]
    capacity = metrics["capacity"]
    resistance = metrics["resistance"]
    return [
        "# Oxford Measured Aging Validation",
        "",
        "## Scope",
        "",
        (
            "Eight 740 mAh Kokam pouch cells are evaluated using the Oxford Battery "
            "Degradation Dataset 1. Characterization is performed every 100 cycles at "
            "40 °C."
        ),
        "",
        "## Key Results",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| Mean initial measured capacity | {capacity['initial_capacity_mah_mean']:.2f} mAh |",
        f"| Mean final capacity retention | {capacity['final_capacity_retention_pct_mean']:.2f}% of first measured capacity |",
        f"| Mean final rated-capacity SOH | {capacity['final_rated_capacity_soh_pct_mean']:.2f}% of 740 mAh |",
        f"| Mean final resistance factor | {resistance['final_resistance_factor_mean']:.3f}× |",
        f"| Linear 60/40 holdout RMSE | {holdout['linear_rmse_pct']:.3f} %pt |",
        f"| Quadratic 60/40 holdout RMSE | {holdout['quadratic_rmse_pct']:.3f} %pt |",
        "",
        "## Interpretation",
        "",
        (
            "Capacity retention is normalized by each cell's first measured 1C "
            "discharge capacity. Rated-capacity SOH is calculated separately as "
            "`capacity_mAh / 740 mAh * 100`. Effective resistance is estimated from the "
            "voltage difference between aligned 1C and pseudo-OCV discharge curves over "
            "20–80% depth of discharge."
        ),
        "",
        (
            "The two capacity metrics intentionally use different denominators and are "
            "not treated as interchangeable definitions of SOH."
        ),
    ]


def main() -> None:
    args = parse_args()
    trajectories = [
        load_oxford_health_trajectory(args.data, cell) for cell in range(1, 9)
    ]
    metrics = build_metrics(trajectories)
    directories = output_directories(args.output_root)
    write_metrics_and_data(metrics, trajectories, directories)
    plot_validation(
        trajectories,
        directories["figures"] / "oxford_soh_validation.png",
    )
    (directories["reports"] / "oxford_soh_validation.md").write_text(
        "\n".join(report_lines(metrics)), encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
