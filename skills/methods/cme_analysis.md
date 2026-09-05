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

## Tool: `track_cme_front` (added 2026-09-05)
Measures the leading edge frame by frame so `cme_height_time` has something real to fit. Before this, a height-time fit needed heights typed in by hand — which is how the source notebook ended up fitting `np.random.uniform` output.

**Method.** Each frame is divided by its own exposure and differenced against the previous one, remapped to heliocentric radius through the WCS, and reduced to a radial profile inside a position-angle sector. Edge = outermost radius where the profile stays above `n_sigma` for three consecutive 0.1 R☉ bins.

**Three choices that are not obvious, each of which failed the other way first:**

1. **The noise reference is the same radius at other position angles**, not an outer annulus and not the whole frame. An outer-annulus σ is contaminated the moment the CME reaches it — on the 2024-05-08 halo that inflated the noise 4.6× and suppressed every detection. A whole-frame MAD is dominated by the bright inner corona, which left the front at 3–5σ against a 5σ threshold. The azimuthal reference cancels both the radial brightness gradient and the frame-wide floor.
2. **The sector statistic is the 90th percentile, not the median.** The front is a thin arc inside a 30° bin; a median averages it away. Measured: median profile peaked at 1.0 where the 90th percentile reached 4.9.
3. **Auto sector selection scores monotonicity first, detection count second, span last.** Scoring by span alone rewards a noisy sector whose "edge" jumps around — the opposite of a tracked front. On the 2024-05-14 limb CME the span-first rule picked PA 30° (non-monotonic, wrong side of the Sun); monotonicity-first picks PA 225°.

**Two artefacts the tracker refuses (added 2026-09-05, after October 2024).** Both reach the end of the routine with three or more *monotonic* detections, so neither is caught by the monotonicity test:

1. **Halo fraction ≥ 0.75.** A halo brightens every position angle at once, so the azimuthal reference annulus is itself full of CME and no sector stands out. What gets followed is the edge of the brightened region, not a front. `halo_fraction_peak` reports the fraction of position angles brightening.
2. **Heights pinned at the search bound.** A CME faster than the field can follow leaves the detector between frames; the outermost bin stays lit and every later detection reports the same radius. Repeated maxima at `r_max` are saturations. Refused when half or more of the heights sit within 0.15 R☉ of the outer bound.

The October 2024 events forced both. The 9 October Earth-directed CME returned `[5.05, 28.85, 28.85, 28.85, 28.85]` in C3 — four identical values at the field edge, reported as a monotonic track with `halo_fraction_peak` 1.0. The 3 October C2 track returned `[..., 5.55, 5.65, 5.65]` and fitted to 272 km s⁻¹, an implausible speed for an X9.0 CME and a pure artefact of the C2 outer edge.

**The refusal is the scientific answer for an Earth-directed CME.** The halo geometry that makes a CME geoeffective is the same geometry that makes plane-of-sky height-time meaningless. Use cone/GCS (`search_donki` CMEAnalysis) for those, and note that the plane-of-sky/cone comparison in the May 2024 case only exists because that event was a *partial* halo (fraction 0.38–0.46).

**Halo events.** A halo brightens every position angle at once, so no quiet reference annulus remains. `halo_fraction_peak` reports the fraction of position angles brightening; above ~0.75 the refusal message says so explicitly and points at cone/GCS instead. This is geometry, not a threshold that wants lowering. Even below that, a halo is only trackable in its **early** frames, before the disturbance fills the field: on 2024-05-08 the front is measurable from 06:12 to 06:36 UT and gone by 07:12.

**Validated result (2024-05-08 halo, `run_validation.py cmetrack`):** PA 225°, 3.75 → 4.75 R☉, plane-of-sky **483 ± 55 km s⁻¹**, r² 0.987. Two independent checks: it lands **below** DONKI's cone fit (729 km s⁻¹), as an edge-on halo must; and the linear fit extrapolates to 1 R☉ at 05:05 UT against an X1.0 peak at 05:09 — the tracker never sees the flare, so that agreement is not circular.

**Field-of-view limit.** C2 spans 2.4–5.8 R☉ at ~12-min cadence, so a CME faster than ~1500 km s⁻¹ crosses it in under two frames and cannot be tracked there. The 2024-05-14 X8.7 event is the example: heights sit at the outer edge from the first detection. Use C3 (3.9–29 R☉) for fast events, and expect the deceleration term to be real rather than a fit artefact.

**Always compare against a cone or GCS fit.** The bright edge in a running difference is where brightness *changed* most, which is the front only if the front is the fastest-moving feature; a streamer deflection can imitate one.
