# CDF Files
> Reading NASA Common Data Format files with cdflib, and the ISTP conventions that make them self-describing.

## What it is / When to use it
CDF is the standard container for heliophysics in-situ data. ISTP/IACG guidelines standardize the metadata so files are machine-interpretable. Use this skill whenever handling .cdf files directly (downloaded from CDAWeb/SPDF) instead of through a client that hides them.

## How to use it
```python
import cdflib
cdf = cdflib.CDF('ac_h0_mfi_20240510_v06.cdf')
info = cdf.cdf_info()                 # zVariables list, etc.
bgsm = cdf.varget('BGSM')             # data array
att  = cdf.varattsget('BGSM')         # per-variable attributes dict
epoch_name = att['DEPEND_0']          # the time variable for BGSM
epochs = cdf.varget(epoch_name)
times = cdflib.cdfepoch.to_datetime(epochs)   # handles CDF_EPOCH/EPOCH16/TT2000
```
- ISTP conventions that matter:
  - `DEPEND_0`: names the epoch variable for each record-varying variable — never assume all variables share one time axis.
  - `DEPEND_1`(+): the bin axis for spectrograms (energies, pitch angles).
  - `FILLVAL`: sentinel for missing data (commonly -1.0e31 for floats). Also `VALIDMIN`/`VALIDMAX` for range screening.
  - `UNITS`, `CATDESC`, `LABLAXIS`, `FIELDNAM`: units and human labels — use them in plots.
  - `VAR_TYPE`: 'data' vs 'support_data' vs 'metadata' — iterate 'data' variables when dumping a file.
- To pandas:
```python
import numpy as np, pandas as pd
v = cdf.varget('BGSM').astype(float)
v[v == att['FILLVAL']] = np.nan       # or np.isclose for float fills
df = pd.DataFrame(v, index=pd.to_datetime(times), columns=['Bx','By','Bz'])
```
- `cdflib.cdf_to_xarray('file.cdf', to_datetime=True)` builds an xarray Dataset with attributes attached — often the fastest correct path.

## Gotchas and judgment calls
- Epoch types: CDF_EPOCH (ms since year 0), CDF_EPOCH16, CDF_TT2000 (ns since J2000, leap-second aware). Let `cdfepoch` convert; hand-rolled conversions off by ~32-37 s or by the year-0 offset are classic bugs.
- Fill comparison on floats: use `np.isclose(v, fillval)` or `v <= -1e30`, not `==`, after any dtype conversion.
- Virtual/computed variables exist in some CDAWeb products; cdflib reads only what's in the file — CDAWeb-generated CDFs may differ from mission originals.
- Multi-day analyses need concatenation across daily files; watch for version differences (v05 vs v06) within a span — prefer the highest version per day.
- Row vs column majority and pad values rarely bite via cdflib, but spectrogram DEPEND_1 can be time-varying (2D) — check its shape.

## Cross-checks
- Compare a day's values against the CDAWeb GUI plot for the same variable.
- Round-trip check: cdflib vs `cdf_to_xarray` vs cdasws for one variable.
- After fill-masking, confirm min/max fall within VALIDMIN/VALIDMAX.
