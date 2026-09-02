# VSO (Virtual Solar Observatory)
> Federated search/download across solar data archives — the sunpy Fido route to SDO, SOHO, and ground-based solar data.

## What it is / When to use it
VSO (https://sdac.virtualsolar.org) is a broker that searches many solar archives (SDAC, NSO, and others) with one query. In practice you use it through `sunpy.net.Fido`, which queries VSO (and other clients) transparently. Use for solar remote-sensing data: AIA/HMI (small volumes), EIT, LASCO, MDI, ground-based H-alpha/magnetograms.

## How to use it
```python
from sunpy.net import Fido, attrs as a
import astropy.units as u
res = Fido.search(a.Time('2024-05-10 06:00', '2024-05-10 06:10'),
                  a.Instrument.aia, a.Wavelength(171 * u.angstrom),
                  a.Sample(60 * u.s))          # thin the cadence!
files = Fido.fetch(res, path='./data/{instrument}/')
```
- Key attrs: `a.Time`, `a.Instrument` (aia, hmi, lasco, eit, ...), `a.Wavelength`, `a.Sample` (cadence decimation), `a.Physobs` (e.g. 'los_magnetic_field' for HMI magnetograms), `a.Detector` (C2/C3 for LASCO), `a.Provider`.
- Inspect `res` before fetching — it prints a table with counts and sizes.
- Bulk AIA/HMI: VSO is the wrong tool for large volumes. Use JSOC (http://jsoc.stanford.edu) via `drms` or Fido's JSOC client (`a.jsoc.Series('aia.lev1_euv_12s')`, `a.jsoc.Notify('you@example.com')` — JSOC requires a registered email export address). JSOC serves the canonical HMI/AIA series and does server-side processing (aia_prep-equivalent, cutouts).

## Gotchas and judgment calls
- AIA full cadence is 12 s per EUV channel at 4096x4096 (~10 MB+ compressed per image) — an unconstrained day-long query is tens of thousands of files. ALWAYS use `a.Sample` or tight time windows.
- Fido queries can return duplicate records from multiple providers; dedupe or select a provider.
- VSO availability wobbles; failed searches may be provider outages, not empty archives — retry, and remember Helioviewer as a browse alternative and JSOC as the AIA/HMI source of truth.
- AIA lev1 needs pointing/PSF corrections and exposure normalization for photometry (`aiapy` for calibration); off-the-shelf JP2/browse images are NEVER photometric.
- LASCO via VSO is level-0.5-ish; CDAW-catalog-grade work uses calibrated processing.
- HMI magnetograms: choose the right series (45 s vs 720 s; line-of-sight vs vector) — physobs and series names matter.

## Cross-checks
- Verify image times/pointing by overlaying limb/grid with sunpy Map (`map.peek()`); confirm a feature seen in AIA appears in the Helioviewer browse image at the same time.
- Compare file counts against the instrument's expected cadence — big shortfalls mean data gaps (eclipse seasons, calibration) or an incomplete provider.
- For HMI, cross-check the daily sunspot picture against NOAA SWPC active region maps.
