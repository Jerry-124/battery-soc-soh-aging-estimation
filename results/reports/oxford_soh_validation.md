# Oxford Measured Aging Validation

## Scope

Eight 740 mAh Kokam pouch cells are evaluated using the Oxford Battery Degradation Dataset 1. Characterization is performed every 100 cycles at 40 °C.

## Key Results

| Quantity | Value |
|---|---:|
| Mean initial measured capacity | 733.44 mAh |
| Mean final capacity retention | 75.50% of first measured capacity |
| Mean final rated-capacity SOH | 74.82% of 740 mAh |
| Mean final resistance factor | 1.704× |
| Linear 60/40 holdout RMSE | 2.847 %pt |
| Quadratic 60/40 holdout RMSE | 1.908 %pt |

## Interpretation

Capacity retention is normalized by each cell's first measured 1C discharge capacity. Rated-capacity SOH is calculated separately as `capacity_mAh / 740 mAh * 100`. Effective resistance is estimated from the voltage difference between aligned 1C and pseudo-OCV discharge curves over 20–80% depth of discharge.

The two capacity metrics intentionally use different denominators and are not treated as interchangeable definitions of SOH.