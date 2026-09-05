# CME Analysis
> Measure CME kinematics from coronagraph height-time data and estimate Earth arrival, with catalog cross-checks.

## What it is / When to use it
Coronal mass ejections are observed in white-light coronagraphs: SOHO/LASCO C2 (~1.5-6 Rs) and C3 (~3.7-30 Rs) from the Sun-Earth line, and STEREO-A COR1/COR2 from a different vantage. Use this skill for CME identification, speed/direction estimation, and arrival-time forecasting questions.

## How to use it
1. Height-time measurement: track the leading edge of the CME front (usually at a fixed position angle, typically the fastest point) across successive frames. Heights are plane-of-sky projected distances in solar radii.
2. Speed fits:
   - Linear fit height vs time -> average plane-of-sky speed. Robust, standard, what CDAW reports as "linear speed".
   - 2nd-order (quadratic) fit -> constant acceleration estimate; report speed at a reference height (e.g., 20 Rs). Sensitive to the first/last points; only meaningful with >= 5-6 well-spread points.
3. Projection: plane-of-sky speed underestimates radial speed for Earth-directed (halo) CMEs and roughly equals it for limb CMEs. For halos, use cone-model or multi-viewpoint (STEREO + LASCO) reconstructions, or take catalog "space speed" values where provided.
4. Catalogs:
   - CDAW SOHO LASCO CME catalog (https://cdaw.gsfc.nasa.gov/CME_list/): manually measured, comprehensive since 1996, plane-of-sky quantities, no Earth-impact judgment.
   - DONKI CME + CMEAnalysis: human-curated by CCMC/SWPC-adjacent forecasters, includes 3D (cone) parameters — latitude, longitude, half-angle, radial speed — and linked WSA-ENLIL model runs with predicted arrival times. Forecast-oriented, less complete for small CMEs.
   - Also exist: CACTus and SEEDS (automated; noisier, different completeness).
5. Rough arrival-time estimate: transit time t ≈ 1 AU / V with drag correction. Fast CMEs (>1000 km/s) decelerate toward the ambient wind speed; slow ones accelerate. Zeroth order: t[hours] ≈ 1.496e8 km / V[km/s] / 3600. For a 700 km/s CME that's ~59 h; real transit is typically 1-4 days. For anything quantitative, prefer an empirical drag-based model (DBM) or cite the DONKI/ENLIL prediction. Typical arrival-time errors are ±10 hours even for good models — say so.

## Gotchas and judgment calls
- Halo CMEs may be front-side OR back-side: check EUV low-coronal signatures (dimmings, EIT/AIA waves, post-eruption arcades) on the disk to decide. A halo with no disk signature is likely far-side.
- Catalog speeds for the same event can differ by hundreds of km/s (CDAW vs CACTus vs DONKI) — measurement choices, not errors. Quote the source.
- LASCO data gaps (notably mid-1998 to early 1999 SOHO loss) and cadence changes affect completeness.
- Don't fit a quadratic to 3 points. Don't extrapolate coronagraph acceleration to 1 AU.
- CME-flare association is by time+position coincidence, not causation bookkeeping; be careful assigning a flare to a CME when multiple ARs are active.

## Tool: `hindcast_forecasts` (ported from helio-agent 2026-09-03)
- Replays the live `helio-agent monitor` arrival rule over a past window: DONKI CMEAnalysis per CME, longitude known and |lon| <= `earth_cone_deg` (60), highest-speed fit, `cme_arrival` drag ensemble window, verified against DONKI Earth IPS shocks +/- `grace_hours` (12). Storm recall against DONKI GST (class from max Kp). Diagnostic only; `monitor_state.json` is untouched.
- Read hit rate and recall together. May 2024: 56 windows, 52% hit rate, storm recall 4/5, hit MAE 12.5 h; the "high" tier (>= 1000 km/s and |lon| <= 30 deg) was 7/7, "low" 42%. The rule has no speed floor, so slow CMEs around an active period all "hit" the same shock; that inflates hits and is why `min_speed_kms` exists as an experiment knob.
- DONKI is a living record: analysts add and revise fits and IPS entries for months, so counts drift between runs. Quote the run date and the audit id, and keep assertions to invariants (a named storm covered, a named CME hit).
- The confidence tiers are helio-agent's 2024 fit; re-verify them here before citing the numbers. The severity prior (min SYM-H from launch speed) was NOT ported: it needs a SYM-H backtest this repo has not run.
- Typical DBM accuracy is +/- 10 h; a hindcast MAE near that is the model working, not a bug. A MAE far below it usually means the grace window is doing the work.

## Cross-checks
- Compare CDAW and DONKI entries for the same event; reconcile plane-of-sky vs radial speed before calling a discrepancy.
- Predicted arrival vs observed: look for the interplanetary shock / ICME at L1 (see solar_wind_analysis skill) and the sudden commencement in SYM-H.
- STEREO-A imagery (when at a useful separation) breaks the projection degeneracy — check it for Earth-directed events.

## The Earth-directed cone is 45 degrees, and why not tighter (2026-09-04)
`helio-agent monitor` forecasts every DONKI cone-model CME whose longitude falls within `EARTH_DIRECTED_MAX_LON`. That was 60 deg; it is now **45**.

**What prompted it.** The live ledger reached 0 hits in 3 scored, every miss carrying `observed_arrival: null` — nothing arrived at all. Two of the three were 48-59 deg east: inside the 60 deg cone, but flank passages at best.

**What the hindcast says**, replaying the rule over four months (163 windows, 12 storms) spanning active, quiet and declining conditions:

| Rule | Windows | Hits | False alarms | Storms covered |
|---|---|---|---|---|
| 60 deg (old) | 163 | 89 | 74 | 9/12 |
| **45 deg (now)** | 131 | 76 | **55** | **9/12** |

26% fewer false alarms, identical storm coverage. Both of the live 48-59 deg misses fall outside 45 deg.

**Why not 30 deg, and why no speed floor.** On May 2024 alone, 30 deg + a 500 km/s floor looks excellent — false alarms 27 to 7, hit rate 0.518 to 0.696, recall unchanged. It is a trap. In June 2025 the only covered storm (2025-06-13, Kp 6.33) was caught by a **249 km/s CME at 41 deg longitude**; the speed floor kills it, and the 30 deg cone kills it independently. That month goes to **zero recall**. Tuning on one month would have shipped it.

**The asymmetry that decides it.** A false alarm costs attention; a missed storm costs the mission. So recall neutrality is the constraint on this threshold, not precision — pinned by `hindcast.recall_neutral`, which fails if the cone moves off 45 or if the narrower rule stops being recall-neutral.

**A ceiling neither threshold touches.** May 2024's 05-02 storm (Kp 6.67) and June 2025's 06-01 storm (Kp 8.0, severe) are missed by *every* setting including the loosest. No catalogued Earth-directed CME covers them, so they are most likely CIR / high-speed-stream driven — structurally outside what a CME-arrival rule can catch. Overall recall is capped near 0.75 by that, not by the cone. Quote hit rate and recall together, never one alone.
