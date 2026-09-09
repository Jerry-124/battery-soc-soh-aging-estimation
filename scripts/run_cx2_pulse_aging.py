from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.calce_cx2 import (
    aggregate_cx2_by_file,
    extract_cx2_pulse_records,
)


def trailing_median(values: np.ndarray, window: int = 3) -> np.ndarray:
    """Causal robust health estimate from the latest diagnostic checkpoints."""
    return np.array(
        [np.median(values[max(0, i - window + 1) : i + 1]) for i in range(len(values))]
    )


def output_directories(output_root: Path) -> dict[str, Path]:
    """Return all CX2 artifacts under the requested output root."""
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


def report_lines(metrics: dict) -> list[str]:
    measured = metrics["measured_health"]
    checkpoint = metrics["observer_checkpoint"]
    dataset = metrics["dataset"]
    return [
        "# CALCE CX2-3 Full-Life Pulse-Aging Validation",
        "",
        "## Scope",
        "",
        (
            "The measured aging pipeline processes the full-life CALCE CX2-3 archive "
            "and retains the complete degradation trajectory, including the abrupt "
            "end-of-life region."
        ),
        "",
        "## Key Results",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| Valid dated exports | {dataset['files_with_valid_cycles']} |",
        f"| Sampled complete diagnostic cycles | {dataset['pulse_cycles_sampled']:,} |",
        f"| Capacity-retention factor, first → last | 1.000 → {measured['final_capacity_factor']:.3f} |",
        f"| 5 s pulse-resistance factor, first → last | 1.000× → {measured['final_resistance_factor']:.3f}× |",
        (
            "| Observer checkpoint capacity-retention factor, measured / estimated | "
            f"{checkpoint['true_capacity_factor']:.3f} / "
            f"{checkpoint['estimated_capacity_factor']:.3f} |"
        ),
        (
            "| Observer checkpoint resistance factor, measured / estimated | "
            f"{checkpoint['true_resistance_factor']:.3f}× / "
            f"{checkpoint['estimated_resistance_factor']:.3f}× |"
        ),
        "",
        "## Interpretation",
        "",
        (
            "Capacity is normalized to the first measured diagnostic value. Pulse "
            "resistance uses the voltage change from the end of a 10-second rest to "
            "the first 5-second sample of the 0.5C discharge pulse, divided by the "
            "measured current step."
        ),
        "",
        (
            "The observer checkpoint is selected near a 0.70 capacity-retention "
            "factor; this ratio is not re-labeled as rated-capacity SOH."
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract full-life 5-second pulse resistance and capacity fade from CALCE CX2-3"
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "data" / "raw" / "calce_cx2" / "CX2_3.complete.zip",
    )
    parser.add_argument("--max-cycles-per-file", type=int, default=25)
    parser.add_argument(
        "--reuse-records",
        action="store_true",
        help="Reuse the processed cx2_pulse_records.csv for this output root",
    )
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    directories = output_directories(args.output_root)
    cached_records = directories["processed"] / "cx2_pulse_records.csv"
    if args.reuse_records and cached_records.exists():
        records = pd.read_csv(cached_records, parse_dates=["timestamp"])
    else:
        records = extract_cx2_pulse_records(args.archive, args.max_cycles_per_file)
    aging = aggregate_cx2_by_file(records)
    cap_estimate = trailing_median(aging["capacity_retention_pct"].to_numpy())
    resistance_estimate = trailing_median(aging["resistance_factor"].to_numpy())
    operational = aging[aging["capacity_retention_pct"].between(65.0, 75.0)]
    target_index = int((operational["capacity_retention_pct"] - 70.0).abs().idxmin())
    true_capacity_factor = float(aging["capacity_retention_pct"].iloc[-1] / 100.0)
    true_resistance_factor = float(aging["resistance_factor"].iloc[-1])
    metrics = {
        "dataset": {
            "publisher": "CALCE, University of Maryland",
            "cell": "CX2-3 LiCoO2 pouch cell",
            "source_url": "https://web.calce.umd.edu/batteries/data/CX2_3.zip",
            "files_with_valid_cycles": len(aging),
            "pulse_cycles_sampled": len(records),
            "first_timestamp": aging["timestamp"].iloc[0].isoformat(),
            "last_timestamp": aging["timestamp"].iloc[-1].isoformat(),
        },
        "measured_health": {
            "initial_capacity_ah": float(aging["capacity_ah"].iloc[0]),
            "final_capacity_ah": float(aging["capacity_ah"].iloc[-1]),
            "final_capacity_factor": true_capacity_factor,
            "initial_5s_pulse_resistance_ohm": float(
                aging["pulse_resistance_ohm"].iloc[0]
            ),
            "final_5s_pulse_resistance_ohm": float(
                aging["pulse_resistance_ohm"].iloc[-1]
            ),
            "final_resistance_factor": true_resistance_factor,
        },
        "estimated_health": {
            "method": "causal trailing median of 3 diagnostic checkpoints",
            "capacity_retention_rmse_pct": float(
                np.sqrt(
                    np.mean(
                        (cap_estimate - aging["capacity_retention_pct"].to_numpy()) ** 2
                    )
                )
            ),
            "resistance_factor_rmse": float(
                np.sqrt(
                    np.mean(
                        (resistance_estimate - aging["resistance_factor"].to_numpy())
                        ** 2
                    )
                )
            ),
        },
        "observer_checkpoint": {
            "timestamp": aging.loc[target_index, "timestamp"].isoformat(),
            "true_capacity_factor": float(
                aging.loc[target_index, "capacity_retention_pct"] / 100.0
            ),
            "true_resistance_factor": float(
                aging.loc[target_index, "resistance_factor"]
            ),
            "estimated_capacity_factor": float(cap_estimate[target_index] / 100.0),
            "estimated_resistance_factor": float(resistance_estimate[target_index]),
        },
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    metrics_path = directories["metrics"] / "cx2_pulse_aging.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    aging.assign(
        capacity_retention_estimate_pct=cap_estimate,
        resistance_factor_estimate=resistance_estimate,
    ).to_csv(directories["processed"] / "cx2_pulse_aging.csv", index=False)
    records.to_csv(directories["processed"] / "cx2_pulse_records.csv", index=False)

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(
        aging["elapsed_days"],
        aging["capacity_retention_pct"],
        "o-",
        ms=3,
        label="Measured median",
    )
    axes[0].plot(
        aging["elapsed_days"], cap_estimate, "--", label="Causal 3-checkpoint estimate"
    )
    axes[0].set_ylabel("Capacity retention [% of initial]")
    axes[0].grid(alpha=0.25)
    axes[0].legend()
    axes[1].plot(
        aging["elapsed_days"],
        aging["resistance_factor"],
        "o-",
        ms=3,
        label="Measured 5 s pulse",
    )
    axes[1].plot(
        aging["elapsed_days"],
        resistance_estimate,
        "--",
        label="Causal 3-checkpoint estimate",
    )
    axes[1].set_ylabel("Resistance factor")
    axes[1].set_xlabel("Elapsed test days")
    axes[1].grid(alpha=0.25)
    axes[1].legend()
    fig.suptitle(
        "CALCE CX2-3 measured capacity retention and 5-second pulse resistance growth"
    )
    fig.tight_layout()
    figure_path = directories["figures"] / "cx2_pulse_aging.png"
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)
    report_path = directories["reports"] / "cx2_pulse_aging.md"
    report_path.write_text("\n".join(report_lines(metrics)), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved {metrics_path}")
    print(f"Saved {figure_path}")
    print(f"Saved {report_path}")


if __name__ == "__main__":
    main()
