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
