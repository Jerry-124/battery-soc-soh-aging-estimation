# Changelog

All notable portfolio releases are documented here. The `v1.0.0` entry records the first stable project-level portfolio baseline at its historical commit; package-level semantic versioning was unified with the project release line in `v1.1.0`.

## [1.1.1] - 2026-09-09

### Fixed
- CALCE voltage validation now reports a true full-state open-loop trajectory separately from the reference-SOC-conditioned diagnostic instead of injecting reference SOC into a quantity called open-loop.
- The CALCE EKF OCV Jacobian now exactly matches the piecewise-linear OCV interpolation; the artificial minimum derivative floor was removed.
- Oxford capacity normalized to the first characterization is now labeled `capacity_retention_pct`, while rated-capacity SOH is reported separately using the 740 mAh rated capacity.

### Validation
- Official SHA-256-verified CALCE workbooks were rerun after the Jacobian correction: EKF FUDS SOC RMSE is 0.740 %pt versus the legacy 0.731 %pt result, a ~1.2% increase that does not change the conclusion or require retuning.
- CALCE full-state open-loop and reference-SOC-conditioned voltage RMSE are both 22.38 mV in this setup because they use the same initial SOC, current, capacity, efficiency, and clipping recursion.
- Oxford mean final capacity retention is 75.50%; mean final rated-capacity SOH is 74.82% of 740 mAh. Holdout retention-trend errors are unchanged.
- Added four targeted regression tests for OCV derivative semantics, open-loop state propagation, and Oxford denominator definitions, expanding the suite from 27 to 31 tests.

### Scope
- This patch release corrects scientific semantics and validation reporting without expanding project scope or deleting any historical release.

## [1.1.0] - 2026-09-07

### Added
- Physical validation for 2-RC ECM parameters and synthetic experiment inputs.
- Redirect-host validation after HTTPS redirects, complementing the existing allow-list and SHA-256 checks.
- Regression coverage for invalid physical parameters and redirect-host enforcement.
- Repository metadata linking the Python package to its GitHub source.

### Changed
- Expanded the automated suite from 24 to 27 tests.
- CI now validates Python 3.10 and 3.12 with dependency checks, bytecode compilation, pytest, and Ruff.
- GitHub Actions uses current Node 24-compatible `actions/checkout@v5` and `actions/setup-python@v6`.
- CI triggers are scoped to `main` and pull requests targeting `main`, with redundant in-progress runs cancelled.

### Scope
- This release hardens the stable portfolio baseline while keeping the project focused on reproducible SOC/SOH estimation, measured-data validation, aging-aware adaptation, and robustness evaluation.

## [1.0.0] - 2026-09-07

### Stable Portfolio Baseline
- Second-order Thevenin equivalent circuit model (2-RC ECM), OCV-SOC modeling, and dynamic ECM parameter identification.
- Coulomb Counting, Extended Kalman Filter (EKF), and Unscented Kalman Filter (UKF) SOC estimation.
- CALCE DST measured-data parameter identification with independent CALCE FUDS SOC validation.
- Full-life CALCE CX2-3 capacity and pulse-resistance analysis across 1,185 diagnostic cycles.
- Measured aging analysis across eight Oxford battery cells.
- Capacity-SOH and resistance-growth indicators feeding an aging-aware observer adaptation workflow.
- Fresh-fixed, aged-fixed, and aging-aware parameter strategy comparisons.
- Robustness benchmarks covering initial-SOC error, measurement noise, and ECM parameter mismatch.
- Reproducible metrics, datasets, reports, figures, and automated verification.
- 24 automated pytest tests with Python 3.10/3.12 validation.

### Baseline Results
- Independent CALCE FUDS SOC RMSE: 0.731 %pt for EKF and 0.849 %pt for UKF.
- Full-life aging evaluation based on 1,185 CALCE CX2-3 diagnostic cycles.
- Cross-dataset aging evaluation using eight Oxford battery cells.

### Version History Note
- `v1.0.0` was restored retrospectively at the original stable V1 baseline commit to preserve the project's release history.
- At that historical commit, Python package metadata still used the earlier `0.1.0` development identifier; project/package semantic versioning was unified in `v1.1.0`.
