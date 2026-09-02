# IMAP (Interstellar Mapping and Acceleration Probe)
> One-line: NASA's newest L1 mission (launched 2025-09-24) mapping the heliosphere's boundary via energetic neutral atoms while serving as a next-generation real-time solar wind monitor.

## Overview
- Launched 2025-09-24 (shared ride with Carruthers Geocorona Observatory and SWFO-L1); cruise to L1 takes months, followed by commissioning — expect routine science data flow to begin during 2026. NASA; PI institution Princeton, operations/SOC at APL/LASP (verify current SOC arrangements).
- Two roles: (1) ENA imaging of the outer heliosphere (successor to IBEX), pickup ions, interstellar neutrals, dust; (2) an operational real-time solar wind and SEP broadcast ("I-ALiRT") supporting space weather forecasting alongside/after DSCOVR and ACE.
- As of early 2026 this is a young mission: treat any dataset ID, cadence, or archive path as provisional and verify against the IMAP SOC / SPDF before scripting.

## Instruments that matter
- **IMAP-Lo, IMAP-Hi, IMAP-Ultra**: ENA imagers spanning ~eV to ~keV-100s keV ranges — global maps of the heliosheath (the IBEX "ribbon" at higher resolution/sensitivity).
- **SWAPI**: solar wind protons/alphas and interstellar pickup ions.
- **SWE**: solar wind electrons.
- **MAG**: magnetometer (dual fluxgates).
- **CoDICE**: suprathermal/energetic ion composition and charge states.
- **HIT**: high-energy ion telescope (SEPs, ~MeV to ~100 MeV/nuc).
- **IDEX**: dust analyzer; **GLOWS**: heliospheric Lyman-alpha glow photometer.

## Key datasets and where to get them
- Primary archive planned via the IMAP Science Operations Center with mirroring to NASA SPDF/CDAWeb; the team publishes the `imap-processing`/SOC tooling openly on GitHub. No stable public CDAWeb dataset IDs can be assumed yet — verify with a cdaweb dataset search once data are public.
- Real-time solar wind: the I-ALiRT broadcast is intended to feed NOAA SWPC-style real-time streams (MAG, SWAPI, SEP quantities). NOAA's SWFO-L1, launched on the same rocket, becomes the operational primary; distinguish the two when citing "real-time L1 data" post-2026.
- ENA maps will be released as periodic (roughly 6-month) all-sky map products, analogous to IBEX map releases.

## Analysis recipes
- **Once data flow**: solar wind event context at L1 — MAG + SWAPI moments, same recipe as ACE/Wind (common cadence resample, FILLVAL masking), with cross-calibration against Wind for the overlap era as the first sanity exercise.
- **Heliosheath science**: compare first IMAP-Hi ENA maps against the final IBEX map epoch for ribbon stability; this is a map-differencing exercise, mind the different energy passbands.
- **Suprathermal seed population studies**: CoDICE charge states + HIT SEP fluxes around large events — the mission's "Acceleration" half.
- Until then: use IMAP documentation/SOC status pages to answer availability questions; do not fabricate data products.

## Gotchas and judgment calls
- **The dominant gotcha is prematurity**: papers, IDs, calibrations, and cadences are in flux through commissioning. Any pipeline built now must fail loudly if a dataset is absent rather than silently substituting.
- Spin-stabilized spacecraft (~15 s spin): time resolution of many products is spin-gated; ENA maps accumulate over months — "cadence" means something different per instrument class.
- Don't conflate IMAP with SWFO-L1 (NOAA operational) or with ACE/DSCOVR continuity claims.
- ENA fluxes are line-of-sight integrals through the heliosheath; interpreting map features as localized structures is a modeling exercise, not an observation.

## Validation anchors
- **IBEX ribbon reproduction**: when the first IMAP ENA maps arrive, recovering the known IBEX ribbon geometry (a circular arc of enhanced ~keV ENA flux) is the natural first validation.
- **L1 cross-calibration**: overlap-period comparison of IMAP MAG/SWAPI vs Wind MFI/SWE on quiet solar wind — agreement within calibration uncertainties validates ingestion.
