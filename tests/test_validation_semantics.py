from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.calce import MeasuredProfile, OCVCurve
from battery_estimation.data.oxford import OxfordHealthTrajectory


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestOCVInterpolationConsistency(unittest.TestCase):
    def test_derivative_is_exact_active_segment_slope(self):
        curve = OCVCurve(
            np.array([0.0, 0.25, 1.0]),
            np.array([3.0, 3.1, 4.0]),
        )
        np.testing.assert_allclose(curve.derivative([0.1, 0.5]), [0.4, 1.2])

    def test_derivative_has_no_artificial_minimum_floor(self):
        curve = OCVCurve(np.array([0.0, 0.5, 1.0]), np.array([3.0, 3.0, 4.0]))
        self.assertEqual(curve.derivative(0.25), 0.0)


class _SocEchoModel:
    def terminal_voltage(self, state, current):
        return float(state[0])

    def transition(self, state, current):
        result = np.asarray(state, dtype=float).copy()
        result[0] -= 0.1
        return result


class TestValidationDefinitions(unittest.TestCase):
    def test_full_state_open_loop_never_injects_reference_soc(self):
        module = load_script("run_calce_validation")
        profile = MeasuredProfile(
            time_s=np.arange(3.0),
            current_a=np.zeros(3),
            voltage_v=np.zeros(3),
            reference_soc=np.array([0.9, 0.7, 0.5]),
            initial_soc=0.9,
            capacity_ah=1.0,
            source_path="synthetic",
        )
        full_state, conditioned = module.voltage_model_diagnostics(
            _SocEchoModel(), profile
        )
        np.testing.assert_allclose(full_state, [0.9, 0.8, 0.7])
        np.testing.assert_allclose(conditioned, profile.reference_soc)

    def test_oxford_capacity_fields_have_distinct_denominators(self):
        capacity = np.array([750.0, 555.0])
        trajectory = OxfordHealthTrajectory(
            cell="Cell1",
            cycle=np.array([0, 100]),
            capacity_mah=capacity,
            capacity_retention_pct=100.0 * capacity / capacity[0],
            rated_capacity_soh_pct=100.0 * capacity / 740.0,
            effective_resistance_ohm=np.array([0.05, 0.06]),
            resistance_soh_pct=np.array([100.0, 100.0 / 1.2]),
        )
        self.assertAlmostEqual(trajectory.capacity_retention_pct[-1], 74.0)
        self.assertAlmostEqual(trajectory.rated_capacity_soh_pct[-1], 75.0)


if __name__ == "__main__":
    unittest.main()
