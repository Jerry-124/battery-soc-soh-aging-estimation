# Changelog

All notable portfolio releases are documented here. The `v1.0.0` entry records the first stable project-level portfolio baseline at its historical commit; package-level semantic versioning was unified with the project release line in `v1.1.0`.

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
