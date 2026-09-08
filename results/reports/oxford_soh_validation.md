# Oxford Measured SOH Validation

Eight 740 mAh pouch cells, characterized every 100 cycles at 40 C.

- Mean initial measured capacity: 733.44 mAh
- Mean final capacity retention: 75.50% of initial measured capacity
- Mean final rated-capacity SOH: 74.82% of 740 mAh rated capacity
- Mean final resistance factor: 1.704x
- Linear 60/40 holdout RMSE: 2.847 percentage points
- Quadratic 60/40 holdout RMSE: 1.908 percentage points

Capacity retention is relative to each cell's first measured 1C discharge capacity. Rated-capacity SOH is `capacity_mAh / 740 mAh * 100`. Effective resistance is estimated from the voltage difference between aligned 1C and pseudo-OCV discharge curves over 20-80% depth of discharge.
