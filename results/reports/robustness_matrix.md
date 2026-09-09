# Robustness Matrix

## Scope

All cases use the same measured-aging-informed checkpoint and an independent synthetic dynamic profile. Each uncertainty family is varied separately.

## Key Results

| Uncertainty Family | EKF Mean Post-300 s RMSE | EKF Worst Post-300 s RMSE | UKF Mean Post-300 s RMSE | UKF Worst Post-300 s RMSE |
|---|---:|---:|---:|---:|
| Initial SOC error | 0.844 %pt | 1.524 %pt | 0.659 %pt | 0.969 %pt |
| Measurement noise | 0.992 %pt | 1.445 %pt | 0.613 %pt | 0.701 %pt |
| Parameter uncertainty | 3.344 %pt | 8.350 %pt | 3.631 %pt | 8.944 %pt |

## Interpretation

Initial-SOC and measurement-noise perturbations remain comparatively well controlled after convergence. Parameter uncertainty is substantially more damaging and is intentionally retained in the benchmark because it quantifies the motivation for better identification and aging-aware adaptation.