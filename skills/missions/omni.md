# OMNI
> One-line: not a spacecraft — NASA/SPDF's multi-source compilation of near-Earth solar wind field/plasma data, time-shifted to the bow shock nose, plus geomagnetic and solar indices.

## Overview
- Maintained by NASA GSFC/SPDF; hourly OMNI2 spans 1963-present; high-resolution OMNI (1-min, 5-min) spans 1981-present.
- Built by cross-normalizing and time-shifting ACE, Wind, DSCOVR (and historically IMP-8, GOES-era sources) to the bow shock nose. The default dataset for "what hit Earth" — use it unless you specifically need single-spacecraft measurements at L1.
- Includes Dst/SYM-H, Kp, AE, F10.7, sunspot number alongside the plasma/field data — one-stop shop for storm studies.

## Instruments that matter
- None of its own. Per-record source spacecraft ID variables tell you whether each interval came from Wind, ACE, DSCOVR, etc. — inspect them when data quality questions arise.

## Key datasets and where to get them
- CDAWeb:
  - `OMNI2_H0_MRG1HR` — hourly merged data, 1963-present (B, V, n, T, Dst, Kp, AE, F10.7, proton fluxes...).
  - `OMNI_HRO_1MIN` and `OMNI_HRO_5MIN` — high-res 1-min/5-min, 1981-present (B GSE/GSM, flow, SYM-H, AE, timeshift variables).
  - `OMNI_HRO2_1MIN` — the "/2" variant using a refined bow-shock-nose shift; prefer HRO2 for modern intervals.
- Also via `pyspedas.omni.data()`, `omniweb.gsfc.nasa.gov` (ftp/https text files), and HAPI servers.
- Kp/Dst definitive values ultimately come from GFZ Potsdam and WDC Kyoto; OMNI's copies can lag or carry provisional values for recent months.

## Analysis recipes
- **Storm overview plot**: load `OMNI_HRO_1MIN` for the event +-3 days; panel stack of B, Bz(GSM), V, n, dynamic pressure, SYM-H, AE. Mask fill values FIRST (9999.99, 99999.9, 9999999. — per-variable sentinel values, not NaN).
- **Coupling-function studies**: compute e.g. Newell dPhi/dt or epsilon from OMNI B, V; OMNI's bow-shock-nose timing means no additional propagation delay is needed against magnetospheric indices.
- **Long-baseline statistics**: `OMNI2_H0_MRG1HR` for solar-cycle trends; note pre-1971-ish coverage is sparse (large gaps when no upstream spacecraft existed) — compute coverage fraction before averaging.
- **ICME cataloging cross-check**: use the Richardson-Cane near-Earth ICME list (hourly, keyed to OMNI) as ground truth for ICME interval identification.

## Gotchas and judgment calls
- **Fill values are large positive numbers, not NaN** — the classic silent killer: 999.9, 9999.99, 99999.9, 9999999. depending on the variable. A "solar wind speed of 99999.9" averaged into your series ruins everything. Always mask on each variable's FILLVAL.
- Hourly OMNI2 and high-res OMNI are built with different shifting/normalization; small systematic differences between them are expected.
- The time shift to the bow shock assumes planar phase fronts; during highly tilted or small-scale structures the shift can be off by minutes to ~15+ min — for precise SSC timing compare with ground magnetometers.
- Coverage gaps: when ACE/Wind/DSCOVR all lack data (maneuvers, SEP contamination of moments), OMNI plasma is blank — notably parts of extreme events (Halloween 2003 plasma has gaps).
- Dst in OMNI2 is hourly Dst (Kyoto); SYM-H in high-res OMNI is a 1-min analogue but NOT identical to Dst — don't call SYM-H minima "Dst".
- Kp is stored as Kp*10 in some products (e.g., 37 means 3.7); check the variable notes.

## Validation anchors
- **2003-10-30 Halloween storm**: hourly Dst minimum -383 nT (2003-10-30 23 UT) in OMNI2; the 2003-11-20 storm reaches Dst -422 nT — reproduce both minima.
- **2024-05-10/11 Gannon storm**: SYM-H minimum near -518 nT in high-res OMNI (Dst hourly minimum -412 nT); a modern end-to-end check including provisional-index caveats.
