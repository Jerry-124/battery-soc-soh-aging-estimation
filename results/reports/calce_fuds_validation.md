# CALCE Measured-Data Validation

## Scope

ECM identification uses CALCE DST data at nominal 80% SOC and 25 °C. Independent SOC validation uses CALCE FUDS data at nominal 80% SOC and 25 °C.

## Key Results

| Quantity | Value |
|---|---:|
| Measured initial capacity | 2.0283 Ah |
| Reference initial SOC | 80.28% |
| Estimator initial SOC | 70.28% |
| Full-state open-loop voltage RMSE | 22.38 mV |
| Reference-SOC-conditioned voltage RMSE | 22.38 mV |

| Method | SOC RMSE | SOC MAE | Max Error | Final Error | Runtime |
|---|---:|---:|---:|---:|---:|
| Coulomb Counting | 9.648 %pt | 9.533 %pt | 10.000 %pt | -1.558 %pt | 9.64 µs/sample |
| EKF | 0.740 %pt | 0.617 %pt | 10.000 %pt | -0.882 %pt | 188.72 µs/sample |
| UKF | 0.849 %pt | 0.717 %pt | 10.000 %pt | -0.856 %pt | 376.78 µs/sample |

## Interpretation

The SOC reference is constructed by integrating measured current from the capacity-derived initial SOC. The full-state open-loop and reference-SOC-conditioned voltage RMSE values are numerically equal in this configuration because both recursions use the same initial SOC, measured current, measured capacity, unit coulombic efficiency, and clipping behavior; they remain separately reported because their definitions differ.