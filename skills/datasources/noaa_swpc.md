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
