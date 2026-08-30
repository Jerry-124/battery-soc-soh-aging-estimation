from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from battery_estimation.data.calce import OCVCurve
from battery_estimation.data.oxford import effective_resistance_from_segments
from battery_estimation.data.synthetic import simulate_dataset
from battery_estimation.estimators import ExtendedKalmanFilter, UnscentedKalmanFilter
from battery_estimation.evaluation import calculate_metrics
from battery_estimation.health import (
    adapt_parameters,
    capacity_soh,
    perturb_parameters,
    pulse_anchored_fresh_parameters,
    resistance_soh,
)
from battery_estimation.identification import fit_2rc_ecm
from battery_estimation.models import ECMParameters, SecondOrderThevenin, docv_dsoc


class TestECM(unittest.TestCase):
    def test_rest_state_preserves_soc(self):
        model = SecondOrderThevenin(ECMParameters(), 1.0)
        result = model.transition(np.array([0.7, 0.0, 0.0]), 0.0)
        np.testing.assert_allclose(result, [0.7, 0.0, 0.0])

    def test_discharge_reduces_soc_and_voltage(self):
        model = SecondOrderThevenin(ECMParameters(), 1.0)
        state = np.array([0.7, 0.0, 0.0])
        self.assertLess(model.transition(state, 2.0)[0], state[0])
        self.assertLess(model.terminal_voltage(state, 2.0), model.terminal_voltage(state, 0.0))

    def test_ocv_derivative_is_positive(self):
        self.assertTrue(np.all(docv_dsoc(np.linspace(0.0, 1.0, 101)) > 0.0))


class TestHealth(unittest.TestCase):
    def test_soh_and_adaptation(self):
        reference = ECMParameters()
        adapted = adapt_parameters(reference, reference.capacity_ah * 0.8, 1.5)
        self.assertAlmostEqual(capacity_soh(adapted.capacity_ah, reference.capacity_ah), 80.0)
        self.assertAlmostEqual(resistance_soh(adapted.r0, reference.r0), 100.0 / 1.5)

    def test_pulse_anchor_matches_five_second_response(self):
        params = pulse_anchored_fresh_parameters(1.35, 0.12)
        response = params.r0 + params.r1 * (1 - np.exp(-5 / (params.r1 * params.c1))) + params.r2 * (1 - np.exp(-5 / (params.r2 * params.c2)))
        self.assertAlmostEqual(response, 0.12, places=10)

    def test_parameter_perturbation_is_explicit(self):
        params = ECMParameters()
        changed = perturb_parameters(params, 0.8, 1.2)
        self.assertAlmostEqual(changed.capacity_ah, 0.8 * params.capacity_ah)
        self.assertAlmostEqual(changed.r0, 1.2 * params.r0)
        self.assertEqual(changed.c1, params.c1)


class TestMetrics(unittest.TestCase):
    def test_non_converged_result_is_json_safe(self):
        metrics = calculate_metrics(np.ones(5), np.zeros(5), 1.0)
        self.assertIsNone(metrics["convergence_s"])


class TestMeasuredDataSupport(unittest.TestCase):
    def test_ocv_curve_is_bounded_and_has_positive_derivative(self):
        curve = OCVCurve(np.array([0.0, 0.5, 1.0]), np.array([3.0, 3.6, 4.2]))
        self.assertAlmostEqual(curve(-1.0), 3.0)
        self.assertAlmostEqual(curve(2.0), 4.2)
        self.assertGreater(curve.derivative(0.5), 0.0)

    def test_grid_fit_recovers_known_2rc_parameters(self):
        rng = np.random.default_rng(9)
        current = rng.normal(0.4, 1.0, 1200)
        dt = 1.0

        def response(tau):
            alpha = np.exp(-dt / tau)
            value = np.zeros(len(current))
            for k in range(1, len(current)):
                value[k] = alpha * value[k - 1] + (1 - alpha) * current[k - 1]
            return value

        ocv = np.full(len(current), 3.7)
        voltage = ocv - 0.02 * current - 0.012 * response(10.0) - 0.03 * response(200.0) + 0.006
        fit = fit_2rc_ecm(current, voltage, ocv, dt, np.array([10.0]), np.array([200.0]))
        self.assertAlmostEqual(fit.r0, 0.02, places=6)
        self.assertAlmostEqual(fit.r1, 0.012, places=6)
        self.assertAlmostEqual(fit.r2, 0.03, places=6)
        self.assertAlmostEqual(fit.ocv_bias_v, 0.006, places=6)

    def test_effective_resistance_from_aligned_discharge_curves(self):
        q = np.linspace(0.0, -700.0, 701)
        t_load_days = np.linspace(0.0, 700.0 / 700.0 / 24.0, 701)
        t_ocv_days = np.linspace(0.0, 700.0 / 40.0 / 24.0, 701)
        base_voltage = 4.2 - 1.2 * np.abs(q) / 700.0
        load = {"q": q, "t": t_load_days, "v": base_voltage - 0.7 * 0.05}
        ocv = {"q": q, "t": t_ocv_days, "v": base_voltage - 0.04 * 0.05}
        self.assertAlmostEqual(effective_resistance_from_segments(load, ocv), 0.05, places=3)


class TestFilters(unittest.TestCase):
    def test_filters_reduce_initial_soc_error(self):
        params = ECMParameters()
        data = simulate_dataset(params, 1.0, 500.0, 0.9, 0.002, 0.005, 0.0, 42)
        model = SecondOrderThevenin(params, 1.0)
        x0 = np.array([0.75, 0.0, 0.0])
        p0 = np.diag([0.04, 0.002, 0.002])
        q = np.diag([8e-8, 4e-7, 2e-7])
        ekf = ExtendedKalmanFilter(model, x0, p0, q, 2.5e-5).run(data.current_a, data.voltage_v)[:, 0]
        ukf = UnscentedKalmanFilter(model, x0, p0, q, 2.5e-5).run(data.current_a, data.voltage_v)[:, 0]
        self.assertLess(abs(ekf[-1] - data.true_soc[-1]), 0.03)
        self.assertLess(abs(ukf[-1] - data.true_soc[-1]), 0.03)


if __name__ == "__main__":
    unittest.main()
