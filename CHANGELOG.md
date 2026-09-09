# Changelog

Notable stable releases are documented below. Historical results are preserved as they were reported for each release; later corrections are not retroactively substituted into earlier entries.

## [1.1.2] - 2026-09-09

### Summary

Reproducibility and terminology-consistency patch for report generation, CX2 capacity semantics, metric naming, and defensive validation.

### Changes

- Updated all public Markdown report generators to reproduce the structured `Scope / Key Results / Interpretation` reports committed in the repository.
- Renamed CALCE CX2-3 first-diagnostic-normalized capacity from `capacity_soh_pct` to `capacity_retention_pct`, including the processed CSV schema, estimator field names, plotting labels, tests, and documentation.
- Replaced the ambiguous `convergence_s` metric with `first_within_2pct_s`, defined as the first sample whose absolute SOC error is no greater than two percentage points.
- Added finite-value validation for ECM parameters, aging factors, and synthetic experiment inputs.
- Removed the metadata-only `resistance_factor` argument and field from the synthetic dataset API; resistance aging remains represented explicitly in the supplied ECM parameters.
- Isolated CALCE CX2-3 processed artifacts under custom `--output-root` directories while preserving the repository's default curated-data location.
- Updated committed metric artifacts and the synthetic benchmark report to the corrected field names without changing numerical benchmark values.

### Validation

- Automated suite expanded from 31 to 34 tests.
- Added regression coverage for CX2 capacity-retention naming, CX2 custom-output isolation, and public report-generator structure.
- Existing numerical SOC, SOH, aging, and robustness results are unchanged; no estimator retuning was required.

### Scope

This patch closes reproducibility and naming inconsistencies discovered after `v1.1.1`. It does not expand the scientific scope or rewrite historical release results.

## [1.1.1] - 2026-09-09

### Summary

Scientific-semantics patch correcting CALCE voltage-validation definitions, EKF OCV-Jacobian consistency, and Oxford capacity-health terminology.

### Changes

- Separated true full-state CALCE open-loop voltage validation from the reference-SOC-conditioned diagnostic.
- Aligned the CALCE EKF OCV Jacobian with the active segment of the piecewise-linear OCV interpolation.
- Removed the artificial minimum OCV-derivative floor.
- Renamed first-characterization-normalized Oxford capacity as `capacity_retention_pct`.
- Added `rated_capacity_soh_pct` using the 740 mAh rated capacity.
- Updated the corresponding processed data, metrics, reports, figures, README, and tests.

### Validation

- Automated suite expanded from 27 to 31 tests.
- Official CALCE workbooks were rerun after the Jacobian correction.
- CALCE FUDS EKF SOC RMSE: 0.740 %pt versus the legacy 0.731 %pt result, an increase of approximately 1.2% that does not change the conclusion or require retuning.
- Full-state open-loop voltage RMSE: 22.38 mV.
- Reference-SOC-conditioned voltage RMSE: 22.38 mV.
- Oxford mean final capacity retention: 75.50%.
- Oxford mean final rated-capacity SOH: 74.82% of 740 mAh.

### Scope

This patch corrects scientific definitions and reporting semantics without expanding the project scope or rewriting historical release results.

## [1.1.0] - 2026-09-07

### Summary

Validation and CI hardening for the stable SOC/SOH estimation baseline.

### Changes

- Added physical validation for 2-RC ECM parameters and synthetic experiment inputs.
- Added redirect-host validation after HTTPS redirects, complementing the existing host allow-list and SHA-256 checks.
- Added regression coverage for invalid physical parameters and redirect-host enforcement.
- Updated GitHub Actions to Node 24-compatible `actions/checkout@v5` and `actions/setup-python@v6`.
- Scoped CI triggers to `main` and pull requests targeting `main`, with redundant in-progress runs cancelled.

### Validation

- Automated suite expanded from 24 to 27 tests.
- CI validates Python 3.10 and 3.12 with dependency checks, source compilation, pytest, Ruff linting, and Ruff formatting checks.

### Scope

The release hardens the existing baseline while keeping the project focused on reproducible SOC/SOH estimation, measured-data validation, aging-aware adaptation, and robustness evaluation.

## [1.0.0] - 2026-09-07

### Summary

First stable project-level baseline for lithium-ion battery SOC/SOH estimation and aging-aware modeling.

### Changes

- Second-order Thevenin equivalent circuit model (2-RC ECM), OCV-SOC modeling, and dynamic ECM parameter identification.
- Coulomb Counting, Extended Kalman Filter (EKF), and Unscented Kalman Filter (UKF) SOC estimation.
- CALCE DST measured-data parameter identification with independent CALCE FUDS validation.
- Full-life CALCE CX2-3 capacity and pulse-resistance analysis across 1,185 diagnostic cycles.
- Measured aging analysis across eight Oxford battery cells.
- Aging-aware observer adaptation and robustness benchmarks.
- Reproducible metrics, datasets, reports, figures, and automated verification.

### Validation

- 24 automated pytest tests with Python 3.10 and 3.12 validation.
- Independent CALCE FUDS SOC RMSE: 0.731 %pt for EKF and 0.849 %pt for UKF.
- Full-life aging evaluation based on 1,185 CALCE CX2-3 diagnostic cycles.
- Cross-dataset aging evaluation using eight Oxford battery cells.

### Scope

`v1.0.0` was restored retrospectively at the original stable V1 commit to preserve release history. At that historical commit, Python package metadata still used the earlier `0.1.0` development identifier; project/package semantic versioning was unified in `v1.1.0`.