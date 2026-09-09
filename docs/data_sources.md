# Data Sources

This repository uses public battery datasets for reproducible validation. Raw experimental files are downloaded from the original providers and are not redistributed here.

## CALCE INR18650-20R Measured Validation Data

The SOC-validation pipeline uses open experimental data published by the Center for Advanced Life Cycle Engineering (CALCE), University of Maryland.

- Source: <https://calce.umd.edu/data>
- Cell: Samsung INR18650-20R
- Chemistry: NMC/graphite
- Rated capacity: 2.0 Ah
- Temperature: 25 °C
- OCV characterization: incremental-current OCV test, sample SP20-1
- ECM identification: DST, sample SP20-2, nominal 80% SOC
- Independent SOC validation: FUDS, sample SP20-2, nominal 80% SOC
- Capacity reference: initial-capacity test, sample SP20-2

CALCE requests that publications using these data cite the associated experimental articles listed on its data page. Run `scripts/download_calce_data.py` to obtain the required files directly from the official source.

The OCV characterization and dynamic profiles come from different cells of the same model. A fitted OCV voltage bias is therefore included during ECM identification. The remaining cross-cell difference is treated as a real source of model uncertainty and is reported explicitly.

## Oxford Measured Aging Data

The measured aging pipeline uses Oxford Battery Degradation Dataset 1.

- Repository: <https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac>
- DOI: `10.5287/bodleian:KO2kdmYGg`
- License: ODC Open Database License (ODbL)
- Cells: eight Kokam SLPB533459H4 lithium-ion pouch cells
- Rated capacity: 740 mAh
- Test temperature: 40 °C
- Characterization: 1C and pseudo-OCV tests every 100 cycles

The approximately 254 MiB MATLAB file is downloaded from Oxford, verified against its expected SHA-256 digest, and excluded from Git.

Capacity retention is normalized by each cell's first measured 1C discharge capacity. Rated-capacity SOH is reported separately using the 740 mAh rated capacity. These denominators are intentionally kept distinct.

## CALCE CX2-3 Full-Life Pulse-Aging Data

- Official archive: <https://web.calce.umd.edu/batteries/data/CX2_3.zip>
- Cell: CX2-3 lithium cobalt oxide pouch cell
- Archive size: 425,523,304 bytes
- SHA-256: `1a1d8c2aecba147c398ae9d6e1305a677dadba98b89accb65753ddbdfb51c330`
- Coverage: 61 dated exports containing 1,185 sampled complete diagnostic cycles
- Capacity metric: full-discharge capacity increment, normalized to the first measured diagnostic value
- Pulse-resistance metric: voltage change from the end of the 10-second rest to the first 5-second sample of the 0.5C pulse, divided by the measured current step

Raw workbooks are not committed or redistributed. The complete failure region is retained in the measured health curve. The SOC-observer comparison uses the operational checkpoint nearest a **0.70 capacity-retention factor** and is labeled semi-empirical because the health factors are measured while the dynamic voltage/SOC trajectory is simulated.