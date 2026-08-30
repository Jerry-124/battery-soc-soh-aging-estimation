from __future__ import annotations

import numpy as np
import pytest

from battery_estimation.identification.ecm_fit import _filtered_current, fit_2rc_ecm


def test_fit_2rc_recovers_known_grid_candidate() -> None:
    samples = 240
    dt_s = 1.0
    time = np.arange(samples, dtype=float)
    current = 1.2 * np.sin(time / 17.0) + 0.6 * np.cos(time / 9.0)
    tau1, tau2 = 10.0, 100.0
    r0, r1, r2 = 0.02, 0.01, 0.015
    ocv_bias = 0.01
    response1 = _filtered_current(current, dt_s, tau1)
    response2 = _filtered_current(current, dt_s, tau2)
    target = r0 * current + r1 * response1 + r2 * response2 - ocv_bias
    ocv = np.full(samples, 3.7)
    voltage = ocv - target

    result = fit_2rc_ecm(
        current,
        voltage,
        ocv,
        dt_s,
        tau1_grid_s=np.array([tau1]),
        tau2_grid_s=np.array([tau2]),
    )

    assert result.r0 == pytest.approx(r0, rel=1e-8, abs=1e-10)
    assert result.r1 == pytest.approx(r1, rel=1e-8, abs=1e-10)
    assert result.r2 == pytest.approx(r2, rel=1e-8, abs=1e-10)
    assert result.tau1_s == tau1
    assert result.tau2_s == tau2
    assert result.ocv_bias_v == pytest.approx(ocv_bias, abs=1e-10)
    assert result.voltage_rmse_v < 1e-10
