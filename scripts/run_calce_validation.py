from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.calce import load_capacity_ah, load_dynamic_profile, load_incremental_ocv_curve
from battery_estimation.estimators import CoulombCounter, ExtendedKalmanFilter, UnscentedKalmanFilter
from battery_estimation.evaluation import calculate_metrics
from battery_estimation.identification import fit_2rc_ecm
from battery_estimation.models import ECMParameters, SecondOrderThevenin


def find_one(root: Path, pattern: str) -> Path:
    matches = list(root.rglob(pattern))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one file matching {pattern} under {root}, found {len(matches)}")
    return matches[0]


def run_filter(estimator, current: np.ndarray, voltage: np.ndarray | None = None):
    start = time.perf_counter()
    values = estimator.run(current) if voltage is None else estimator.run(current, voltage)
    runtime = 1e6 * (time.perf_counter() - start) / len(current)
    return values, runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Identify on CALCE DST and validate SOC estimation on independent FUDS data")
    parser.add_argument("--data-root", type=Path, default=ROOT / "data" / "raw" / "calce")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    parser.add_argument("--initial-soc-error", type=float, default=-0.10, help="SOC fraction added to the reference initial SOC")
    args = parser.parse_args()

    ocv_path = find_one(args.data_root, "*Incremental OCV*.xlsx")
    capacity_path = find_one(args.data_root, "*Initial capacity*.xls")
    dst_path = find_one(args.data_root, "*DST_80SOC.xls")
    fuds_path = find_one(args.data_root, "*FUDS_80SOC.xls")
    capacity_ah = load_capacity_ah(capacity_path)
    ocv_curve = load_incremental_ocv_curve(ocv_path)
    dst = load_dynamic_profile(dst_path, capacity_ah, dt_s=1.0)
    fuds = load_dynamic_profile(fuds_path, capacity_ah, dt_s=1.0)

    # Use every second DST point for identification to reduce grid-search cost while
    # retaining the complete dynamic range.
    fit_slice = slice(None, None, 2)
    fit = fit_2rc_ecm(
        dst.current_a[fit_slice],
        dst.voltage_v[fit_slice],
        ocv_curve(dst.reference_soc[fit_slice]),
        dt_s=2.0,
    )
    fitted_ocv = ocv_curve.with_bias(fit.ocv_bias_v)
    params = ECMParameters(
        capacity_ah=capacity_ah,
        coulombic_efficiency=1.0,
        r0=fit.r0,
        r1=fit.r1,
        c1=fit.c1,
        r2=fit.r2,
        c2=fit.c2,
    )
    model = SecondOrderThevenin(params, 1.0, fitted_ocv, fitted_ocv.derivative)
    open_loop_state = np.array([fuds.initial_soc, 0.0, 0.0])
    open_loop_voltage = np.empty(len(fuds.time_s))
    for k in range(len(fuds.time_s)):
        # Use the independently constructed SOC reference to isolate voltage-model error.
        open_loop_state[0] = fuds.reference_soc[k]
        open_loop_voltage[k] = model.terminal_voltage(open_loop_state, fuds.current_a[k])
        if k + 1 < len(fuds.time_s):
            next_state = model.transition(open_loop_state, fuds.current_a[k])
            open_loop_state[1:] = next_state[1:]
    open_loop_voltage_rmse = float(np.sqrt(np.mean((open_loop_voltage - fuds.voltage_v) ** 2)))
    initial_soc = float(np.clip(fuds.initial_soc + args.initial_soc_error, 0.0, 1.0))
    x0 = np.array([initial_soc, 0.0, 0.0])
    p0 = np.diag([0.025, 0.003, 0.003])
    q = np.diag([2e-8, 3e-6, 2e-6])
    voltage_variance = 0.012**2

    cc = CoulombCounter(initial_soc, capacity_ah, 1.0, 1.0)
    ekf = ExtendedKalmanFilter(model, x0, p0, q, voltage_variance)
    ukf = UnscentedKalmanFilter(model, x0, p0, q, voltage_variance, alpha=0.2, beta=2.0, kappa=0.0)
    cc_soc, cc_runtime = run_filter(cc, fuds.current_a)
    ekf_states, ekf_runtime = run_filter(ekf, fuds.current_a, fuds.voltage_v)
    ukf_states, ukf_runtime = run_filter(ukf, fuds.current_a, fuds.voltage_v)
    estimates = {
        "coulomb_counting": cc_soc,
        "ekf": ekf_states[:, 0],
        "ukf": ukf_states[:, 0],
    }
    runtimes = {"coulomb_counting": cc_runtime, "ekf": ekf_runtime, "ukf": ukf_runtime}
    metrics: dict[str, object] = {
        "dataset": {
            "publisher": "CALCE, University of Maryland",
            "cell": "Samsung INR18650-20R (NMC/graphite)",
            "temperature_c": 25,
            "identification_profile": dst_path.name,
            "validation_profile": fuds_path.name,
            "measured_capacity_ah": capacity_ah,
            "reference_initial_soc": fuds.initial_soc,
            "estimator_initial_soc": initial_soc,
            "samples": len(fuds.time_s),
            "open_loop_voltage_rmse_v": open_loop_voltage_rmse,
        },
        "identified_parameters": asdict(fit),
    }
    for method, estimate in estimates.items():
        values = calculate_metrics(fuds.reference_soc, estimate, 1.0)
        values["runtime_us_per_sample"] = runtimes[method]
        metrics[method] = values

    metrics_dir = args.output_root / "metrics"
    figures_dir = args.output_root / "figures"
    reports_dir = args.output_root / "reports"
    for directory in (metrics_dir, figures_dir, reports_dir):
        directory.mkdir(parents=True, exist_ok=True)
    metrics_path = metrics_dir / "calce_fuds_validation.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(fuds.time_s, fuds.current_a, lw=0.7)
    axes[0].set_ylabel("Current [A]")
    axes[0].grid(alpha=0.25)
    axes[1].plot(fuds.time_s, fuds.voltage_v, lw=0.7, label="Measured")
    axes[1].plot(fuds.time_s, open_loop_voltage, lw=0.7, alpha=0.8, label="2-RC open-loop")
    axes[1].set_ylabel("Measured voltage [V]")
    axes[1].legend()
    axes[1].grid(alpha=0.25)
    axes[2].plot(fuds.time_s, 100 * fuds.reference_soc, lw=1.4, label="Coulomb-integrated reference")
    axes[2].plot(fuds.time_s, 100 * estimates["coulomb_counting"], lw=0.9, label="Coulomb Counting")
    axes[2].plot(fuds.time_s, 100 * estimates["ekf"], lw=0.9, label="EKF")
    axes[2].plot(fuds.time_s, 100 * estimates["ukf"], lw=0.9, label="UKF")
    axes[2].set_ylabel("SOC [%]")
    axes[2].set_xlabel("Dynamic-profile time [s]")
    axes[2].legend(ncol=2)
    axes[2].grid(alpha=0.25)
    fig.suptitle("CALCE FUDS 25 C measured-data validation")
    fig.tight_layout()
    figure_path = figures_dir / "calce_fuds_validation.png"
    fig.savefig(figure_path, dpi=160)
    plt.close(fig)

    lines = [
        "# CALCE Measured-Data Validation",
        "",
        "Identification: DST 80% SOC at 25 C. Independent validation: FUDS 80% SOC at 25 C.",
        "",
        f"Measured initial capacity: {capacity_ah:.4f} Ah",
        f"Reference initial SOC: {100*fuds.initial_soc:.2f}%",
        f"Estimator initial SOC: {100*initial_soc:.2f}%",
        f"Independent FUDS open-loop voltage RMSE: {1000*open_loop_voltage_rmse:.2f} mV",
        "",
        "| Method | SOC RMSE [%pt] | SOC MAE [%pt] | Max error [%pt] | Final error [%pt] | Runtime [us/sample] |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method in ("coulomb_counting", "ekf", "ukf"):
        value = metrics[method]
        lines.append(
            f"| {method} | {value['rmse_pct']:.3f} | {value['mae_pct']:.3f} | {value['max_error_pct']:.3f} | "
            f"{value['final_error_pct']:.3f} | {value['runtime_us_per_sample']:.2f} |"
        )
    lines.extend(["", "The SOC reference is constructed by integrating measured current from the capacity-derived initial SOC.", ""])
    report_path = reports_dir / "calce_fuds_validation.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved {metrics_path}")
    print(f"Saved {figure_path}")
    print(f"Saved {report_path}")


if __name__ == "__main__":
    main()
