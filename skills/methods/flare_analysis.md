# Solar Flare Analysis
> Classify and time solar flares from GOES XRS soft X-ray flux, then cross-check against catalogs and imagery.

## What it is / When to use it
Flares are classified by peak 1-8 Å soft X-ray flux from the GOES X-Ray Sensor (XRS):
- A: < 1e-7 W/m^2, B: 1e-7 to 1e-6, C: 1e-6 to 1e-5, M: 1e-5 to 1e-4, X: >= 1e-4.
- The number is the multiplier within the decade (M5.2 = 5.2e-5 W/m^2). X-class continues past X10.
Use this skill any time the task involves identifying, timing, ranking, or classifying flares.

## How to use it
1. Get XRS data: NOAA SWPC JSON for recent data (`https://services.swpc.noaa.gov/json/goes/primary/xrays-7-day.json`), or GOES XRS science data via CDAWeb / NOAA NCEI for historical events. sunpy `TimeSeries` reads GOES XRS files natively.
2. Use the long channel (1-8 Å, "xrsb") for classification; the short channel (0.5-4 Å, "xrsa") hardens during flares and is useful for temperature/impulsiveness.
3. Timing (NOAA operational definitions, use unless told otherwise):
   - Start: first minute of a steep monotonic rise (operationally, 4 consecutive minutes of rise with the last flux >= 1.4x the first).
   - Peak: maximum of the 1-8 Å flux.
   - End: flux decays to halfway between peak and pre-flare background (half-power point), NOT return to background.
4. Background subtraction: for weak flares riding on elevated background (active-Sun periods), estimate background from a quiet interval hours before and consider reporting both raw and background-subtracted class. NOAA classes are NOT background-subtracted; many science papers do subtract. State which you used.
5. Location/source region: GOES gives no location. Use SDO/AIA imagery (131 Å and 94 Å for hot flare plasma, 1600 Å for ribbons) at the peak time, or the flare's NOAA active region number from event lists.
6. Cross-check: query HEK (event type FL, frm SWPC or SSW Latest Events) and DONKI FLR endpoint for the same window.

## Gotchas and judgment calls
- GOES satellite changes matter: pre-GOES-16 fluxes used SWPC scaling factors; GOES-R (16/17/18) science fluxes are unscaled and differ by roughly a factor ~1.4 for the long channel. Comparing classes across eras needs care — verify via NOAA NCEI GOES-R documentation before quantitative cross-era claims.
- Eclipse seasons and calibration gaps produce dips/dropouts in XRS — don't call them flare ends.
- Overlapping flares: a second flare on the decay of a big one can be missed by threshold logic; inspect the time series by eye (or derivative).
- Occulted flares (behind the limb) show reduced X-ray flux; class underestimates true size.
- 1-minute vs 1-second cadence: operational lists use 1-min averages; peak class from high-cadence data can be slightly higher.

## Cross-checks
- Compare your class/times against the SWPC event list, HEK FL entries, and DONKI FLR — they should agree within a class subdivision and a few minutes.
- Confirm the source region with AIA 131/1600 Å imagery (Helioviewer is fine for this) — a flare with no visible AIA brightening at the reported time is a red flag.
- For large flares, an associated CME in LASCO within ~1 hour and an SEP event (for well-connected west-limb flares) are corroborating context.
