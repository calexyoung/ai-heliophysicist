# NOAA SWPC Real-Time Data
> Operational, real-time space weather feeds from the NOAA Space Weather Prediction Center — freshest data, operational-grade caveats.

## What it is / When to use it
SWPC (https://www.swpc.noaa.gov) runs the US operational space weather service. Its data services host (https://services.swpc.noaa.gov) provides no-auth JSON/text feeds updated in near-real time. Use for: current conditions, the last few days of GOES X-rays / Kp / solar wind, alerts, and anything where CDAWeb's latency (days+) is unacceptable.

## How to use it
- Browse https://services.swpc.noaa.gov/json/ and /products/ and /text/ directly — they are plain directory listings; the reliable way to find current feed paths.
- Useful JSON endpoints (verify paths in the listing if a 404 appears; SWPC reorganizes occasionally):
  - GOES XRS: `/json/goes/primary/xrays-1-day.json`, `xrays-7-day.json` (flux vs time, both channels).
  - Planetary K index: `/json/planetary_k_index_1m.json`; also `/products/noaa-planetary-k-index.json`.
  - Real-time solar wind (RTSW, from DSCOVR/ACE): `/products/solar-wind/mag-1-day.json`, `/products/solar-wind/plasma-1-day.json`.
  - Alerts/watches/warnings: `/products/alerts.json`.
  - Solar regions, proton flux, electron flux under `/json/goes/...` and `/json/solar_regions.json`.
- `/products/` JSON is typically a list-of-lists with a header row; `/json/` endpoints are lists of objects. Timestamps are UTC.
```python
import requests, pandas as pd
d = requests.get('https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json').json()
df = pd.DataFrame(d); df['time_tag'] = pd.to_datetime(df['time_tag'])
xl = df[df['energy'] == '0.1-0.8nm']   # long channel for flare class
```

## Gotchas and judgment calls
- Operational vs science data: RTSW and real-time GOES feeds are minimally processed, can contain spikes, gaps, and preliminary calibrations, and are later superseded by science products (NCEI for GOES, CDAWeb/OMNI for solar wind). Fine for "what's happening now", not for publishable quantitative analysis — say which grade you used.
- Feeds are rolling windows (1-day/3-day/7-day); historical data must come from NCEI/CDAWeb, not SWPC.
- Estimated (real-time) Kp here differs from GFZ definitive Kp.
- The XRS JSON mixes both channels in one list keyed by `energy` — filter before computing flare class.
- Rate-limit yourself politely; feeds update at 1-min cadence, polling faster is pointless.

## Cross-checks
- Flare classes vs the SWPC event list and (later) GOES science data.
- RTSW vs OMNI/L1 science data once available (expect small differences).
- Kp vs GFZ Potsdam definitive values after a few days.

## Tool: `get_sunspot_reports` (added 2026-09-04)
- Wraps `/json/sunspot_report.json`: the **raw per-observatory** sunspot classifications (HOL, SVI, LEA), rolling ~1 month, about 400 rows. `get_solar_regions` is the **edited** daily summary — one authoritative class per region. Use the edited product for "the" class; use this for history and for how uncertain that class is.
- Two uses: **yesterday's Zurich class** for `flare_probability` (whose rates are evolution-indexed), and an honest spread on today's class.
- **Observatories disagree a lot**: 65% of region-days carry more than one McIntosh class, 35% more than one Mount Wilson class, and 19% are Zurich ties. A tie leaves `zurich_consensus` None rather than picking — the two candidates can differ by 4x in flare probability.
- The edited summary is **not** a straight vote of these reports. On 2026-09-04 both stations reported AR 4523 as `Hsx` while the edited summary said `Cao`. Do not reconstruct the edited class from station reports.
- Records with a null `Region` (unnumbered groups) are dropped and counted in `skipped_unnumbered`; `ValidSpotClass = 0` rows are excluded. `Quality` (1-4) is the station's own confidence, not accuracy — `min_quality` defaults to 0 because filtering quietly narrows the disagreement this tool exists to show.
- Rolling window only. A date outside it refuses and names the coverage; older data needs a different archive.
- Validation: `uv run python validation/run_validation.py sunspots`.

### The position-epoch trap (cost a wrong figure on 2026-09-04)
**SWPC region `location` is the position at 2400 UT of `observed_date`, not 0000 UT.** Every station measurement is rotated forward to the end of the report day, so the coordinates lead the date stamp by a full 24 hours. Plot them on an image taken at 0000 UT of that date and every region sits **~14.5° too far west** — about a quarter of a solar radius near disk centre, and obvious to anyone who knows the Sun.

Determined from the feed, not assumed: regressing `Location` against `Report_Location` and `Obstime` over 388 station reports gives a correction epoch of **24.07 h** after 0000 UT and a rotation rate of **14.50°/day**, rms 0.27° (reported longitudes are integers). Pinned by `validation/run_validation.py sunspots`.

- `get_solar_regions` exposes `coordinates_epoch` for this; `plot_solar_regions` uses it automatically. Never match an image against `observed_date`.
- Note 14.50°/day is SWPC's own correction rate, faster than the 13.2°/day synodic equatorial value — use it when estimating drift for SWPC-sourced positions.
- **Cleanest option: skip the correction entirely.** `get_sunspot_reports` returns `report_location` with `obs_time` — the raw measurement at a known instant. Match an image to `obs_time` and there is no epoch to get wrong.
