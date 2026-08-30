from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from battery_estimation.data.synthetic import simulate_dataset
from battery_estimation.evaluation import calculate_metrics
from battery_estimation.health import (
    perturb_parameters,
    pulse_anchored_fresh_parameters,
    run_kalman_observers,
)

OBSERVERS = ("ekf", "ukf")
CATEGORIES = ("initial_soc_error", "measurement_noise", "parameter_uncertainty")
UNCERTAINTY_LEVELS = (0.8, 0.9, 1.0, 1.1, 1.2)
NOISE_CASES = (
    ("low", 0.002, 0.005),
    ("nominal", 0.005, 0.015),
    ("high", 0.010, 0.030),
    ("severe", 0.020, 0.060),
)


def score(
    rows,
    category,
    level,
    observer_params,
    true_params,
    initial_soc,
    voltage_noise,
    current_noise,
    seed=512,
):
    data = simulate_dataset(
        true_params,
        1.0,
        1800.0,
        0.85,
        voltage_noise,
        current_noise,
        0.0,
        seed,
    )
    estimates = run_kalman_observers(
        observer_params,
        1.0,
        data.current_a,
        data.voltage_v,
        initial_soc,
        voltage_noise,
    )
    for method, estimate in estimates.items():
        full = calculate_metrics(data.true_soc, estimate, 1.0)
        settled = calculate_metrics(data.true_soc[300:], estimate[300:], 1.0)
        rows.append(
            {
                "category": category,
                "level": level,
                "observer": method,
                "rmse_pct": full["rmse_pct"],
                "post_300s_rmse_pct": settled["rmse_pct"],
                "max_error_pct": full["max_error_pct"],
            }
        )


def _load_checkpoint_parameters():
    health = json.loads(
        (ROOT / "results/metrics/cx2_pulse_aging.json").read_text(encoding="utf-8")
    )
    measured = health["measured_health"]
    checkpoint = health["observer_checkpoint"]
    fresh = pulse_anchored_fresh_parameters(
        measured["initial_capacity_ah"],
        measured["initial_5s_pulse_resistance_ohm"],
    )
    true_params = fresh.aged(
        checkpoint["true_capacity_factor"],
        checkpoint["true_resistance_factor"],
    )
    estimated_params = fresh.aged(
        checkpoint["estimated_capacity_factor"],
        checkpoint["estimated_resistance_factor"],
    )
    return true_params, estimated_params


def _run_initial_soc_sweep(rows, estimated_params, true_params) -> None:
    for error in (-0.20, -0.10, 0.0, 0.10, 0.20):
        score(
            rows,
            "initial_soc_error",
            f"{error:+.2f}",
            estimated_params,
            true_params,
            np.clip(0.85 + error, 0, 1),
            0.005,
            0.015,
        )


def _run_noise_sweep(rows, estimated_params, true_params) -> None:
    for name, voltage_noise, current_noise in NOISE_CASES:
        score(
            rows,
            "measurement_noise",
            name,
            estimated_params,
            true_params,
            0.75,
            voltage_noise,
            current_noise,
        )


def _run_parameter_sweep(rows, true_params) -> None:
    for capacity_multiplier in UNCERTAINTY_LEVELS:
        for resistance_multiplier in UNCERTAINTY_LEVELS:
            observer_params = perturb_parameters(
                true_params,
                capacity_multiplier,
                resistance_multiplier,
            )
            score(
                rows,
                "parameter_uncertainty",
                f"C={capacity_multiplier:.1f},R={resistance_multiplier:.1f}",
                observer_params,
                true_params,
                0.75,
                0.005,
                0.015,
            )


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _observer_summary(rows: list[dict], category: str, observer: str) -> dict[str, float]:
    values = [
        row["post_300s_rmse_pct"]
        for row in rows
        if row["category"] == category and row["observer"] == observer
    ]
    return {
        "mean_post_300s_rmse_pct": float(np.mean(values)),
        "worst_post_300s_rmse_pct": float(np.max(values)),
    }


def _summarize_rows(rows: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    return {
        category: {
            observer: _observer_summary(rows, category, observer)
            for observer in OBSERVERS
        }
        for category in CATEGORIES
    }


def _plot_initial_soc(ax, rows: list[dict]) -> None:
    initial_rows = [row for row in rows if row["category"] == "initial_soc_error"]
    for observer in OBSERVERS:
        subset = [row for row in initial_rows if row["observer"] == observer]
        ax.plot(
            [float(row["level"]) for row in subset],
            [row["post_300s_rmse_pct"] for row in subset],
            "o-",
            label=observer.upper(),
        )
    ax.set(
        xlabel="Initial SOC error",
        ylabel="Post-300 s RMSE [%pt]",
        title="Initial-state robustness",
    )
    ax.legend()
    ax.grid(alpha=0.25)


def _plot_noise(ax, rows: list[dict]) -> None:
    noise_order = [case[0] for case in NOISE_CASES]
    for observer in OBSERVERS:
        by_level = {
            row["level"]: row
            for row in rows
            if row["category"] == "measurement_noise" and row["observer"] == observer
        }
        subset = [by_level[level] for level in noise_order]
        ax.plot(
            noise_order,
            [row["post_300s_rmse_pct"] for row in subset],
            "o-",
            label=observer.upper(),
        )
    ax.set(xlabel="Noise level", title="Measurement-noise robustness")
    ax.grid(alpha=0.25)


def _uncertainty_matrix(rows: list[dict], observer: str = "ekf") -> np.ndarray:
    lookup = {
        row["level"]: row["post_300s_rmse_pct"]
        for row in rows
        if row["category"] == "parameter_uncertainty" and row["observer"] == observer
    }
    return np.array(
        [
            [lookup[f"C={capacity:.1f},R={resistance:.1f}"] for resistance in UNCERTAINTY_LEVELS]
            for capacity in UNCERTAINTY_LEVELS
        ],
        dtype=float,
    )


def _save_figure(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    _plot_initial_soc(axes[0], rows)
    _plot_noise(axes[1], rows)
    matrix = _uncertainty_matrix(rows)
    image = axes[2].imshow(
        matrix,
        origin="lower",
        cmap="viridis",
        extent=[0.75, 1.25, 0.75, 1.25],
        aspect="auto",
    )
    axes[2].set(
        xlabel="Resistance multiplier",
        ylabel="Capacity multiplier",
        title="EKF parameter uncertainty",
    )
    fig.colorbar(image, ax=axes[2], label="RMSE [%pt]")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _write_report(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    report = [
        "# Robustness matrix",
        "",
        "All cases use the same measured-aging-informed checkpoint and an independent synthetic dynamic profile.",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
    ]
    path.write_text("\n".join(report), encoding="utf-8")


def main() -> None:
    true_params, estimated_params = _load_checkpoint_parameters()
    rows: list[dict] = []
    _run_initial_soc_sweep(rows, estimated_params, true_params)
    _run_noise_sweep(rows, estimated_params, true_params)
    _run_parameter_sweep(rows, true_params)

    metrics_dir = ROOT / "results/metrics"
    _write_rows(metrics_dir / "robustness_matrix.csv", rows)
    summary = _summarize_rows(rows)
    (metrics_dir / "robustness_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    _save_figure(ROOT / "results/figures/robustness_matrix.png", rows)
    _write_report(ROOT / "results/reports/robustness_matrix.md", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
