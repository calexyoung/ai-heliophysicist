# Troubleshooting Data Retrieval and Processing
> Failure signatures in heliophysics data work, and whether to retry, fix, or re-plan.

## What it is / When to use it
Read when a query returns nothing, numbers look insane, timestamps don't line up, or a pipeline that worked yesterday fails today.

## How to use it
1. Empty query results — check in this order:
   - Dataset ID exactly right? IDs are case-sensitive in many services and conventions vary (`AC_H0_MFI` not `ac_h0_mfi`). Verify the ID exists by listing datasets (cdasws `get_datasets`, HAPI `/catalog`) rather than guessing.
   - Time range inside the dataset's coverage? Missions end; L2 production lags real time by days-months. Check the dataset's start/stop dates from the catalog metadata.
   - Time format the service expects? ISO 8601 with `Z`/UTC is safest; some services reject naive or fractional forms.
   - Variable name valid for that dataset? Request the variable list first.
   - Empty is a legitimate answer for event queries (HEK, DONKI): maybe nothing happened. Confirm against a known-active interval before blaming the query.
2. Fill values: CDF convention is -1.0e31 (FILLVAL attribute); OMNI ASCII uses 9999.9 / 999.9 / 9999999. style sentinels per column; some sources use -9999.9 or NaN. ALWAYS read FILLVAL from metadata and mask to NaN before any arithmetic. Signature of unmasked fills: absurd means (~ -1e29), plots autoscaled to a flat line.
3. Time confusion:
   - Everything in this field is UTC. A constant 4/5/7-hour offset between datasets means a local-timezone leak (pandas naive timestamps, matplotlib local formatting). Force tz-aware UTC end to end.
   - CDF epochs come in CDF_EPOCH (ms), CDF_EPOCH16, and CDF_TT2000 (ns, includes leap seconds). cdflib converts; hand-conversion off by 32-37 s is the leap-second signature.
   - One-day offsets: DOY vs date confusion, or inclusive/exclusive end-time conventions.
4. NaN propagation in resampling: pandas `resample().mean()` skips NaNs (fine) but `interpolate()` will happily bridge multi-day gaps (not fine — set a `limit`); rolling means with `min_periods` unset can hide gaps. Decide a max-gap-to-interpolate policy and state it. Never interpolate across data gaps then compute spectra (see timing_periodicity).
5. Server outages — retry vs re-plan:
   - Transient (timeouts, 5xx, connection reset): retry with exponential backoff, 2-3 attempts.
   - Sustained outage of one service: re-plan to an equivalent source — CDAWeb data via its HAPI server, OMNI via CDAWeb IDs, imagery via Helioviewer vs VSO, positions via SSCWeb vs spiceypy. Most heliophysics data has >= 2 access routes; keep a mapping.
   - 4xx errors: your request is wrong; retrying identical requests is futile — fix the ID/time/parameter.

## Gotchas and judgment calls
- Distinguish "no data returned" (gap, real) from "query failed" (error) from "no events" (valid empty) — they demand different responses; don't paper over any of them silently.
- Quicklook/near-real-time data get replaced by definitive versions; a result that changes on re-download may be reprocessing, not a bug.
- Caching (sunpy/cdasws local caches) can serve stale or truncated files after an interrupted download — clear the cache before deep-debugging.

## Cross-checks
- Reproduce one known event end-to-end (e.g., a famous storm) as a pipeline smoke test.
- Pull the same interval from a second route (HAPI vs REST vs pyspedas) and diff.
- Plot raw data with fills unmasked once — seeing where the sentinels sit teaches you the dataset's failure modes.
