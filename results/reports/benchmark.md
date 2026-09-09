# Synthetic SOC Benchmark

## Scope

These results use generated data to validate the estimator pipeline and controlled aging-mismatch scenarios. They are not experimental-cell performance claims.

## Key Results

| Scenario | Method | SOC RMSE | SOC MAE | Max Error | Convergence | Runtime |
|---|---|---:|---:|---:|---:|---:|
| Aged, fixed parameters | Coulomb Counting | 7.318 %pt | 6.572 %pt | 12.000 %pt | 3245 s | 4.62 µs/sample |
| Aged, fixed parameters | EKF | 2.393 %pt | 2.274 %pt | 12.000 %pt | 1 s | 74.98 µs/sample |
| Aged, fixed parameters | UKF | 2.339 %pt | 2.214 %pt | 12.000 %pt | 2 s | 213.48 µs/sample |
| Aged, adapted parameters | Coulomb Counting | 12.039 %pt | 12.039 %pt | 12.091 %pt | N/A | 5.21 µs/sample |
| Aged, adapted parameters | EKF | 1.258 %pt | 0.718 %pt | 12.000 %pt | 1 s | 73.49 µs/sample |
| Aged, adapted parameters | UKF | 0.267 %pt | 0.104 %pt | 12.000 %pt | 2 s | 225.06 µs/sample |
| Nominal | Coulomb Counting | 12.059 %pt | 12.059 %pt | 12.106 %pt | N/A | 4.28 µs/sample |
| Nominal | EKF | 0.712 %pt | 0.289 %pt | 12.000 %pt | 1 s | 73.63 µs/sample |
| Nominal | UKF | 0.250 %pt | 0.065 %pt | 12.000 %pt | 2 s | 217.61 µs/sample |

## Interpretation

The synthetic benchmark isolates estimator behavior under controlled initial-SOC error and parameter mismatch. Measured-data validation is reported separately for CALCE and Oxford datasets.