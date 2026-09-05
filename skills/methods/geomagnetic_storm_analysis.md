# Geomagnetic Storm Analysis
> Characterize storms with Dst/SYM-H and Kp, classify intensity, and attribute the interplanetary driver.

## What it is / When to use it
Geomagnetic storms are global magnetospheric disturbances driven by sustained southward IMF Bz and enhanced solar wind coupling. Use this skill for storm identification, phase timing, intensity classification, and CME-vs-CIR driver attribution.

## How to use it
1. Indices:
   - Dst (hourly, Kyoto WDC) and SYM-H (1-min, essentially high-cadence Dst): ring-current strength; storm minima are negative.
   - Kp (3-hourly, GFZ Potsdam, 0-9): global mid-latitude range index; drives NOAA G-scale.
   - Get them from OMNI (SYM-H, Kp included), Kyoto WDC, or SWPC JSON for real-time Kp.
2. Storm phases in Dst/SYM-H:
   - Sudden commencement / initial phase: positive jump (dynamic pressure increase at shock arrival), not always present.
   - Main phase: rapid decrease to minimum over hours (ring current injection while Bz south).
   - Recovery: exponential-ish return over ~1-several days.
3. Classification (common Dst-based convention, Gonzalez et al. style): moderate -50 to -100 nT; intense -100 to -250 nT; extreme < -250 nT. NOAA G-scale maps Kp: G1=Kp5, G2=Kp6, G3=Kp7, G4=Kp8-9-, G5=Kp9.
4. Driver attribution:
   - CME-driven: sheath and/or magnetic cloud at L1 (smooth strong B, low beta), often shock + SSC, can reach intense/extreme, Bz south sustained and smooth. Check DONKI GST entries and linked CMEs.
   - CIR/HSS-driven: recurrent (~27 d), moderate at most (rarely < -100 nT), fluctuating Bz (Alfvenic), long-duration recovery with continued high-latitude activity (HILDCAA). No shock usually.
   - Examine L1 data (see solar_wind_analysis) for the interval spanning storm onset minus ~12 h.
5. Propagation delay: L1 to magnetopause is ~30-60 min at typical speeds (~1.5 million km / Vsw; 45 min at 550 km/s). OMNI data are already time-shifted to the bow-shock nose — do NOT add the delay again when using OMNI. Magnetospheric response (Dst main phase) then develops over additional hours.

## Gotchas and judgment calls
- Real-time Kp (SWPC estimated) and definitive Kp (GFZ) differ; say which you used. Quicklook Dst gets revised.
- Dst responds to dynamic pressure (positive) and tail currents, not only ring current — a compressed quiet magnetosphere can push Dst positive without a storm.
- Multi-step main phases usually mean multiple Bz-south intervals (sheath then cloud, or CME-CME interaction) — attribute each dip.
- Kp saturates (9 is a ceiling) and is 3-h coarse; don't use it for timing.
- Storm onset time != shock arrival time; SSC is the shock, main-phase onset is when Bz turns south.

## Cross-checks
- Cross-check DONKI GST (lists Kp maxima and linked CME/HSS causes) against your own L1-based attribution.
- SYM-H minimum vs Dst minimum should roughly agree (SYM-H typically slightly deeper); large disagreement means a data problem.
- The empirical coupling check: integrate the solar wind electric field VBz-south over the main phase — a deep storm without sustained VBs in OMNI means you have the wrong interval or bad data.


## Sheath vs ejecta attribution: what it can and cannot support (2026-09-05)

`detect_icme` reports a `driver` — "sheath", "ejecta" or "ambiguous". Three things to know before quoting it.

**1. It compares totals, and totals reward duration.** The verdict uses total southward field-time (nT·h), because ring-current injection integrates VBs. But a long weak sheath outscores a short intense ejecta. `south_nT_per_hour` and `driver_by_rate` are reported beside it: across 19 attributable storms below Dst −200 nT, **the two measures disagree on 9**. Quote the label only when both agree, or quote both.

**2. The sheath is only as good as the shock pairing.** A sheath runs from the driving shock to the ejecta leading edge, and getting that shock right is harder than it looks — see the three failure modes recorded in `validation/run_validation.py::case_shock_pairing`, each of which produced a plausible answer and a different one. The check that catches all three is the shock *time* against a catalogue (DONKI IPS), not the label.

**3. Half the record has no attribution, and that is an ERA effect, not a selection on physics.** Of 40 declustered storms below −200 nT since 1981, 21 produce no attribution — but **19 of those 21 are pre-1995**. Before Wind (1994) and ACE (1997), OMNI 1-min plasma is sparse, and the ejecta test needs a proton temperature series. Restricted to 1995 onward the sample is **17 of 19 attributable (89%)**. Quote the modern sample; do not quote a 1981-start statistic as though it were uniformly sampled.

### The population result (1995–2024, 17 storms)
**8 sheath, 8 ejecta, 1 ambiguous** — exactly even. But it depends on depth: **6 of 8 storms below −250 nT are sheath-driven, against 2 of 9 between −250 and −200.**

Threshold-robust: re-running with `min_hours` 6→4, `shock_jump_kms` 60→40, or `temp_ratio_max` 0.5→0.6 moves the overall split by at most one storm and never makes the population sheath-dominated. The depth trend is steadier still — 6 sheath against 2–3 ejecta below −250 nT under every setting tested.

The trend is established in the literature (Gonzalez et al. 2011 treat superintense storms, Dst ≤ −250, as a separate category; Zhang et al. 2004 find only ~30% of storms driven by magnetic clouds), so reproducing it is a check on the pipeline rather than a new result.

The two modern failures are threshold artefacts worth knowing: **2003-11-20** (−422 nT, second-deepest in the record) has a 5.3 h ejecta against the 6 h minimum, and **2001-11-06** has a clear 50 h ejecta but no detected shock — the cost of a shock test strict enough to reject turbulence.

**Do not generalise a driver attribution from a handful of events.** Both 2024 superstorms are sheath-driven on both measures, and that is a statement about those two storms. The full study is `users/cayoung/analyses/sheath-vs-ejecta/`.
