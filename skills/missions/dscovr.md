# DSCOVR (Deep Space Climate Observatory)
> One-line: NOAA's operational real-time solar wind monitor at L1 (launched 2015), the source of the live upstream data behind SWPC forecasts.

## Overview
- Launched 2015-02-11 (NOAA/NASA/USAF); L1 orbit; operational solar wind data since ~2016-07 (took over the real-time role from ACE).
- Primary purpose is operational space weather — real-time telemetry with minutes latency. Science-grade archives exist but ACE/Wind remain preferred for retrospective research; DSCOVR is essential for "what did forecasters see" and for filling ACE/Wind gaps.
- Has had safe-hold outages (notably much of 2019-06 to 2020-02); check coverage.

## Instruments that matter
- **PlasMag Faraday cup (FC)**: solar wind proton density, speed, temperature.
- **MAG**: fluxgate magnetometer, vector B.
- (EPIC and NISTAR are the Earth-facing instruments — irrelevant to solar wind work.)

## Key datasets and where to get them
- **NOAA NCEI archive** (ncei.noaa.gov, "DSCOVR space weather"): level-2 files — `f1m` (Faraday cup 1-min moments), `m1m` (magnetometer 1-min), plus 1-sec mag (`m1s`) and 3-sec fc products; NetCDF format, daily files, mid-2016 to present.
- **SWPC real-time**: services.swpc.noaa.gov JSON endpoints (`products/solar-wind/mag-*.json`, `plasma-*.json`) — rolling real-time feed used by dashboards; keep for nowcasting only, values may be revised in the archive.
- CDAWeb also carries DSCOVR: `DSCOVR_H0_MAG` (1-sec mag) and `DSCOVR_H1_FC` (1-min Faraday cup moments) — convenient for cdflib/pyspedas workflows; verify IDs with a cdaweb dataset search if a load fails.

## Analysis recipes
- **Storm-arrival nowcast reconstruction**: pull SWPC real-time JSON (or the NCEI archive for the interval) for B, Bz(GSM), n, V; compute the L1-to-bow-shock advection delay dt = x_L1 / Vsw (~30-60 min) and overlay on ground magnetometer/Dst response.
- **Cross-validation triangle**: for any important event, plot DSCOVR vs ACE vs Wind at 1-min cadence; the three spacecraft are at slightly different positions, so small timing offsets are physical, but amplitude disagreements flag calibration or contamination problems.
- **Filling ACE SWEPAM dropouts**: post-2016 extreme events — substitute DSCOVR FC moments where SWEPAM is blank.

## Gotchas and judgment calls
- **Real-time vs archive**: the SWPC JSON feed is unvalidated telemetry; spikes, dropouts, and later-corrected calibration are common. Never publish analysis from the real-time feed when the NCEI/CDAWeb archive covers the interval.
- **Outages**: DSCOVR went into extended safe hold roughly 2019-06-27 to 2020-02 (ACE covered operationally); shorter outages happen. Absence of data is mission state, not your bug.
- Faraday cup temperature and density during high-speed or very cold streams have known biases vs Wind SWE; treat Tp comparisons cautiously.
- 1-min moments are averages that can smear shock ramps; use the higher-cadence mag (m1s / DSCOVR_H0_MAG) for shock timing.
- GSM vs GSE: SWPC real-time products give Bz in GSM; some archive variables are GSE — check attributes before feeding a Bz-driven coupling function.
- Fill values in NetCDF are typically -99999-style; mask on the declared _FillValue.

## Validation anchors
- **2018-08-25/26 storm**: DSCOVR shows the slow but strongly southward ICME (Bz ~ -17 nT for hours) that drove a Dst ~ -175 nT storm — reproduce the L1-to-Dst delay chain.
- **2024-05-10 Gannon storm**: successive shocks and Bz < -40 nT at DSCOVR preceding the G5 storm; compare against OMNI and SWPC's issued alerts for an operational-chain validation.

## Tool: `fetch_dscovr_l2` (added 2026-09-05)

**CDAWeb cannot serve modern DSCOVR science data. NOAA's own archive can.**
- `DSCOVR_H1_FC` (plasma) stops 2019-06-27. `DSCOVR_H0_MAG` runs to the present but carries **GSE and RTN only, no GSM** — so Bz, the quantity that drives a storm, was not obtainable from DSCOVR through CDAWeb at all.
- The Level-2 archive lives at `archive.data.noaa.gov/satellite-spaceweather`, an S3 bucket behind a JS explorer. The old `ngdc.noaa.gov/dscovr/data/YYYY/MM/` path is dead and `ncei.noaa.gov/data/dscovr-space-weather/` 404s. List it path-style: `GET /satellite-spaceweather/?list-type=2&prefix=DSCOVR/DSCOVR/FC/f1m/2024/05/&delimiter=/`. Note the doubled `DSCOVR/DSCOVR/` — that is real, not a typo.
- Products: `FC/f1m` (Faraday cup 1-min, `oe_f1m_dscovr_*`) and `MAG/m1m` (magnetometer 1-min, `oe_m1m_dscovr_*`), plus `FC/f3s`, `FC/fc0`, `FC/fc1` and an `auxiliary/` tree. Daily gzipped netCDF, ~50 kB each, from 2016-07 to present. The magnetometer product **does** carry `bx/by/bz_gsm`.
- A reprocessed day leaves several files distinguished by their `p` timestamp; the tool takes the newest and reports how many it skipped.

### The quality flag that matters is not `overall_quality`
`overall_quality` (0 normal, 1 suspect, 2 error) is necessary and **not sufficient**. During the May 2024 storm:

- The cup reported **~470 km/s at 2024-05-12 01:00** while OMNI 1-min, ACE and Wind all put the solar wind near **1000 km/s** — and stamped `overall_quality = 0` on every one of those minutes.
- Its maximum over 05-10 → 05-13 is **826 km/s** against OMNI's 1026 and ACE's 1004. Restricting to `overall_quality == 0` changes nothing; the maximum is 826 either way.
- The only header signal is **`reduced_proton_quality_flag`**, set on **58%** of the storm window. `fetch_dscovr_l2` reports it as `reduced_proton_quality_fraction` and puts a warning in `note` above 10%.

**So: DSCOVR plasma is usable for context and for density/temperature structure, and is the wrong source for a storm speed peak.** Use OMNI 1-min or ACE/Wind for that, and cross-check any DSCOVR speed against one of them before quoting it. The magnetometer has no such problem — its |B| (74.5 nT) and Bz (−50.9 nT) sit squarely inside the ACE/Wind/OMNI bracket.

`valid_ranges` in the result carries the instrument's own declared bounds from the file header (proton speed 189–1111 km/s, density 1–100 cm⁻³). A value pinned at a bound is a saturation, not a measurement.

Validation: `uv run python validation/run_validation.py dscovrl2` — which pins the under-read as well as the capability, so a future reprocessing that fixes the speeds will fail the check and flag this note for rewriting.
