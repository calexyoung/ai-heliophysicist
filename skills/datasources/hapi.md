# HAPI (Heliophysics Application Programmer's Interface)
> A standard REST interface for time-series data adopted by many heliophysics servers — one client, many archives.

## What it is / When to use it
HAPI is a community specification: any compliant server exposes `/catalog` (dataset list), `/info` (parameter metadata), and `/data` (the time series, CSV or binary) with a uniform request/response format. Use it when you want simple, uniform time-series access without learning each archive's bespoke API — great for agent pipelines because discovery and retrieval look identical everywhere.

## How to use it
- Known servers include:
  - CDAWeb: `https://cdaweb.gsfc.nasa.gov/hapi`
  - SSCWeb (positions): `https://sscweb.gsfc.nasa.gov/hapi` — verify path via the server's `/about` or the hapi-server.org registry.
  - Others exist (CCMC ISWA, ESA, University of Iowa das2, INTERMAGNET-adjacent) — the community keeps a server list at hapi-server.org; verify there.
- Python client: `hapiclient` (see the hapiclient tool skill for detail).
```python
from hapiclient import hapi
server  = 'https://cdaweb.gsfc.nasa.gov/hapi'
dataset = 'OMNI_HRO_1MIN'
params  = 'flow_speed,BZ_GSM'      # comma-separated, from /info
data, meta = hapi(server, dataset, params,
                  '2024-05-10T00:00:00Z', '2024-05-12T00:00:00Z')
# data is a numpy structured array; data['Time'] are ISO byte strings
```
- Raw REST equivalent: `<server>/data?id=<dataset>&parameters=<p1,p2>&time.min=...&time.max=...&format=csv`.
- Discovery pattern: GET `/catalog`, pick an id, GET `/info?id=...` to see parameters, units, fill values, cadence, and time coverage — then request data.

## Gotchas and judgment calls
- Fill values are declared per-parameter in `/info` (`fill` field, often "-1.0E31") but delivered literally in the data — you still must mask them.
- Times are ISO 8601 strings (variable precision); parse to datetime64 explicitly. time.min is inclusive, time.max exclusive by spec.
- Dataset ids on a HAPI front-end usually match the native archive's ids (CDAWeb HAPI uses CDAWeb ids, sometimes with @N suffixes for multi-cadence datasets — check the catalog).
- Long requests: servers impose duration limits; chunk long intervals. Binary format is much faster than CSV for high-cadence data.
- HAPI serves numbers + minimal metadata; rich ISTP attributes (coordinate system notes, labels) may be thinner than in the source CDFs — consult the native archive docs for interpretation.

## Cross-checks
- Pull the same interval from the native interface (cdasws for CDAWeb) and diff values — should be identical.
- Check `/info` cadence and coverage against what you received (gap vs truncation).
- Validate an unfamiliar server with a known dataset/event before trusting it in a pipeline.

## ISWA (CCMC) HAPI server — added 2026-09-04
`https://iswa.ccmc.gsfc.nasa.gov/IswaSystemWebApp/hapi` (also reachable as `iswa.gsfc.nasa.gov/IswaSystemWebApp/hapi` and `iswa.ccmc.gsfc.nasa.gov/hapi`). **Works through the existing `fetch_hapi` tool with no new code.**

- **322 datasets.** The distinctive content is CCMC *model output* the repo has nothing else for: WSA-ENLIL, SWMF (2008/2011/2023 real-time Dst, magnetopause standoff, field at GOES and THEMIS), OpenGGCM, Tsyganenko field at GEO. Plus real-time GOES X-ray/particle/magnetometer, ACE EPAM/SIS, and IMAP I-ALiRT.
- Parameter names are ISWA's own — `goesp_xray_flux_P1M` is `Short_Wave` / `Long_Wave`, **not** the GOES `xrsa`/`xrsb` or SWPC `A_FLUX`/`B_FLUX`. Hit `/info?id=<dataset>` first; a wrong name fails with `HAPIError: Parameter ... is not in metadata`.
- Coverage is long for the RT feeds: `goesp_xray_flux_P1M` runs 2010-04-13 to the current minute.
- **Real-time and model output, not a science archive** (contract point 7). Cross-check against GOES science data or OMNI before quoting.
- Cross-check that passed: ISWA `goesp_xray_flux_P1M` peaked at 1.238e-5 W/m^2 at 2026-09-04 07:53 UT — M1.24 at 07:53, matching SpaceWeatherLive's independent flare list exactly.
- Note the SDO images on `sdo.gsfc.nasa.gov` and the ISWA data feeds are **JPG/PNG browse products, not FITS** — no WCS, so they cannot back `plot_solar_regions` or any measurement.
