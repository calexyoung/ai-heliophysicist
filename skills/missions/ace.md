# ACE (Advanced Composition Explorer)
> One-line: NASA solar wind and energetic-particle monitor at L1 since 1997 — the long-baseline workhorse for upstream field, plasma, and composition.

## Overview
- Launched 1997-08-25; L1 halo orbit; science data from ~1997-09/1998-01 (instrument-dependent) to present. NASA; ACE Science Center at Caltech.
- Nearly three decades of continuous upstream solar wind — the backbone (with Wind) of OMNI.

## Instruments that matter
- **MAG**: magnetic field vectors (twin fluxgates), 16 s and higher cadence.
- **SWEPAM**: solar wind proton density, speed, temperature; electron data too.
- **EPAM**: low-energy energetic ions/electrons (~50 keV to ~5 MeV) — first sign of shock arrival, upstream events.
- **SIS**: solar energetic particle heavy-ion composition, ~10-100 MeV/nuc.
- **SWICS**: solar wind heavy-ion composition and charge states (O7+/O6+, C6+/C5+ — CME/ICME fingerprints). Note SWICS suffered a hardware anomaly 2011-08; post-2011 data are a different, reduced product.
- **CRIS**: galactic cosmic ray composition.

## Key datasets and where to get them
- CDAWeb level-2:
  - `AC_H2_MFI` — MAG 1-hr; `AC_H1_MFI` — 4-min; `AC_H0_MFI` — 16-sec. GSE/GSM components + magnitude.
  - `AC_H0_SWE` — SWEPAM 64-sec proton moments; `AC_H2_SWE` — 1-hr.
  - `AC_H1_EPM` / `AC_H2_EPM` — EPAM fluxes (verify exact ID with a cdaweb dataset search).
  - `AC_H2_SIS` — SIS 1-hr heavy-ion fluxes.
  - SWICS: `AC_H2_SW2` era-dependent (post-2011 product differs) — verify before use.
- ACE Science Center (izw1.caltech.edu/ACE) provides the same level-2 plus browse plots.
- Real-time ACE (RTSW) via NOAA SWPC exists but DSCOVR is now the operational real-time source; use science-quality level 2 for analysis.

## Analysis recipes
- **Solar wind conditions around an event**: load `AC_H0_SWE` + `AC_H2_MFI` (or AC_H1_MFI for finer field), resample to a common cadence (e.g. 5 min medians), and watch for fill values (-9999.9 or similar per-variable FILLVAL — always mask on the CDF FILLVAL attribute, not a hardcoded number).
- **ICME identification**: look for the classic triad — enhanced |B| with smooth rotation (magnetic cloud), depressed proton temperature versus the expected Tp(Vsw) relation, low plasma beta; corroborate with SWICS O7+/O6+ enhancement (pre-2011) and bidirectional suprathermal electrons.
- **Shock arrival timing**: EPAM low-energy ion enhancement + simultaneous jumps in B, n, V, T. Cross-check the timing against the Wind and DSCOVR to catch spacecraft-specific glitches; remember L1-to-Earth convection delay ~30-60 min.

## Gotchas and judgment calls
- **SWEPAM degrades in exactly the events you care about**: during strong SEP events the CCD background contaminates moments — density/temperature become unreliable or missing right at big storm arrivals (e.g., Halloween 2003 has large SWEPAM gaps). Fall back to Wind SWE or (post-2016) DSCOVR for those intervals; OMNI already does this stitching for you.
- Fill values differ per variable; some are -9999.9, some -1e31. Mask via FILLVAL metadata.
- SWICS post-2011-08 is a different data product with fewer species; don't extend a charge-state time series across that boundary naively.
- ACE has no continuous electron density from a plasma wave instrument; SWEPAM moments are the only game.
- L1 is ~235 Re upstream and off-axis; solar wind features can miss Earth or arrive tilted — propagation to the bow shock (as OMNI does) is nontrivial for tilted phase fronts.

## Validation anchors
- **2003-10-29/30 Halloween storms**: |B| exceeding 50 nT and speed ~1800-2000 km/s (SWEPAM partly unreliable — a deliberate test that your gap/fallback logic works).
- **2006-12-13 shock + ICME**: clean shock jump in AC_H0_SWE/MFI near 14:14 UT at ACE, with a textbook magnetic cloud following — good pipeline sanity event.

## Coverage limit: ACE plasma Level 2 stops mid-2024 (found 2026-09-05)
`AC_H2_SWE` (hourly) and `AC_H0_SWE` (64-second) SWEPAM Level 2 both end at **2024-07-09** on CDAWeb. An October 2024 request is refused by the coverage check, correctly:

> `refusing: requested window 2024-10-08..2024-10-14 is outside AC_H2_SWE coverage 1998-02-04..2024-07-09`

This bites any analysis of a late-2024 event that reuses a recipe written against an earlier one. For events after mid-2024 the L1 plasma routes are:
- **OMNI 1-min** (`OMNI_HRO_1MIN`) — merged and time-shifted to the bow-shock nose; the right default for storm metrics.
- **Wind SWE** — `WI_H1_SWE` (non-linear proton fits: `Proton_V_nonlin`, `Proton_Np_nonlin`, `Proton_W_nonlin`) or `WI_K0_SWE` (key parameter, `V_GSM`/`Np`/`THERMAL_SPD`). Both cover October 2024.
- **DSCOVR Level 2** via `fetch_dscovr_l2` — NOAA NCEI, not CDAWeb. Check `reduced_proton_quality_fraction` per event: 58% in May 2024 (cup under-read the speed by ~200 km s⁻¹) against 39% in October 2024 (agreed with OMNI to 33 km s⁻¹). The caveat is event-dependent, not a blanket property.

ACE **MAG** (`AC_H1_MFI`) is unaffected and still covers the present.
