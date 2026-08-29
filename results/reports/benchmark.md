# Synthetic Benchmark Report

> These results use generated data and validate the software pipeline; they are not experimental cell claims.

| Experiment | Method | SOC RMSE [%pt] | SOC MAE [%pt] | Max error [%pt] | Convergence [s] | Runtime [us/sample] |
|---|---|---:|---:|---:|---:|---:|
| synthetic_aged_fixed_benchmark | coulomb_counting | 7.318 | 6.572 | 12.000 | 3245.0 | 4.62 |
| synthetic_aged_fixed_benchmark | ekf | 2.393 | 2.274 | 12.000 | 1.0 | 74.98 |
| synthetic_aged_fixed_benchmark | ukf | 2.339 | 2.214 | 12.000 | 2.0 | 213.48 |
| synthetic_aging_aware_benchmark | coulomb_counting | 12.039 | 12.039 | 12.091 | N/A | 5.21 |
| synthetic_aging_aware_benchmark | ekf | 1.258 | 0.718 | 12.000 | 1.0 | 73.49 |
| synthetic_aging_aware_benchmark | ukf | 0.267 | 0.104 | 12.000 | 2.0 | 225.06 |
| synthetic_soc_benchmark | coulomb_counting | 12.059 | 12.059 | 12.106 | N/A | 4.28 |
| synthetic_soc_benchmark | ekf | 0.712 | 0.289 | 12.000 | 1.0 | 73.63 |
| synthetic_soc_benchmark | ukf | 0.250 | 0.065 | 12.000 | 2.0 | 217.61 |
