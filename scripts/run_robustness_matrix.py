from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from battery_estimation.data.synthetic import simulate_dataset
from battery_estimation.evaluation import calculate_metrics
from battery_estimation.health import pulse_anchored_fresh_parameters, perturb_parameters, run_kalman_observers


def score(rows, category, level, observer_params, true_params, initial_soc, voltage_noise, current_noise, seed=512):
    data = simulate_dataset(true_params, 1.0, 1800.0, 0.85, voltage_noise, current_noise, 0.0, seed)
    estimates = run_kalman_observers(observer_params, 1.0, data.current_a, data.voltage_v, initial_soc, voltage_noise)
    for method, estimate in estimates.items():
        full = calculate_metrics(data.true_soc, estimate, 1.0)
        settled = calculate_metrics(data.true_soc[300:], estimate[300:], 1.0)
        rows.append({"category": category, "level": level, "observer": method,
                     "rmse_pct": full["rmse_pct"], "post_300s_rmse_pct": settled["rmse_pct"],
                     "max_error_pct": full["max_error_pct"]})


def main() -> None:
    health = json.loads((ROOT / "results/metrics/cx2_pulse_aging.json").read_text(encoding="utf-8"))
    measured, cp = health["measured_health"], health["observer_checkpoint"]
    fresh = pulse_anchored_fresh_parameters(measured["initial_capacity_ah"], measured["initial_5s_pulse_resistance_ohm"])
    true_params = fresh.aged(cp["true_capacity_factor"], cp["true_resistance_factor"])
    estimated_params = fresh.aged(cp["estimated_capacity_factor"], cp["estimated_resistance_factor"])
    rows = []
    for error in (-0.20, -0.10, 0.0, 0.10, 0.20):
        score(rows, "initial_soc_error", f"{error:+.2f}", estimated_params, true_params, np.clip(.85 + error, 0, 1), .005, .015)
    for name, vn, cn in [("low", .002, .005), ("nominal", .005, .015), ("high", .010, .030), ("severe", .020, .060)]:
        score(rows, "measurement_noise", name, estimated_params, true_params, .75, vn, cn)
    for cm in (0.8, 0.9, 1.0, 1.1, 1.2):
        for rm in (0.8, 0.9, 1.0, 1.1, 1.2):
            score(rows, "parameter_uncertainty", f"C={cm:.1f},R={rm:.1f}", perturb_parameters(true_params, cm, rm), true_params, .75, .005, .015)
    csv_path = ROOT / "results/metrics/robustness_matrix.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summary = {}
    for category in ("initial_soc_error", "measurement_noise", "parameter_uncertainty"):
        category_rows = [r for r in rows if r["category"] == category]
        summary[category] = {method: {"mean_post_300s_rmse_pct": float(np.mean([r["post_300s_rmse_pct"] for r in category_rows if r["observer"] == method])),
                                      "worst_post_300s_rmse_pct": float(np.max([r["post_300s_rmse_pct"] for r in category_rows if r["observer"] == method]))}
                             for method in ("ekf", "ukf")}
    (ROOT / "results/metrics/robustness_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    initial_rows = [r for r in rows if r["category"] == "initial_soc_error"]
    for method in ("ekf", "ukf"):
        subset = [r for r in initial_rows if r["observer"] == method]
        axes[0].plot([float(r["level"]) for r in subset], [r["post_300s_rmse_pct"] for r in subset], "o-", label=method.upper())
    axes[0].set(xlabel="Initial SOC error", ylabel="Post-300 s RMSE [%pt]", title="Initial-state robustness"); axes[0].legend(); axes[0].grid(alpha=.25)
    noise_order = ["low", "nominal", "high", "severe"]
    for method in ("ekf", "ukf"):
        subset = [next(r for r in rows if r["category"] == "measurement_noise" and r["level"] == level and r["observer"] == method) for level in noise_order]
        axes[1].plot(noise_order, [r["post_300s_rmse_pct"] for r in subset], "o-", label=method.upper())
    axes[1].set(xlabel="Noise level", title="Measurement-noise robustness"); axes[1].grid(alpha=.25)
    matrix = np.empty((5, 5)); levels = (0.8, 0.9, 1.0, 1.1, 1.2)
    for i, cm in enumerate(levels):
        for j, rm in enumerate(levels):
            matrix[i, j] = next(r["post_300s_rmse_pct"] for r in rows if r["category"] == "parameter_uncertainty" and r["level"] == f"C={cm:.1f},R={rm:.1f}" and r["observer"] == "ekf")
    image = axes[2].imshow(matrix, origin="lower", cmap="viridis", extent=[.75,1.25,.75,1.25], aspect="auto")
    axes[2].set(xlabel="Resistance multiplier", ylabel="Capacity multiplier", title="EKF parameter uncertainty"); fig.colorbar(image, ax=axes[2], label="RMSE [%pt]")
    fig.tight_layout(); fig.savefig(ROOT / "results/figures/robustness_matrix.png", dpi=160); plt.close(fig)
    report = ["# Robustness matrix", "", "All cases use the same measured-aging-informed checkpoint and an independent synthetic dynamic profile.", "", "```json", json.dumps(summary, indent=2), "```", ""]
    (ROOT / "results/reports/robustness_matrix.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
