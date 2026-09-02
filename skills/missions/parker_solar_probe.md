# Parker Solar Probe (PSP)
> One-line: NASA probe diving repeatedly into the solar corona (perihelia now inside 10 solar radii), measuring nascent solar wind fields, particles, and white-light structure in situ.

## Overview
- Launched 2018-08-12; Venus gravity assists shrank perihelion in steps — from ~35.7 Rs (Enc. 1, Nov 2018) to ~9.86 Rs (final orbit geometry reached with Enc. 22, Dec 2024). NASA/APL.
- Data are encounter-centric: full-cadence science happens in ~10-day windows around each perihelion; cruise data are sparse or absent for some instruments. Know the encounter number/dates for your interval before searching.
- Downlink lags perihelia by weeks to months.

## Instruments that matter
- **FIELDS**: fluxgate + search-coil magnetometers, electric fields, plasma waves, radio. The magnetic field data (MAG) is the primary product — source of the switchback discoveries.
- **SWEAP**: SPC (Faraday cup proton/alpha moments; degrades usefulness very close in) and SPAN-A/SPAN-B (electrostatic analyzers for ions/electrons; SPAN-I becomes the main ion instrument at close perihelia).
- **ISOIS**: energetic particles — EPI-Lo (~tens of keV to ~MeV) and EPI-Hi (~1 to >100 MeV/nuc).
- **WISPR**: wide-field white-light heliospheric imager looking anti-ramward — streamer blobs, dust-free zone, even Venus surface glimpses.

## Key datasets and where to get them
- CDAWeb carries the public level-2 data: `PSP_FLD_L2_MAG_RTN` (full cadence) and `PSP_FLD_L2_MAG_RTN_4_SA_PER_CYC` (~4 samples/cycle, manageable volume), `PSP_SWP_SPC_L3I` (SPC proton moments), `PSP_SWP_SPI_SF00_L3_MOM` (SPAN-I moments), `PSP_ISOIS-EPIHI_L2-HET-RATES60` and EPI-Lo equivalents — verify exact IDs with a cdaweb dataset search before scripting.
- Instrument-team archives: FIELDS at Berkeley (fields.ssl.berkeley.edu), SWEAP at SAO/UMich, WISPR at NRL; SPDF/CDAWeb mirrors are usually sufficient.
- `pyspedas.psp` loaders wrap the CDAWeb datasets conveniently.
- WISPR images via the NRL WISPR site or the Virtual Solar Observatory.

## Analysis recipes
- **Encounter overview**: load MAG RTN (4/cyc version) + SPC or SPAN-I moments for the encounter window; plot Br to spot switchbacks (polarity-reversing spikes with |B| roughly constant); mark perihelion time and radial distance on all plots.
- **Which ion instrument**: early encounters (roughly 1-8) SPC is the primary proton monitor; at closer perihelia the flow shifts into SPAN-I's field of view — check both, prefer the one with sensible, continuous moments for your interval, and never average them blindly.
- **Sub-Alfvenic intervals**: compute the Alfven speed from B and density and compare to measured flow speed; PSP first crossed into sub-Alfvenic corona 2021-04-28 (Encounter 8, ~18.8 Rs).

## Gotchas and judgment calls
- **Radial scaling**: B ~ tens to hundreds of nT and n orders of magnitude above 1 AU values near perihelion — comparisons to 1 AU data require r^-2 (Br, n) normalization; never plot PSP and OMNI on shared axes without it.
- **SPC degradation/FOV**: SPC measurements degrade near closest approach (flow moves off the cup's optimal range; instrument aging); the SPC/SPAN-I handoff means density/velocity jumps between datasets are instrumental, not physical.
- Encounter-only coverage: an empty query for a cruise-phase date is normal.
- FIELDS full-cadence MAG files are enormous; use the 4_SA_PER_CYC or 1-min products unless you need waveforms.
- Spacecraft frame vs RTN: some L2 products are in spacecraft coordinates; check the variable metadata.
- Time tags are at the spacecraft; for solar-event timing at Earth account for both light travel time and PSP's position.

## Validation anchors
- **Encounter 1 (2018-11, perihelion ~35.7 Rs)**: switchbacks in Br and slow-wind ubiquity — reproduce the canonical Br spike plots from the 2019 Nature papers using PSP_FLD_L2_MAG_RTN + SPC.
- **2021-04-28 sub-Alfvenic crossing (E8)**: verify Va > Vsw over the published interval near 18.8 Rs.
