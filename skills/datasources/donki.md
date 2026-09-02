# DONKI
> NASA CCMC's Space Weather Database Of Notifications, Knowledge, Information — human-curated space weather event catalog with linkages.

## What it is / When to use it
DONKI (https://ccmc.gsfc.nasa.gov/tools/DONKI/) is maintained by CCMC's space weather forecasting team. It catalogs flares, CMEs (with 3D cone analyses and ENLIL model runs), SEP events, interplanetary shocks, geomagnetic storms, and high-speed streams — with explicit LINKS between them (this CME -> that shock -> that storm). Forecast-oriented and human-curated. Use it for event context, cause-effect chains, and CME 3D parameters; it's the best single place to ask "what caused this storm?"

## How to use it
- Two API routes, same data:
  - Public via api.nasa.gov: `https://api.nasa.gov/DONKI/<endpoint>?startDate=2024-05-01&endDate=2024-05-15&api_key=DEMO_KEY` (rate-limited; get a free key).
  - Direct CCMC: `https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get/<endpoint>?startDate=...&endDate=...` (no key; verify current hostname if it fails — CCMC URLs migrate).
- Endpoints: `FLR` (flares), `CME`, `CMEAnalysis` (cone params: latitude, longitude, halfAngle, speed, time21_5 — parameters at 21.5 Rs used as ENLIL input), `GST` (geomagnetic storms with Kp entries), `IPS` (interplanetary shocks), `SEP`, `MPC` (magnetopause crossings), `RBE` (radiation belt enhancements), `HSS` (high speed streams), `WSAEnlilSimulations`, `notifications`.
- Dates are `YYYY-MM-DD`. Responses are JSON; events carry `activityID` (e.g., `2024-05-08T05:36:00-CME-001`) and `linkedEvents` arrays — walk these for causal chains.
```python
import requests
r = requests.get('https://api.nasa.gov/DONKI/CMEAnalysis',
                 params={'startDate':'2024-05-07','endDate':'2024-05-12',
                         'mostAccurateOnly':'true','api_key':'DEMO_KEY'})
```

## Gotchas and judgment calls
- Curated for forecasting, not completeness: small/back-sided/non-geoeffective events are under-cataloged, especially before ~2010 (database starts ~2010) and during staffing gaps. Never use DONKI alone for occurrence statistics — use CDAW (CMEs) or GOES lists (flares).
- Multiple CMEAnalysis entries per CME (initial, refined); filter `mostAccurateOnly=true` or pick the latest.
- Predicted arrival times in linked ENLIL runs are forecasts with ±~10 h typical error; don't quote them as observed arrivals — the IPS entries are the observations.
- linkedEvents can be null; absence of a link is not absence of a relationship.
- api.nasa.gov DEMO_KEY rate limits are tight (roughly 30/hr class); batch queries or use a real key / direct CCMC route.

## Cross-checks
- CME speeds/times vs the CDAW LASCO catalog (expect plane-of-sky vs cone-model differences).
- Flares vs GOES XRS data and HEK/SWPC lists.
- Storm entries (GST Kp values) vs GFZ Kp and Kyoto Dst/SYM-H.
- Shock arrivals (IPS) vs your own L1 shock identification (see solar_wind_analysis).
