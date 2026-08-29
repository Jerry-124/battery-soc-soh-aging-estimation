from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Markdown benchmark report from JSON metrics")
    parser.add_argument("--results", type=Path, default=Path("results/metrics"))
    parser.add_argument("--output", type=Path, default=Path("results/reports/benchmark.md"))
    args = parser.parse_args()
    rows = []
    for path in sorted(args.results.glob("synthetic_*benchmark.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for method in ("coulomb_counting", "ekf", "ukf"):
            value = data[method]
            convergence = value["convergence_s"]
            convergence_text = "N/A" if convergence is None else f"{convergence:.1f}"
            rows.append(
                f"| {path.stem} | {method} | {value['rmse_pct']:.3f} | {value['mae_pct']:.3f} | "
                f"{value['max_error_pct']:.3f} | {convergence_text} | {value['runtime_us_per_sample']:.2f} |"
            )
    lines = [
        "# Synthetic Benchmark Report",
        "",
        "> These results use generated data and validate the software pipeline; they are not experimental cell claims.",
        "",
        "| Experiment | Method | SOC RMSE [%pt] | SOC MAE [%pt] | Max error [%pt] | Convergence [s] | Runtime [us/sample] |",
        "|---|---|---:|---:|---:|---:|---:|",
        *rows,
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()
