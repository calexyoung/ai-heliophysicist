# HEK (Heliophysics Event Knowledgebase)
> Searchable catalog of solar events and features (flares, CMEs, active regions, coronal holes...) hosted at LMSAL.

## What it is / When to use it
HEK (https://www.lmsal.com/hek/) aggregates event/feature detections from many "feature recognition methods" (FRMs) — some human (SWPC forecasters, SSW Latest Events), most automated pipelines running on SDO and other data. Use it to find events in a time range, get flare positions/AR numbers, coronal hole boundaries, filament eruptions, etc.

## How to use it
- Via sunpy Fido:
```python
from sunpy.net import Fido, attrs as a
res = Fido.search(a.Time('2024-05-10', '2024-05-11'),
                  a.hek.EventType('FL'),
                  a.hek.FL.GOESCls > 'M1.0')
tbl = res['hek']   # astropy table: event_starttime, event_peaktime, hpc_x/y, ar_noaanum, frm_name...
```
- Common event type codes: FL (flare), CE (CME), AR (active region), CH (coronal hole), FI (filament), FE (filament eruption), EF (emerging flux), SG (sigmoid), OS (oscillation). Full list in the HEK docs / `a.hek` attrs.
- Filter by FRM with `a.hek.FRM.Name == '...'` — critical, see below.
- Positions come in helioprojective (hpc_x/hpc_y, arcsec) and heliographic fields; couple with sunpy coordinates to overlay on maps.
- Raw API: the her/HEK web service at lmsal takes URL queries returning JSON — sunpy wraps it; use sunpy unless you have a reason.

## Gotchas and judgment calls
- Provenance is everything: the same physical flare appears multiple times from different FRMs with different times/positions. Always check `frm_name` and dedupe before counting events — naive counts overestimate by factors.
- Automated FRMs have characteristic failure modes: spurious small detections, merged/split events, coverage gaps when their upstream pipeline was down. An absence in HEK is weak evidence of absence.
- Human-curated flare entries (SWPC) are the closest to "official" for GOES flares; automated flare detections may disagree on class/timing.
- CE (CME) entries in HEK are NOT the CDAW catalog; for CME kinematics prefer CDAW/DONKI (see cme_analysis).
- Comparison operators on attrs (like GOESCls) do string-ish comparisons — verify edge behavior (e.g., 'C9.9' vs 'M1.0') on a known sample.
- Coordinates are as-detected at the FRM's observation time; rotate to a common time before cross-matching features (sunpy `propagate_with_solar_surface` or RotatedSunFrame).

## Cross-checks
- Cross-check flares against the GOES XRS time series directly and the DONKI FLR list.
- Cross-check AR numbers/locations against NOAA SWPC's daily Solar Region Summary.
- For any automated detection you care about, pull the actual imagery (Helioviewer/AIA) at the reported time and look.
