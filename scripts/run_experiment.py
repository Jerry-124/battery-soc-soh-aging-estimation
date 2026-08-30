from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.synthetic import simulate_dataset
from battery_estimation.estimators import (
    CoulombCounter,
    ExtendedKalmanFilter,
    UnscentedKalmanFilter,
)
from battery_estimation.evaluation import calculate_metrics
from battery_estimation.health import adapt_parameters, capacity_soh, resistance_soh
from battery_estimation.models import ECMParameters, SecondOrderThevenin


def build_filter_inputs(config: dict, model: SecondOrderThevenin) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    x0 = np.array([config["estimated_initial_soc"], 0.0, 0.0])
    p0 = np.diag([0.04, 0.002, 0.002])
    pv = config["process_variance"]
    q = np.diag([pv["soc"], pv["v1"], pv["v2"]])
    return x0, p0, q, float(config["voltage_variance"])


def timed_run(name: str, estimator, current: np.ndarray, voltage: np.ndarray | None = None):
    start = time.perf_counter()
    values = estimator.run(current) if voltage is None else estimator.run(current, voltage)
    elapsed = time.perf_counter() - start
    return name, values, 1e6 * elapsed / len(current)


def write_dataset(path: Path, dataset) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time_s", "current_a", "voltage_v", "clean_voltage_v", "true_soc"])
        writer.writerows(zip(dataset.time_s, dataset.current_a, dataset.voltage_v, dataset.clean_voltage_v, dataset.true_soc))


def output_directories(output_root: Path) -> tuple[Path, Path, Path]:
    """Return all experiment artifact roots under the requested output root."""
    return (
        output_root / "metrics",
        output_root / "figures",
        output_root / "data" / "processed",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a reproducible synthetic SOC/SOH benchmark")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    reference = ECMParameters()
    aging = config["aging"]
    true_params = reference.aged(float(aging["capacity_factor"]), float(aging["resistance_factor"]))
    dataset = simulate_dataset(
        params=true_params,
        dt_s=float(config["dt_s"]),
        duration_s=float(config["duration_s"]),
        initial_soc=float(config["true_initial_soc"]),
        voltage_noise_std_v=float(config["voltage_noise_std_v"]),
        current_noise_std_a=float(config["current_noise_std_a"]),
        current_bias_a=float(config["current_bias_a"]),
        seed=int(config["seed"]),
        resistance_factor=float(aging["resistance_factor"]),
    )
    observer_params = reference
    if config["observer"]["use_aging_adaptation"]:
        observer_params = adapt_parameters(reference, true_params.capacity_ah, float(aging["resistance_factor"]))
    observer_model = SecondOrderThevenin(observer_params, float(config["dt_s"]))
    x0, p0, q, r = build_filter_inputs(config, observer_model)
    cc = CoulombCounter(x0[0], observer_params.capacity_ah, observer_params.coulombic_efficiency, float(config["dt_s"]))
    ekf = ExtendedKalmanFilter(observer_model, x0, p0, q, r)
    ukf = UnscentedKalmanFilter(observer_model, x0, p0, q, r)
    outputs = {}
    runtimes = {}
    for name, estimator, voltage in [("coulomb_counting", cc, None), ("ekf", ekf, dataset.voltage_v), ("ukf", ukf, dataset.voltage_v)]:
        method, values, runtime = timed_run(name, estimator, dataset.current_a, voltage)
        outputs[method] = values if values.ndim == 1 else values[:, 0]
        runtimes[method] = runtime
    metrics = {}
    for method, estimate in outputs.items():
        metrics[method] = calculate_metrics(dataset.true_soc, estimate, float(config["dt_s"]))
        metrics[method]["runtime_us_per_sample"] = runtimes[method]
    metrics["health"] = {
        "capacity_soh_pct": capacity_soh(true_params.capacity_ah, reference.capacity_ah),
        "resistance_soh_pct": resistance_soh(true_params.r0, reference.r0),
        "capacity_ah": true_params.capacity_ah,
        "resistance_factor": float(aging["resistance_factor"]),
        "observer_aging_adapted": bool(config["observer"]["use_aging_adaptation"]),
    }
    name = config["experiment_name"]
    metrics_dir, figures_dir, data_dir = output_directories(args.output_root)
    for directory in (metrics_dir, figures_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)
    (metrics_dir / f"{name}.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    write_dataset(data_dir / f"{name}.csv", dataset)
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(dataset.time_s, dataset.current_a, lw=0.8)
    axes[0].set_ylabel("Current [A]")
    axes[0].grid(alpha=0.25)
    axes[1].plot(dataset.time_s, dataset.voltage_v, lw=0.7, label="Measured")
    axes[1].plot(dataset.time_s, dataset.clean_voltage_v, lw=1.0, label="Clean truth")
    axes[1].set_ylabel("Voltage [V]")
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    axes[2].plot(dataset.time_s, 100 * dataset.true_soc, lw=1.4, label="True SOC")
    axes[2].plot(dataset.time_s, 100 * outputs["coulomb_counting"], lw=0.9, label="Coulomb Counting")
    axes[2].plot(dataset.time_s, 100 * outputs["ekf"], lw=0.9, label="EKF")
    axes[2].plot(dataset.time_s, 100 * outputs["ukf"], lw=0.9, label="UKF")
    axes[2].set_ylabel("SOC [%]")
    axes[2].set_xlabel("Time [s]")
    axes[2].legend(ncol=2)
    axes[2].grid(alpha=0.25)
    fig.suptitle(name.replace("_", " ").title() + " (synthetic data)")
    fig.tight_layout()
    fig.savefig(figures_dir / f"{name}.png", dpi=160)
    plt.close(fig)
    print(json.dumps(metrics, indent=2))
    print(f"Saved metrics to {metrics_dir / f'{name}.json'}")
    print(f"Saved figure to {figures_dir / f'{name}.png'}")


if __name__ == "__main__":
    main()
