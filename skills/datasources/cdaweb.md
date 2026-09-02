# CDAWeb
> NASA's Coordinated Data Analysis Web — the workhorse archive for heliophysics in-situ time series.

## What it is / When to use it
CDAWeb (https://cdaweb.gsfc.nasa.gov), run by NASA GSFC SPDF, serves thousands of datasets from most heliophysics missions (ACE, Wind, OMNI, MMS, THEMIS, STEREO, Solar Orbiter in-situ, Parker Solar Probe, and more) as ISTP-compliant CDF files. Default choice for any archival in-situ plasma, field, or particle time series.

## How to use it
- Python client: `cdasws`.
```python
from cdasws import CdasWs
cdas = CdasWs()
# discover: cdas.get_datasets(observatoryGroup='ACE'); cdas.get_variables('AC_H0_MFI')
status, data = cdas.get_data('AC_H0_MFI', ['Magnitude', 'BGSM'],
                             '2024-05-10T00:00:00Z', '2024-05-12T00:00:00Z')
# data is xarray-like (SpasePy/cdflib backed depending on version); check data.keys()
```
- Dataset ID convention: roughly `<OBSERVATORY>_<LEVEL/CADENCE>_<INSTRUMENT>`, e.g. `AC_H0_MFI` (ACE, H0 = high-res level, MFI magnetometer), `WI_H1_SWE`, `OMNI2_H0_MRG1HR`, `STA_L1_MAG_RTN`. H/K prefixes historically mean high-resolution/key-parameter; treat the ID as opaque and verify via the catalog.
- REST API base: `https://cdaweb.gsfc.nasa.gov/WS/cdasr/1` (e.g. `/dataviews/sp_phys/datasets` to list datasets; `/datasets/<ID>/variables`; data requests return links to generated CDF/text). cdasws wraps this.
- Also exposed via HAPI at `https://cdaweb.gsfc.nasa.gov/hapi` (see hapi skill) — often simpler for plain time-series pulls.
- Web GUI is useful for interactive discovery and quicklook plots before scripting.

## Gotchas and judgment calls
- Fill values: mask FILLVAL (typically -1.0e31) before arithmetic — cdasws/cdflib may or may not have done it depending on version and options. An average near -1e29 means you didn't.
- Variable names are per-dataset and inconsistent across missions (`BGSM` vs `B_GSM` vs `bgsm`); always list variables first.
- Some datasets have multiple cadence/level variants (H0/H1/H2/K0/K1); K (key parameter) products are quicklook quality — prefer H/L2 for science.
- Coverage lags: L2 data appear days to months after observation. For near-real-time, use NOAA SWPC or low-latency sources instead.
- Large requests time out or get chunked; loop over daily/weekly chunks for long intervals.
- Units and coordinate frames live in CDF variable attributes — read them, don't assume nT/GSE.

## Cross-checks
- Pull the same dataset via the CDAWeb HAPI endpoint or pyspedas and compare values.
- Compare a merged product (OMNI) against its source dataset (e.g., ACE MFI) for the same interval, remembering OMNI's time shift.
- Spot-check against the CDAWeb web-GUI plot for the same interval — fast way to confirm your masking and units.
