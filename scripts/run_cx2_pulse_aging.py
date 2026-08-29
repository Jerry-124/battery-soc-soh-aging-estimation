from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.calce_cx2 import aggregate_cx2_by_file, extract_cx2_pulse_records


def trailing_median(values: np.ndarray, window: int = 3) -> np.ndarray:
    """Causal robust health estimate from the latest diagnostic checkpoints."""
    return np.array([np.median(values[max(0, i - window + 1) : i + 1]) for i in range(len(values))])


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract full-life 5-second pulse resistance and capacity fade from CALCE CX2-3")
    parser.add_argument("--archive", type=Path, default=ROOT / "data" / "raw" / "calce_cx2" / "CX2_3.complete.zip")
    parser.add_argument("--max-cycles-per-file", type=int, default=25)
    parser.add_argument("--reuse-records", action="store_true", help="Reuse data/processed/cx2_pulse_records.csv")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    cached_records = ROOT / "data" / "processed" / "cx2_pulse_records.csv"
    if args.reuse_records and cached_records.exists():
        records = pd.read_csv(cached_records, parse_dates=["timestamp"])
    else:
        records = extract_cx2_pulse_records(args.archive, args.max_cycles_per_file)
    aging = aggregate_cx2_by_file(records)
    cap_estimate = trailing_median(aging["capacity_soh_pct"].to_numpy())
    resistance_estimate = trailing_median(aging["resistance_factor"].to_numpy())
    operational = aging[aging["capacity_soh_pct"].between(65.0, 75.0)]
    target_index = int((operational["capacity_soh_pct"] - 70.0).abs().idxmin())
    true_capacity_factor = float(aging["capacity_soh_pct"].iloc[-1] / 100.0)
    true_resistance_factor = float(aging["resistance_factor"].iloc[-1])
    metrics = {
        "dataset": {
            "publisher": "CALCE, University of Maryland",
            "cell": "CX2-3 LiCoO2 pouch cell",
            "source_url": "https://web.calce.umd.edu/batteries/data/CX2_3.zip",
            "files_with_valid_cycles": int(len(aging)),
            "pulse_cycles_sampled": int(len(records)),
            "first_timestamp": aging["timestamp"].iloc[0].isoformat(),
            "last_timestamp": aging["timestamp"].iloc[-1].isoformat(),
        },
        "measured_health": {
            "initial_capacity_ah": float(aging["capacity_ah"].iloc[0]),
            "final_capacity_ah": float(aging["capacity_ah"].iloc[-1]),
            "final_capacity_factor": true_capacity_factor,
            "initial_5s_pulse_resistance_ohm": float(aging["pulse_resistance_ohm"].iloc[0]),
            "final_5s_pulse_resistance_ohm": float(aging["pulse_resistance_ohm"].iloc[-1]),
            "final_resistance_factor": true_resistance_factor,
        },
        "estimated_health": {
            "method": "causal trailing median of 3 diagnostic checkpoints",
            "capacity_rmse_pct": float(np.sqrt(np.mean((cap_estimate - aging["capacity_soh_pct"].to_numpy()) ** 2))),
            "resistance_factor_rmse": float(np.sqrt(np.mean((resistance_estimate - aging["resistance_factor"].to_numpy()) ** 2))),
        },
        "observer_checkpoint": {
            "timestamp": aging.loc[target_index, "timestamp"].isoformat(),
            "true_capacity_factor": float(aging.loc[target_index, "capacity_soh_pct"] / 100.0),
            "true_resistance_factor": float(aging.loc[target_index, "resistance_factor"]),
            "estimated_capacity_factor": float(cap_estimate[target_index] / 100.0),
            "estimated_resistance_factor": float(resistance_estimate[target_index]),
        },
    }
    metrics_dir = args.output_root / "metrics"
    figures_dir = args.output_root / "figures"
    reports_dir = args.output_root / "reports"
    processed_dir = ROOT / "data" / "processed"
    for directory in (metrics_dir, figures_dir, reports_dir, processed_dir):
        directory.mkdir(parents=True, exist_ok=True)
    metrics_path = metrics_dir / "cx2_pulse_aging.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    aging.assign(
        capacity_soh_estimate_pct=cap_estimate,
        resistance_factor_estimate=resistance_estimate,
    ).to_csv(processed_dir / "cx2_pulse_aging.csv", index=False)
    records.to_csv(processed_dir / "cx2_pulse_records.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(aging["elapsed_days"], aging["capacity_soh_pct"], "o-", ms=3, label="Measured median")
    axes[0].plot(aging["elapsed_days"], cap_estimate, "--", label="Causal 3-checkpoint estimate")
    axes[0].set_ylabel("Capacity SOH [%]")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(aging["elapsed_days"], aging["resistance_factor"], "o-", ms=3, label="Measured 5 s pulse")
    axes[1].plot(aging["elapsed_days"], resistance_estimate, "--", label="Causal 3-checkpoint estimate")
    axes[1].set_ylabel("Resistance factor")
    axes[1].set_xlabel("Elapsed test days")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.suptitle("CALCE CX2-3 measured capacity fade and 5-second pulse resistance growth")
    fig.tight_layout()
    figure_path = figures_dir / "cx2_pulse_aging.png"
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)
    report = [
        "# CALCE CX2-3 Pulse Aging Validation",
        "",
        f"- Valid date exports: {len(aging)}",
        f"- Sampled complete pulse cycles: {len(records)}",
        f"- Capacity factor, first to last: 1.000 to {true_capacity_factor:.3f}",
        f"- 5 s pulse resistance factor, first to last: 1.000 to {true_resistance_factor:.3f}",
        f"- Observer checkpoint capacity factor (true / estimated): {metrics['observer_checkpoint']['true_capacity_factor']:.3f} / {metrics['observer_checkpoint']['estimated_capacity_factor']:.3f}",
        f"- Observer checkpoint resistance factor (true / estimated): {metrics['observer_checkpoint']['true_resistance_factor']:.3f} / {metrics['observer_checkpoint']['estimated_resistance_factor']:.3f}",
        "",
        "Pulse resistance uses the voltage change from a 10-second rest to the first 5-second sample of the 0.5C discharge pulse.",
        "",
    ]
    (reports_dir / "cx2_pulse_aging.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved {metrics_path}")
    print(f"Saved {figure_path}")


if __name__ == "__main__":
    main()
