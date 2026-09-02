# PyHC ecosystem map
> Which PyHC package answers which need; core-package docs federate at https://heliopython.org/pyhc-docs/.

## What it is / When to use it
PyHC (heliopython.org) curates the field's Python software. Core packages:
**sunpy** (solar data/coords), **pySPEDAS** (mission loaders for in-situ data),
**PlasmaPy** (plasma physics formulary/analysis), **pysat** (satellite data
management), **SpacePy** (space science utilities, CDF, Ap/Kp tooling),
**HAPI client** (standard time-series access), **Kamodo** (model functionalization).

## How to use it (in this system)
- sunpy -> discover/retrieve VSO, GOES XRS, HEK; Maps (`search_vso`, `fetch_goes_xrs`, `plot_solar_map`)
- pySPEDAS -> `fetch_pyspedas` and the two pyspedas discover tools
- PlasmaPy -> `plasma_parameters` (formulary; extend for dispersion/instabilities)
- hapiclient -> `fetch_hapi` (any HAPI server)
- SpacePy -> installed (pyspedas dependency); use for CDF edge cases and magnetic coordinates
- pysat, Kamodo -> not wrapped yet; install pysat via `uv sync --extra extra`.
  Reach for pysat when managing long multi-instrument index/CDF collections;
  Kamodo when comparing data against CCMC model output.
- Other evaluated packages worth knowing: solarmach (spacecraft constellation
  plots), aiapy (AIA calibration), geopack (Tsyganenko fields), OMMBV,
  pyDARN (SuperDARN), viresclient (Swarm). Verify current status on the PyHC
  projects page before depending on one.

## Gotchas and judgment calls
- Do not mix pySPEDAS tplot state with this system's CSV flow mid-analysis;
  fetch to CSV once, then stay in reduce/measure tools.
- Package maturity varies (PyHC publishes evaluations); anything newly wrapped
  here needs a validation case before its numbers are trusted.

## Cross-checks
- New loader results vs an independent path (CDAWeb/HAPI) on the same interval,
  as in validation case `pyspedas`.
