from __future__ import annotations

import argparse
import json
from pathlib import Path

SCENARIO_LABELS = {
    "synthetic_aged_fixed_benchmark": "Aged, fixed parameters",
    "synthetic_aging_aware_benchmark": "Aged, adapted parameters",
    "synthetic_soc_benchmark": "Nominal",
}
METHOD_LABELS = {
    "coulomb_counting": "Coulomb Counting",
    "ekf": "EKF",
    "ukf": "UKF",
}


def build_report(results: Path) -> str:
    rows = []
    for path in sorted(results.glob("synthetic_*benchmark.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        scenario = SCENARIO_LABELS.get(path.stem, path.stem.replace("_", " ").title())
        for method in ("coulomb_counting", "ekf", "ukf"):
            value = data[method]
            first_within = value["first_within_2pct_s"]
            first_within_text = "N/A" if first_within is None else f"{first_within:.0f} s"
            rows.append(
                f"| {scenario} | {METHOD_LABELS[method]} | {value['rmse_pct']:.3f} %pt | "
                f"{value['mae_pct']:.3f} %pt | {value['max_error_pct']:.3f} %pt | "
                f"{first_within_text} | {value['runtime_us_per_sample']:.2f} µs/sample |"
            )
    lines = [
        "# Synthetic SOC Benchmark",
        "",
        "## Scope",
        "",
        (
            "These results use generated data to validate the estimator pipeline and "
            "controlled aging-mismatch scenarios. They are not experimental-cell "
            "performance claims."
        ),
        "",
        "## Key Results",
        "",
        (
            "| Scenario | Method | SOC RMSE | SOC MAE | Max Error | "
            "First Within ±2 %pt | Runtime |"
        ),
        "|---|---|---:|---:|---:|---:|---:|",
        *rows,
        "",
        "## Interpretation",
        "",
        (
            "The synthetic benchmark isolates estimator behavior under controlled "
            "initial-SOC error and parameter mismatch. `First Within ±2 %pt` is the "
            "first sample at which absolute SOC error is no greater than two percentage "
            "points; it is not a persistent-convergence guarantee. Measured-data "
            "validation is reported separately for CALCE and Oxford datasets."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown benchmark report from JSON metrics"
    )
    parser.add_argument("--results", type=Path, default=Path("results/metrics"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/reports/benchmark.md")
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(args.results), encoding="utf-8")
    print(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()
