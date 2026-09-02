# pySPEDAS and PyTplot
> Mission-aware load routines plus the tplot variable/plot ecosystem — the IDL SPEDAS workflow in Python.

## What it is / When to use it
pySPEDAS provides per-mission load functions (MMS, THEMIS, OMNI, ACE, Wind, PSP, Solar Orbiter, STEREO, GOES, and many more) that download from the right archive, read the CDFs, and register variables in the PyTplot store as "tplot variables". PyTplot then handles multi-panel time-series plotting and variable manipulation. Use it when you want mission data loaded with sensible defaults and quick stacked plots; especially strong for magnetospheric missions (MMS/THEMIS) where it encodes instrument-team knowledge (calibration options, coordinate handling, variable selection).

## How to use it
```python
import pyspedas
from pytplot import tplot, get_data, store_data

trange = ['2024-05-10', '2024-05-12']
pyspedas.projects.omni.data(trange=trange)          # OMNI
pyspedas.projects.ace.mfi(trange=trange)            # ACE magnetometer
pyspedas.projects.mms.fgm(trange=trange, probe='1') # MMS FGM
# (older versions expose pyspedas.omni.data etc. without .projects — check your version)

tplot(['BX_GSE', 'flow_speed'])       # stacked time-series panels
d = get_data('flow_speed')            # namedtuple: d.times (unix), d.y (values)
```
- Data land in a local cache directory (SPEDAS_DATA_DIR env var to control); repeated loads reuse files.
- tplot variables carry plot metadata (labels, ylog, colors) via `options()`/`tplot_options()`.
- Convert to pandas: `pytplot.get_data` + `pd.DataFrame(d.y, index=pd.to_datetime(d.times, unit='s'))`.

## When to prefer it over cdasws
- You want mission-specific defaults (right variables, calibrations, coordinate versions) rather than raw dataset IDs.
- You're making stacked survey plots fast.
- Multi-instrument loads from one mission (MMS especially — its data model is painful raw).
Prefer cdasws/HAPI instead when you need a specific dataset ID reproducibly, minimal dependencies, or datasets pyspedas lacks a routine for (pyspedas also has `pyspedas.cdagui`/generic CDAWeb loaders as a bridge).

## Gotchas and judgment calls
- The tplot store is global mutable state: reloading overwrites variables silently; same-named variables from different probes/missions can collide. Use `varformat`/`prefix`/`suffix` options and check `pytplot.tplot_names()`.
- Load routine defaults may pull quicklook vs L2 depending on `level=` — be explicit.
- Times from get_data are unix seconds (floats) — convert deliberately; sub-second precision loss is possible for ns-cadence data.
- API churn: the `pyspedas.projects.<mission>` namespacing changed across versions; pin the version and verify call signatures.
- Fill values are usually handled (NaN) by the CDF-to-tplot layer, but verify on first use per dataset.
- Downloads can silently fall back to a mirror or fail partially — check the returned variable-name list.

## Cross-checks
- Compare a loaded variable against cdasws/HAPI for the same interval and dataset.
- `tplot()` the raw variable before analysis — spikes/gaps are visible instantly.
- Check the mission team's own quicklook plots (e.g., MMS SDC, THEMIS summary plots) against yours.

## helio-agent integration (added 2026-09-02)
- pySPEDAS 2.x: `pytplot` is merged into the `pyspedas` namespace
  (`from pyspedas import get_data`); loaders live under `pyspedas.projects.<mission>`.
- Agent tools: `list_pyspedas_missions`, `list_pyspedas_loaders`,
  `fetch_pyspedas(mission, instrument, start, end, probe=, datatype=, variables=)`
  -> workspace CSV. Spectrogram-like (>6-column 2-D) variables are skipped;
  they need a dedicated tool if required.
- File cache: SPEDAS_DATA_DIR is pinned to workspace/data/pyspedas.
- Validated: THEMIS-C FGM 2008-02-26 loads; ACE MFI hourly means agree with
  the CDAWeb pipeline to <2% (validation case `pyspedas`).
