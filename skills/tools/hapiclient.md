# hapiclient
> The reference Python client for HAPI time-series servers.

## What it is / When to use it
`hapiclient` (pip package `hapiclient`) fetches time series from any HAPI-compliant server with one function. Use it when the hapi datasource skill points you at a HAPI endpoint — it handles chunking, caching, and parsing so you don't hand-roll REST calls.

## How to use it
```python
from hapiclient import hapi

server  = 'https://cdaweb.gsfc.nasa.gov/hapi'
dataset = 'OMNI_HRO_1MIN'
params  = 'flow_speed,BZ_GSM'          # from the /info response; '' = all params
start   = '2024-05-10T00:00:00Z'
stop    = '2024-05-12T00:00:00Z'

data, meta = hapi(server, dataset, params, start, stop)
```
- `data` is a numpy structured array: `data['Time']` (ISO-8601 byte strings), plus one field per parameter (arrays for multi-component params).
- `meta` mirrors the server's `/info`: units, fill, size, description per parameter — read `meta['parameters'][i]['fill']` and mask.
- Convert times: `hapiclient.hapitime2datetime(data['Time'])`, or `pd.to_datetime(data['Time'].astype(str))`.
- Discovery without data: `from hapiclient import hapi; cat, _ = ...` — catalog/info calls are made by passing fewer arguments (`hapi(server)` -> catalog, `hapi(server, dataset)` -> info).
- Options dict as the last argument: `{'logging': True, 'usecache': True, 'format': 'binary'}`. Binary is the default where supported and much faster than CSV for high-cadence data; set `'format': 'csv'` only for debugging.
- Time format requirements: HAPI wants restricted ISO 8601 — `YYYY-MM-DDTHH:MM:SSZ` or `YYYY-DOYTHH:MM:SSZ`; time.min inclusive, time.max exclusive. Pass strings exactly in this shape; datetime objects must be formatted first. Requesting `stop` beyond the dataset's coverage returns only what exists — check, don't assume.

## Gotchas and judgment calls
- Fill values arrive literally (e.g., -1e31) — hapiclient does NOT mask them; convert to NaN using `meta` fills before math.
- `data['Time']` are bytes, not str — `.astype(str)` before pandas parsing.
- The local cache (default `./hapi-data/`) persists between runs; a truncated earlier download can serve stale data — delete the cache dir or `'usecache': False` when debugging.
- Multi-dimensional parameters (vectors, spectrograms) come as fields with shape (N, size); bin values live in `meta['parameters'][i]['bins']`.
- Some servers cap request duration; hapiclient splits long requests, but very long high-cadence pulls are still slow — chunk at the application level for progress visibility.
- Server subtleties differ (CDAWeb HAPI `@N` dataset suffixes for cadence variants) — take ids from the server's own catalog.

## Cross-checks
- Compare a sample against the native archive client (cdasws for CDAWeb-backed data).
- Verify record count ≈ interval / cadence from `/info`; large shortfalls are gaps or truncation.
- Plot immediately after load with fills masked — sentinel spikes are unmistakable.
