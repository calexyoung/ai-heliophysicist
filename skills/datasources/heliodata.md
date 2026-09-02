# Helio Data Portal (helio.data.nasa.gov)
> NASA's new unified heliophysics data discovery portal — search >7800 datasets across the division from one place.

## What it is / When to use it
https://helio.data.nasa.gov is NASA's unified discovery layer over heliophysics data holdings (SPDF/CDAWeb, SDAC, and mission archives), with an API at https://api.heliophysics.net/api (v0.8, alpha as of 2025-2026). Use it for DISCOVERY: "what datasets exist for X?", browsing by heliophysics region (solar corona, inner heliosphere, magnetosphere, ionosphere...) or by mission/instrument, and free-text search. It points you to data; actual retrieval usually still goes through CDAWeb/HAPI/VSO.

The older Heliophysics Data Portal (https://heliophysicsdata.gsfc.nasa.gov, SPASE-based) covers similar ground with a clunkier interface; it remains a fallback and the home of SPASE resource descriptions.

## How to use it
- Web UI: free-text search box; facet by observatory, instrument type, measurement region, cadence. Result records link to the serving archive (often a CDAWeb dataset ID — carry that ID into cdasws/HAPI).
- API: base `https://api.heliophysics.net/api`. It is version 0.8 ALPHA — endpoint shapes may change; discover current routes from the site's API documentation rather than trusting cached knowledge. Expect JSON search endpoints taking free-text and facet parameters. Verify via a small test query before building on it.
- Typical agent workflow: free-text search here -> extract the archive + dataset ID from the record -> switch to the cdaweb/hapi/vso skill for retrieval.

## Gotchas and judgment calls
- Alpha status: outages, schema changes, and incomplete indexing are expected. If a search here returns nothing, that is NOT evidence the data doesn't exist — fall back to CDAWeb's own catalog, the HAPI `/catalog`, VSO, or the old Heliophysics Data Portal.
- >7800 datasets means many near-duplicates (cadence/level variants); prefer the highest science level for analysis (see cdaweb skill on H/K/L levels).
- Metadata quality is inherited from SPASE records, which vary in completeness; coverage dates and descriptions can be stale.
- The portal indexes datasets, not events — for events use HEK/DONKI.
- Don't confuse with heliophysics.net community sites or the PyHC portal; the API host `api.heliophysics.net` is the one paired with helio.data.nasa.gov.

## Cross-checks
- Confirm any dataset found here actually exists at the serving archive (query CDAWeb/HAPI for the ID) before promising it in an analysis plan.
- Compare result counts for a mission against the archive's own list (cdasws `get_datasets(observatoryGroup=...)`).
- If a needed dataset seems absent, check the mission's own archive pages and SPDF FTP-style listings before concluding it's unavailable.
