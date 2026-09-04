# SSCWeb
> Satellite Situation Center — ephemeris (positions) for ~200 heliophysics-relevant spacecraft, plus conjunction finding.

## What it is / When to use it
SSCWeb (https://sscweb.gsfc.nasa.gov, NASA GSFC/SPDF) serves orbit/location data for a couple hundred current and past spacecraft (magnetospheric, L1, lunar, heliospheric). Use it for: where was spacecraft X at time T, in what frame; which spacecraft were in region Y; radial-alignment and magnetic-conjunction searches for cross-spacecraft studies. It is for POSITIONS, not instrument data.

## How to use it
- Python client: `sscws`.
```python
from sscws.sscws import SscWs
ssc = SscWs()
obs = ssc.get_observatories()          # list valid IDs, e.g. 'ace', 'wind', 'themisa'
result = ssc.get_locations(['ace', 'dscovr'],
                           ['2024-05-10T00:00:00Z', '2024-05-11T00:00:00Z'])
# result['Data'][i]['Coordinates'] -> X/Y/Z arrays, km, GSE by default
```
- Coordinate options: GEO, GM, GSE, GSM, SM, GEI/J2000 — selectable in the request; distances in km or Earth radii. For heliocentric frames (spacecraft far from Earth), SSCWeb still works for many craft but consider SPICE kernels (spiceypy) for PSP/Solar Orbiter precision work.
- Conjunction/region queries: the web GUI ("Query" for region occupancy, magnetic conjunctions using field models like Tsyganenko) is the mature interface; sscws exposes conjunction queries too (verify via sscws docs for the call shape).
- Also exposed via a HAPI endpoint (see hapi skill) for plain position time series.

## Gotchas and judgment calls
- Observatory IDs are lowercase and sometimes non-obvious ('themisa', 'stereoa'); list observatories first rather than guessing.
- Ephemeris is predictive for future/recent times and definitive later; positions for "tomorrow" are propagated, fine for planning, not for precision timing.
- Resolution: returned cadence varies per spacecraft (often 1-12 min interpolatable spline points); don't expect meter-level accuracy — this is km-class ephemeris.
- Magnetic conjunctions depend entirely on the chosen field model (dipole vs Tsyganenko variants) and activity inputs; a "conjunction" under T89 quiet may vanish under storm conditions.
- Units confusion: km vs Re — check the requested units flag before computing separations.

## Cross-checks
- Cross-check a position against the mission's own SPICE kernels (spiceypy) or the ephemeris in the mission's CDF support data (many CDAWeb datasets carry position variables).
- L1 spacecraft sanity check: ACE/Wind/DSCOVR should sit near X_GSE ~ +230-260 Re with |Y|,|Z| up to ~40-100 Re halo excursions.
- For conjunction claims, verify with a second field model and state both.

## Input pin (added 2026-09-04)
`fetch_spacecraft_ephemeris` goes through `sscws`, a library-managed transfer the repo's HTTP cache does not cover. SSCWeb **recomputes positions from orbit files that get revised**, so a predictive-to-definitive switch would move `ephemeris.ace_l1` with nothing to notice.

`validation/run_validation.py libpins` pins the ACE 2017-09-05 query: CSV SHA-256 `a2266bd5…` (the whole trajectory, not a summary statistic), 121 points, the three column names, and the mean GSE X/Y/Z to 1e-9 relative. Verified meaningful by deleting the CSV and re-querying SSCWeb, which rewrote it identically. Verified to trip by perturbing the checksum.
