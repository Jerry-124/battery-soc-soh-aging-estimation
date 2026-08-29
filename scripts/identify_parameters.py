from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.identification import identify_ohmic_resistance, identify_relaxation_grid
from battery_estimation.models import ECMParameters


def main() -> None:
    parser = argparse.ArgumentParser(description="Demonstrate pulse parameter identification on synthetic relaxation data")
    parser.add_argument("--output", type=Path, default=ROOT / "results" / "metrics" / "synthetic_parameter_identification.json")
    args = parser.parse_args()
    p = ECMParameters()
    current_step = 2.0
    time_s = np.arange(0.0, 900.0, 2.0)
    rng = np.random.default_rng(124)
    polarization = current_step * (p.r1 * np.exp(-time_s / (p.r1 * p.c1)) + p.r2 * np.exp(-time_s / (p.r2 * p.c2)))
    polarization += rng.normal(0.0, 0.0002, len(time_s))
    fit = identify_relaxation_grid(time_s, polarization)
    fit["r0_ohm"] = identify_ohmic_resistance(current_step * p.r0, current_step)
    fit["true_tau1_s"] = p.r1 * p.c1
    fit["true_tau2_s"] = p.r2 * p.c2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fit, indent=2), encoding="utf-8")
    print(json.dumps(fit, indent=2))


if __name__ == "__main__":
    main()

