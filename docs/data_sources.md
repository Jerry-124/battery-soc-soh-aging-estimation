# Data Sources

## CALCE INR18650-20R measured validation data

The measured validation pipeline uses open experimental data published by the Center for Advanced Life Cycle Engineering (CALCE), University of Maryland.

- Source page: https://calce.umd.edu/data
- Cell: Samsung INR18650-20R
- Chemistry: NMC/graphite
- Rated capacity: 2.0 Ah
- Temperature used here: 25 degrees Celsius
- OCV data: incremental-current OCV test, sample SP20-1
- Identification profile: DST, sample SP20-2, nominal 80% SOC
- Independent validation profile: FUDS, sample SP20-2, nominal 80% SOC
- Capacity reference: initial capacity test, sample SP20-2

CALCE requests that publications using the data cite the associated experimental articles listed on its data page. The raw files are not committed to this repository. Run `scripts/download_calce_data.py` to obtain them directly from the official source.

The OCV file and dynamic profiles come from different cells of the same model. A fitted OCV voltage bias is therefore included during ECM identification. This cross-cell difference is a real source of model uncertainty and is reported explicitly.

## Oxford measured aging data

The measured SOH pipeline uses Oxford Battery Degradation Dataset 1.

- Repository: https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac
- DOI: 10.5287/bodleian:KO2kdmYGg
- License: ODC Open Database License (ODbL)
- Cells: 8 Kokam SLPB533459H4 lithium-ion pouch cells
- Rated capacity: 740 mAh
- Test temperature: 40 degrees Celsius
- Characterization: 1C and pseudo-OCV tests every 100 cycles

The 253.8 MB raw MATLAB file is downloaded from Oxford and SHA-256 verified, but is not committed or redistributed in this repository.

## CALCE CX2-3 full-life pulse-aging data

- Official archive: https://web.calce.umd.edu/batteries/data/CX2_3.zip
- Cell: CX2-3 lithium cobalt oxide pouch cell
- Archive size: 425,523,304 bytes
- SHA-256: `1a1d8c2aecba147c398ae9d6e1305a677dadba98b89accb65753ddbdfb51c330`
- Coverage used here: 61 dated exports containing 1,185 sampled complete diagnostic cycles
- Capacity: full-discharge capacity increment
- Pulse resistance: rest-end to first 5-second 0.5C-pulse voltage change divided by the measured current step

Raw workbooks are not committed or redistributed. The complete failure region is retained in the measured health curve. The SOC observer comparison uses the operational checkpoint nearest 70% capacity SOH and is labeled semi-empirical because the health factors are measured while the dynamic voltage/SOC trajectory is simulated.
