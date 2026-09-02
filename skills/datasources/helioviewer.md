# Helioviewer
> Fast browse imagery of the Sun (JPEG2000) via a simple API — for context and visualization, never photometry.

## What it is / When to use it
Helioviewer (https://helioviewer.org; API at https://api.helioviewer.org) serves lossy-compressed JPEG2000 browse images from AIA, LASCO, EIT, STEREO SECCHI, SWAP, GONG, and more. Use it to answer "what did the Sun look like at time T", to grab context images for reports, to eyeball CMEs in LASCO, or to confirm a flare's location — with seconds of latency instead of a FITS download pipeline.

## How to use it
- Key endpoints (GET, JSON or image responses):
  - `https://api.helioviewer.org/v2/getClosestImage/?date=2024-05-10T06:00:00Z&sourceId=10` — metadata for the nearest image.
  - `.../v2/getJP2Image/?date=...&sourceId=10` — the JP2 file itself.
  - `.../v2/takeScreenshot/?date=...&layers=[10,1,100]&imageScale=2.4&x0=0&y0=0&width=1920&height=1200&display=true` — rendered PNG, compositable layers.
  - `.../v2/getDataSources/` — THE way to find sourceId values; don't hardcode from memory beyond well-known ones.
- Well-known source IDs (verify with getDataSources if anything looks off): AIA 171 = 10, AIA 193 = 11, AIA 304 = 13, AIA 131 = 9, LASCO C2 = 4, LASCO C3 = 5.
- Python: plain `requests` is fine; `hvpy` is the maintained official Python wrapper.
- Movies: `queueMovie`/`getMovieStatus`/`downloadMovie` endpoints exist for time-lapse generation.

## Gotchas and judgment calls
- NOT photometric: JP2s are lossy-compressed, byte-scaled, contrast-stretched browse products. Never measure fluxes, do difference-imaging science, or quantitative anything from them. For measurement, get level-1 FITS via VSO/JSOC.
- Image availability lags the instruments by minutes to hours (usually short for AIA); getClosestImage can silently return an image hours away from your requested time during gaps — check the returned date.
- Layer syntax in takeScreenshot is fiddly (`[sourceId,visible,opacity]`); a wrong sourceId gives a blank or wrong-instrument layer without an error.
- imageScale is arcsec/pixel; AIA native is ~0.6, LASCO C3 useful views need ~30-60. Wrong scale = a tiny dot or an off-screen Sun.
- Timestamps are UTC; the observation time is in the JP2/FITS-derived metadata, not the request time.

## Cross-checks
- Confirm a feature against the underlying science data (VSO/JSOC FITS) before claiming anything quantitative.
- Cross-check event times against HEK/DONKI entries; use SDO's own browse site or SolarMonitor as a second pair of eyes.
- If an image looks wrong (missing, stale), hit getClosestImage and compare requested vs returned dates before concluding the Sun did something odd.
