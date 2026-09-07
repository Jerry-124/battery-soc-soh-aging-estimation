# Changelog

All notable portfolio releases are documented here.

## [1.1.0] - 2026-09-07

### Added
- Physical validation for 2-RC ECM parameters and synthetic experiment inputs.
- Redirect-host validation after HTTPS redirects, complementing the existing allow-list and SHA-256 checks.
- Regression coverage for invalid physical parameters and redirect-host enforcement.
- Repository metadata linking the Python package to its GitHub source.

### Changed
- Expanded the automated suite to 27 tests.
- CI now validates Python 3.10 and 3.12 with dependency checks, bytecode compilation, pytest, and Ruff.
- GitHub Actions uses current Node 24-compatible `actions/checkout@v5` and `actions/setup-python@v6`.
- CI triggers are scoped to `main` and pull requests targeting `main`, with redundant in-progress runs cancelled.

### Scope
- This release keeps the project focused on reproducible SOC/SOH estimation, measured-data validation, aging-aware adaptation, and robustness evaluation rather than adding new research scope.
