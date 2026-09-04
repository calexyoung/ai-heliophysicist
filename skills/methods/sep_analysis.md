# Solar Energetic Particle (SEP) Event Analysis
> Detect and grade radiation storms (NOAA S scale) in >10 MeV proton flux, measure fluence and hardness, and test the onset against flare timing and Parker-spiral connection.

## What it is / When to use it
Radiation storms: protons (and heavier ions) accelerated at flares and CME-driven shocks, arriving at 1 AU minutes to hours after the eruption and lasting days. The operational quantity is the >10 MeV integral proton flux in pfu (protons cm⁻² s⁻¹ sr⁻¹); NOAA's S scale runs S1 (10 pfu) to S5 (10⁵ pfu) on the peak.

## Data
- **GOES integral channels** (>1, >5, >10, >30, >50, >60, >100 MeV; SEISS on GOES-16+, EPEAD before) are the NOAA reference. Science-quality: `fetch_goes_protons` (NCEI; see `datasources/goes_ncei.md`) — measured through 2020-03-04, **derived** after. Real-time: SWPC `/json/goes/primary/integral-protons-*.json` (`get_noaa_realtime`, 7 days, not science quality).
- **OMNI hourly** `OMNI2_H0_MRG1HR` carries merged 1 AU fluxes `PR-FLX_11800` (>1 MeV), `PR-FLX_21800`, `PR-FLX_41800`, `PR-FLX_101800` (>10), `PR-FLX_301800` (>30), `PR-FLX_601800` (>60), half-hour-midpoint stamps. **They end 2020-03-04** — `fetch_omni` returns all-fill for later windows and `characterize_sep` refuses with that reason. Pre-2006 values come from IMP-8 and are patchy (Halloween 2003: half the hours missing, peak 9650 vs GOES 29 500 pfu). `MFLX1800` flags magnetospheric contamination (6 = clean).
- Event lists for cross-checks: NOAA SWPC SEP list (>10 MeV, 10 pfu events, 1976-), DONKI `SEP` (`search_donki kind="SEP"`), GLE database (neutron monitors) for the hardest events.

## Tool: `fetch_goes_protons` (added 2026-09-03)
- Writes `p_gt1 … p_gt100` in pfu on a `time` index — exactly the columns `characterize_sep` wants (`flux_10mev_column="p_gt10"`, `flux_30mev_column="p_gt30"`). GOES-R files add `p_gt500`.
- **Check `derived` in the result before quoting a number.** Before 2020-03-05 it is `False`: real EPEAD integral channels, and the 2017-09-11 peak reproduces SWPC's published 1490 pfu to 1493 pfu at the same 11:45 UT stamp. After, it is `True`: a piecewise power law through the SGPS differential channels, because the GOES-R archive has no >10 MeV channel at all. Reconstructed values agree with SWPC's operational feed to ~10% at >10 MeV.
- Say "derived" in any report that rests on a post-2020 value, the same way beacon data is flagged.
- **Quiet-time `p_gt30`+ from the derived path are lower bounds** (2-3x low; GCR above the SGPS range). Inside an event they are fine. `p_gt500` is measured, never derived, and is deliberately not added into the lower thresholds.
- `sensor` defaults to `"max"` (larger of the two telescopes, SWPC alerting practice). During a prompt anisotropic onset the two spacecraft and the two telescopes genuinely differ — GOES-16 read 516 pfu and GOES-18 269 pfu for the 2024-05-10 spike while the rest of the event matched to a few percent. Quote the satellite.
- Refusals, all explicit: a window straddling 2020-03-04 (two instruments, two provenance classes), `resolution="1min"` in the legacy era (cpflux is 5-min only), and `sensor` names from the wrong era.
- Validation: `uv run python validation/run_validation.py protons` — three anchors (published 2017 peak, SWPC operational cross-check, GOES-16 vs GOES-18).

## Tool: `characterize_sep` (ported from helio-agent 2026-09-03)
- Input: a workspace CSV with a >10 MeV integral flux column (pfu), optionally a >30 MeV column. Defaults: threshold 10 pfu (S1), gaps ≤ 12 h merged (decay-phase dips do not split an event), events ≥ 2 h kept. The FIRST qualifying event is `sep` (the prompt injection); all are in `events`.
- Per event: onset/end/duration, peak + time per channel, fluence (cadence-weighted sum, cm⁻² sr⁻¹), hardness = peak(>30)/peak(>10). Hardness near 0.3 is a hard, shock-connected or flare-rich spectrum; below 0.1 is soft (gradual, poorly connected).
- With `flare_peak_time` (+ `flare_class`, `flare_lon_deg`): onset delay vs the free-streaming expectation along a Parker spiral of `vsw_km_s` (arc length ≈ 1.14 AU at 450 km/s; 10 MeV ≈ 0.145c → ~0.95 h after light arrival, 30 MeV ≈ 0.5 h), velocity dispersion (>30 MeV crossing `threshold_30mev_pfu` = 1 pfu should lead the >10 MeV onset), and the connection angle |flare lon − footpoint lon|, well connected ≤ 40°.
- **Hourly OMNI onsets are quantized to the half-hour midpoint** and lag the GOES 5-min onset by up to an hour (2017-09-10: 17:30 vs 16:45). Quote them as "within the hour"; use GOES 5-min data when the onset delay itself is the science.
- **The 40° connection gate is strict at measured wind speeds.** 2017-09-10 (S08W88, GLE 72, unambiguously well connected) sits 33° from the W55 footpoint at the default 450 km/s but 42° at the measured 530 km/s. Report the angle and the assumed speed; the nominal footpoint is set by wind released a few days earlier, so a nominal 400-450 km/s is defensible unless you have the upstream speed at the eruption time.
- Refusals: missing column, all-fill flux (wrong era), unparseable `flare_peak_time` — each names the argument.

## Gotchas
- Integral vs differential: GOES "integral" fluxes are derived from differential channels with a spectral assumption; different satellites/processings disagree at the 20-30% level (OMNI 1208 vs GOES 1490 pfu for 2017-09-11). The S class is robust; the pfu value is not a precision measurement.
- Energetic storm particle (ESP) peaks at shock arrival can exceed the prompt peak (2017-09-12/13, 2003-10-29): the >10 MeV peak time may be the shock, not the flare. Check `detect_icme`/shock time before attributing the peak.
- Magnetospheric contamination near the bow shock inflates >1 to >4 MeV channels; trust >10 MeV upward.
- Flare timestamps are Earth-observed (light-travel already elapsed); the tool subtracts 8.3 min from the transit time accordingly. Do not subtract again.

## Cross-checks
- S class and peak against the NOAA SWPC SEP event list; onset against GOES 5-min; source region against the flare (HEK/DONKI FLR) and CME (DONKI CME, CDAW) records.
- Very hard events (hardness > 0.3, onset delay < 1.5 h) should appear in the GLE database; if not, question the connection or the flare association.
- Literature for the event (`search_ads`) before quoting fluence or spectral conclusions — many well-known events have published spectra to compare against.
