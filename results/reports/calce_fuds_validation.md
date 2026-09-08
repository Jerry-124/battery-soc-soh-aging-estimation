# CALCE Measured-Data Validation

Identification: DST 80% SOC at 25 C. Independent validation: FUDS 80% SOC at 25 C.

Measured initial capacity: 2.0283 Ah
Reference initial SOC: 80.28%
Estimator initial SOC: 70.28%
Independent FUDS full-state open-loop voltage RMSE: 22.38 mV
Independent FUDS reference-SOC-conditioned voltage RMSE: 22.38 mV

| Method | SOC RMSE [%pt] | SOC MAE [%pt] | Max error [%pt] | Final error [%pt] | Runtime [us/sample] |
|---|---:|---:|---:|---:|---:|
| coulomb_counting | 9.648 | 9.533 | 10.000 | -1.558 | 9.64 |
| ekf | 0.740 | 0.617 | 10.000 | -0.882 | 188.72 |
| ukf | 0.849 | 0.717 | 10.000 | -0.856 | 376.78 |

The SOC reference is constructed by integrating measured current from the capacity-derived initial SOC.
