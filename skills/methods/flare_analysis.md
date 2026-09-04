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

## Tool: `flare_probability` (added 2026-09-04)
- Per-region C/M/X probabilities from the McIntosh class. **SWPC publishes whole-disk probabilities only** (`/json/solar_probabilities.json`); there is no per-region feed, so this has to be computed.
- Method: Poisson complement `P = 1 - exp(-rate * hours/24)` on the historical 24-hour flaring rates of **McCloskey, Gallagher & Bloomfield 2016, Sol. Phys. 291, 1711, Table 5** (arXiv:1607.00903, PDF in the workspace).
- The table is indexed by **evolution**, a (yesterday's class -> today's class) pair, which is the paper's actual result: a group that grew H -> D flares at 0.89 per 24 h against 0.68 for one already at D. Pass `previous_class` to use it; omit it and the tool takes the diagonal and sets `assumed_no_evolution`. Yesterday's classes are available from SWPC `/json/sunspot_report.json`, which carries ~1 month of per-region `Spotclass` — no tool wraps it yet.
- **Only the first (modified Zurich) letter is resolved.** Hsx and Hax return identical numbers; the penumbral and compactness components have their own tables in the paper (7 and 9) and combining all three is not something Table 5 supports.
- **Hale class is ignored entirely**, so a δ region scores the same as a simple one of the same Zurich class — and δ is the single strongest predictor of a big flare. Never present these as a forecast.
- Where a rate is not separated from zero at 1σ the tool sets `rate_resolved: false`; quote `probability_range` upper bound, not the central value. Several source cells are `0.00 ± 1.00` (one group), caught by `well_sampled`.
- `lon_deg` flags regions outside the ±75° band the rates were calibrated over.
- **Expect it to undershoot SWPC.** On 2026-09-04 the three classifiable regions combined to C 26% / M 4% against SWPC's C 60% / M 20%. Two reasons, both real: four west-limb regions had no class and scored nothing, and AR4524 had just produced an M flare while its class-based M probability was 1%. Class climatology cannot see recent activity; forecasters weight it heavily.
- Validation: `uv run python validation/run_validation.py flareprob` — four published cells reproduced exactly, monotonicity, and the refusal paths.
