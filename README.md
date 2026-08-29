# Battery SOC/SOH Estimation with EKF/UKF and Aging-Aware Modeling

[![Status](https://img.shields.io/badge/status-in%20development-orange)](#status)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#technical-stack)

A reproducible Battery Management System (BMS) project for lithium-ion battery modeling, parameter identification, State of Charge (SOC) estimation, State of Health (SOH) estimation, and aging-aware observer adaptation.

The `battery-soc-soh-aging-estimation` project combines a second-order Thevenin equivalent circuit model (2-RC ECM), Coulomb Counting, Extended Kalman Filtering (EKF), Unscented Kalman Filtering (UKF), and degradation-aware parameter updates. Its purpose is to connect electrochemical-system behavior with implementable estimation algorithms under realistic operating uncertainties.

> **Important:** This repository is under development. Numerical results, plots, and benchmark values are intentionally marked `TBD` until they are produced by reproducible experiments. No performance values in this README are fabricated.

---

## Motivation

SOC and SOH are essential internal states for safe and efficient battery operation, but neither can be measured directly by standard onboard sensors. A practical BMS must infer them from measurable signals such as terminal voltage, current, and temperature.

The estimation problem is difficult because:

- the open-circuit-voltage relationship is nonlinear;
- model parameters vary with SOC, temperature, and aging;
- current and voltage measurements contain bias and noise;
- the initial SOC may be inaccurate or unknown;
- capacity fade and resistance growth cause model mismatch over battery life;
- dynamic drive cycles excite battery dynamics differently from laboratory pulse tests.

This project addresses these effects within one transparent and reproducible workflow, from data preparation and model identification to state estimation and robustness benchmarking.

## Project Objectives

The project aims to:

1. Implement a physically interpretable 2-RC Thevenin ECM.
2. Identify the OCV-SOC curve and SOC-dependent ECM parameters from battery data.
3. Establish Coulomb Counting as a transparent SOC baseline.
4. Implement EKF- and UKF-based SOC estimators without relying on black-box filter libraries.
5. Estimate SOH using both usable-capacity fade and internal-resistance growth.
6. adapt model and observer parameters as the battery ages.
7. Evaluate accuracy, convergence, robustness, and computational cost under controlled test scenarios.
8. Provide reproducible configurations, scripts, metrics, plots, and experiment records suitable for engineering review.

## System Architecture

```text
Battery dataset
  |-- current, voltage, temperature, timestamps
  |-- reference SOC / capacity / resistance when available
  v
Data validation and preprocessing
  |-- sign convention and unit checks
  |-- resampling, filtering, cycle segmentation
  v
Offline identification
  |-- OCV-SOC characterization
  |-- R0, R1, C1, R2, C2 identification
  |-- nominal capacity and aging indicators
  v
2-RC Thevenin ECM
  |-- nonlinear state-space model
  |-- SOC- and SOH-dependent parameters
  v
State estimation
  |-- Coulomb Counting baseline
  |-- Extended Kalman Filter
  |-- Unscented Kalman Filter
  v
Health estimation and adaptation
  |-- capacity-fade SOH
  |-- resistance-growth SOH
  |-- aging-aware parameter update
  v
Evaluation and benchmarking
  |-- accuracy and convergence
  |-- noise and uncertainty robustness
  |-- computational cost
  |-- reproducible reports and figures
```

## Battery Model: 2-RC Thevenin ECM

The electrical model consists of an open-circuit-voltage source, an ohmic resistance, and two parallel RC polarization branches. The two time constants represent fast and slow voltage dynamics more accurately than a first-order model while remaining suitable for online estimation.

Using the discharge-positive current convention, the continuous-time model is:

```math
\frac{d z}{dt} = -\frac{\eta I(t)}{Q_{\mathrm{usable}}}
```

```math
\frac{d V_1}{dt} = -\frac{V_1}{R_1 C_1} + \frac{I(t)}{C_1}
```

```math
\frac{d V_2}{dt} = -\frac{V_2}{R_2 C_2} + \frac{I(t)}{C_2}
```

```math
V_t = V_{\mathrm{OC}}(z) - I R_0 - V_1 - V_2
```

where:

- $z$ is SOC;
- $I$ is battery current, positive during discharge;
- $\eta$ is Coulombic efficiency;
- $Q_{\mathrm{usable}}$ is usable capacity;
- $V_1$ and $V_2$ are polarization voltages;
- $R_0$ is ohmic resistance;
- $(R_1,C_1)$ and $(R_2,C_2)$ define the polarization branches;
- $V_{\mathrm{OC}}(z)$ is the nonlinear OCV-SOC relationship;
- $V_t$ is terminal voltage.

For a sampling interval $\Delta t$, the discrete state transition is implemented using the analytical RC solution:

```math
V_{i,k+1} = e^{-\Delta t/(R_i C_i)} V_{i,k}
+ R_i\left(1-e^{-\Delta t/(R_i C_i)}\right) I_k,
\quad i \in \{1,2\}.
```

The initial implementation assumes a lumped, isothermal cell model. Temperature-dependent lookup tables are reserved for a later extension.

## OCV-SOC Characterization and Parameter Identification

### OCV-SOC relationship

The OCV-SOC curve will be obtained from low-rate or incremental OCV test data after appropriate rest periods. Candidate representations include:

- shape-preserving piecewise cubic interpolation;
- monotonic spline interpolation;
- a low-order polynomial used only when it preserves physical behavior.

The selected representation must provide both $V_{\mathrm{OC}}(z)$ and a stable derivative $dV_{\mathrm{OC}}/dz$ for EKF linearization. The curve will be bounded to the characterized SOC interval to avoid uncontrolled extrapolation.

### ECM parameter identification

The parameters $R_0$, $R_1$, $C_1$, $R_2$, and $C_2$ will be identified from pulse-relaxation data or a suitable dynamic dataset. The planned workflow is:

1. determine instantaneous voltage response for $R_0$;
2. fit the fast and slow relaxation components;
3. estimate RC time constants and recover capacitances;
4. repeat over SOC operating points;
5. construct bounded SOC-dependent lookup tables;
6. validate on data not used for identification.

Constrained nonlinear least squares will be used where direct pulse extraction is insufficient. Identification and validation segments will remain separate to reduce optimistic performance estimates.

## SOC Estimation

### Coulomb Counting baseline

Coulomb Counting provides the reference baseline:

```math
\hat{z}_{k+1} = \hat{z}_k - \frac{\eta I_k \Delta t}{Q_{\mathrm{assumed}}}.
```

It is simple and computationally efficient, but accumulated sensor bias, an incorrect initial SOC, and capacity mismatch produce drift. The baseline is therefore useful both as an engineering reference and as a controlled demonstration of why voltage-corrected observers are required.

### Extended Kalman Filter

The EKF uses the nonlinear OCV-SOC measurement equation and a locally linearized model. A typical state vector is:

```math
\mathbf{x}_k = [z_k, V_{1,k}, V_{2,k}]^T.
```

At each sample, the EKF performs:

1. nonlinear state prediction using the discrete ECM;
2. covariance prediction using the state-transition Jacobian;
3. terminal-voltage prediction;
4. measurement-model linearization using $dV_{\mathrm{OC}}/dz$;
5. Kalman gain calculation;
6. state and covariance correction;
7. physical state bounding and numerical consistency checks.

Process and measurement covariance matrices will be documented in experiment configurations. Sensitivity to their tuning will be evaluated rather than hidden behind a single favorable setting.

### Unscented Kalman Filter

The UKF propagates deterministically selected sigma points through the nonlinear state and measurement functions. It avoids explicit Jacobians and may better capture nonlinear behavior in OCV regions with strong curvature.

The implementation will document:

- sigma-point construction;
- scaling parameters $\alpha$, $\beta$, and $\kappa$;
- weighted mean and covariance recovery;
- process- and measurement-noise treatment;
- covariance stabilization and state constraints.

EKF and UKF will use the same datasets, model parameterization, initial conditions, and evaluation intervals so that their comparison is meaningful.

## SOH Estimation

SOH is represented using two complementary indicators.

### Capacity-fade SOH

```math
SOH_Q = \frac{Q_{\mathrm{usable}}}{Q_{\mathrm{rated}}} \times 100\%.
```

Usable capacity will be estimated from qualified charge or discharge windows when sufficient SOC span and reliable current integration are available. Partial-window estimates will include observability and data-quality checks.

### Resistance-growth SOH

Resistance growth will be monitored using the identified ohmic resistance and, where appropriate, total effective resistance:

```math
SOH_R = \frac{R_{\mathrm{reference}}}{R_{\mathrm{estimated}}} \times 100\%.
```

Because capacity loss and resistance growth describe different degradation mechanisms, both indicators will be reported rather than collapsed into an unexplained single health score. Any combined indicator introduced later will state its weighting and intended application explicitly.

## Aging-Aware Parameter Adaptation

A fixed fresh-cell model becomes increasingly inaccurate as usable capacity decreases and resistance rises. The aging-aware layer will therefore update selected estimator parameters using health estimates or cycle-specific identification results.

Planned adaptations include:

- replacing nominal capacity with estimated usable capacity in SOC propagation;
- updating $R_0$, $R_1$, $R_2$, and associated time constants using bounded SOH-dependent maps;
- adjusting process-noise assumptions when model uncertainty increases;
- preserving physical bounds, rate limits, and fallback values;
- separating slow health adaptation from fast SOC estimation.

The project will compare fixed-parameter and aging-aware filters on aged-cell data. Adaptation will only be credited when it improves held-out results consistently and does not destabilize the observer.

## Experimental Design

All estimators will be evaluated with identical preprocessing, sign conventions, sampling intervals, and scoring windows. Random noise experiments will use recorded seeds.

### Dynamic operating profiles

Evaluation will use one or more public dynamic current profiles, subject to dataset availability and licensing. Candidate profiles include DST, FUDS, UDDS, or comparable drive-cycle data. Training/identification cycles and evaluation cycles will be kept separate.

### Initial SOC error

Filters will be initialized with controlled SOC offsets to assess convergence and recovery:

- nominal initialization: `TBD`;
- moderate SOC offset: `TBD`;
- severe SOC offset: `TBD`.

### Measurement noise and bias

Controlled perturbations will be applied to current and terminal voltage:

- zero-mean voltage noise: `TBD`;
- zero-mean current noise: `TBD`;
- current-sensor bias: `TBD`;
- voltage-sensor bias: `TBD`.

Noise levels will be selected to represent documented sensor assumptions and will be reported with units.

### Parameter uncertainty

Robustness tests will perturb model inputs independently and jointly, including:

- ohmic resistance;
- RC-branch parameters;
- nominal or usable capacity;
- OCV-SOC curve;
- Coulombic efficiency.

Perturbation magnitudes and randomization distributions are currently `TBD`.

### Aging conditions

Fresh, intermediate, and aged conditions will be evaluated where the selected dataset permits. Tests will compare:

- fixed fresh-cell parameters;
- cycle- or SOH-indexed parameters;
- online or periodically updated aging-aware parameters.

No cross-life benchmark will be reported until sufficiently consistent aging data and reference health labels are available.

## Evaluation Metrics

SOC accuracy will be evaluated using:

```math
RMSE = \sqrt{\frac{1}{N}\sum_{k=1}^{N}(\hat{z}_k-z_k)^2}
```

```math
MAE = \frac{1}{N}\sum_{k=1}^{N}|\hat{z}_k-z_k|
```

Additional metrics include:

- maximum absolute SOC error;
- terminal-voltage RMSE and MAE;
- convergence time after an initial SOC offset;
- steady-state bias;
- capacity-estimation error;
- resistance-estimation error;
- execution time per sample;
- peak memory use, where relevant;
- numerical failures or covariance-stability events.

Metrics will be reported on the same evaluation window. SOC values will be labeled clearly as fractions or percentage points to prevent unit ambiguity.

## Benchmark

The following table is a reporting template. Every value remains `TBD` until generated by the repository's reproducible evaluation pipeline.

| Method | Operating condition | SOC RMSE | SOC MAE | Max. SOC error | Voltage RMSE | Convergence time | Runtime/sample |
|---|---|---:|---:|---:|---:|---:|---:|
| Coulomb Counting | Nominal dynamic cycle | TBD | TBD | TBD | N/A | N/A | TBD |
| EKF, fixed parameters | Nominal dynamic cycle | TBD | TBD | TBD | TBD | TBD | TBD |
| UKF, fixed parameters | Nominal dynamic cycle | TBD | TBD | TBD | TBD | TBD | TBD |
| EKF, aging-aware | Aged-cell dynamic cycle | TBD | TBD | TBD | TBD | TBD | TBD |
| UKF, aging-aware | Aged-cell dynamic cycle | TBD | TBD | TBD | TBD | TBD | TBD |

Planned SOH reporting:

| Method | Cell condition | Capacity error | Resistance error | Evaluation cycles | Notes |
|---|---|---:|---:|---:|---|
| Capacity-based SOH | TBD | TBD | N/A | TBD | TBD |
| Resistance-based SOH | TBD | N/A | TBD | TBD | TBD |
| Combined aging-aware estimator | TBD | TBD | TBD | TBD | TBD |

## Results

Results will be added only after experiments can be reproduced from committed configurations.

Planned figures:

- measured and estimated terminal voltage;
- reference SOC versus Coulomb Counting, EKF, and UKF;
- SOC estimation error over time;
- convergence from incorrect initial SOC;
- noise-robustness comparison;
- parameter-uncertainty sensitivity;
- capacity fade over cycle life;
- resistance growth over cycle life;
- fixed-parameter versus aging-aware estimation;
- accuracy-versus-runtime comparison.

Current results: **TBD**.

## Repository Structure

```text
battery-soc-soh-aging-estimation/
|-- README.md
|-- pyproject.toml                  # Package metadata and dependencies
|-- configs/
|   |-- data/                       # Dataset and preprocessing settings
|   |-- model/                      # ECM and OCV configuration
|   `-- experiments/                # Reproducible benchmark scenarios
|-- data/
|   |-- raw/                        # Not committed when licensing forbids it
|   |-- interim/
|   `-- processed/
|-- docs/
|   |-- model_equations.md
|   |-- parameter_identification.md
|   `-- experiment_protocol.md
|-- notebooks/
|   |-- 01_data_exploration.ipynb
|   |-- 02_ocv_soc_identification.ipynb
|   `-- 03_results_analysis.ipynb
|-- scripts/
|   |-- download_data.py
|   |-- preprocess_data.py
|   |-- identify_parameters.py
|   |-- run_experiment.py
|   `-- generate_report.py
|-- src/
|   `-- battery_estimation/
|       |-- data/
|       |-- models/
|       |-- identification/
|       |-- estimators/
|       |-- health/
|       |-- evaluation/
|       `-- visualization/
|-- tests/
|   |-- unit/
|   `-- integration/
`-- results/
    |-- figures/
    |-- metrics/
    `-- reports/
```

The structure may evolve during implementation. Generated datasets and large result files will not be committed unless their licenses and repository size permit it.

## Technical Stack

Planned stack:

- Python 3.10+
- NumPy for numerical computation
- SciPy for optimization and signal processing
- pandas for time-series data handling
- Matplotlib and Seaborn for visualization
- PyYAML for experiment configuration
- pytest for automated testing
- Jupyter for exploratory analysis and documented experiments

Exact versions will be pinned in `pyproject.toml` and the lock file once implementation begins.

## Reproduction

The commands below define the intended interface and will become executable as the corresponding modules are implemented.

```bash
git clone https://github.com/Jerry-124/battery-soc-soh-aging-estimation.git
cd battery-soc-soh-aging-estimation

python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Prepare the selected dataset:

```bash
python scripts/download_data.py --dataset <dataset-name>
python scripts/preprocess_data.py --config configs/data/<dataset-name>.yaml
```

Identify the OCV-SOC relationship and ECM parameters:

```bash
python scripts/identify_parameters.py \
  --config configs/experiments/parameter_identification.yaml
```

Run a benchmark experiment:

```bash
python scripts/run_experiment.py \
  --config configs/experiments/soc_benchmark.yaml
```

Run the aging-aware evaluation and generate the report:

```bash
python scripts/run_experiment.py \
  --config configs/experiments/aging_aware_benchmark.yaml

python scripts/generate_report.py \
  --results results/metrics \
  --output results/reports/benchmark.md
```

Run the test suite:

```bash
pytest
```

> Dataset names, download behavior, configuration filenames, and command-line options are provisional until their implementations are committed.

## Development Roadmap

- [ ] Define dataset selection criteria, provenance, and license notes
- [ ] Implement data validation, resampling, and cycle segmentation
- [ ] Characterize and validate the OCV-SOC relationship
- [ ] Implement the continuous and discrete 2-RC Thevenin ECM
- [ ] Identify SOC-dependent ECM parameters
- [ ] Validate voltage prediction on held-out dynamic cycles
- [ ] Implement Coulomb Counting baseline
- [ ] Implement and unit-test the EKF
- [ ] Implement and unit-test the UKF
- [ ] Establish nominal dynamic-cycle benchmarks
- [ ] Add initial-SOC-error experiments
- [ ] Add measurement-noise and sensor-bias experiments
- [ ] Add parameter-uncertainty experiments
- [ ] Implement capacity-fade SOH estimation
- [ ] Implement resistance-growth SOH estimation
- [ ] Implement bounded aging-aware parameter adaptation
- [ ] Compare fixed and aging-aware estimators on aged-cell data
- [ ] Profile runtime and memory use
- [ ] Publish reproducible figures and benchmark tables
- [ ] Add continuous integration and documentation checks

## Scope

This repository focuses on algorithm development and offline validation for cell-level battery state estimation. It is intended as an engineering and research portfolio project, not a production-certified BMS.

Included in scope:

- cell-level lumped electrical modeling;
- offline parameter identification;
- SOC and SOH estimation;
- aging-aware parameter adaptation;
- reproducible robustness experiments;
- transparent comparison of estimation methods.

Outside the initial scope:

- electrochemical models such as P2D/DFN;
- pack-level cell balancing and thermal gradients;
- fault diagnosis and functional-safety certification;
- embedded code generation and real-time hardware deployment;
- charging-control or fast-charging optimization;
- cloud-connected fleet analytics.

## Future Work

Potential extensions include:

- temperature-dependent OCV and ECM parameter maps;
- joint SOC-SOH estimation using dual or augmented filters;
- online recursive parameter identification;
- hysteresis modeling;
- sensor-fault and outlier detection;
- electro-thermal coupling;
- pack-level estimation with cell-to-cell variation;
- comparison with particle filters and moving-horizon estimation;
- embedded implementation and hardware-in-the-loop validation;
- uncertainty calibration and confidence-interval reporting.

## Status

**In development.** The current repository specification defines the modeling assumptions, estimator scope, experiment plan, and reproducibility interface. Implementation, dataset integration, and validated benchmark results are pending.

Until results are generated and verified:

- all numerical performance fields remain `TBD`;
- no accuracy or runtime claim should be inferred from the planned methodology;
- reproduction commands describe the target interface and may change during development;
- no open-source license has been assigned; all rights are reserved unless permission is granted explicitly.

Contributions, issues, and technical discussion will be welcomed after the first reproducible baseline is published.
