# STEREO (Solar TErrestrial RElations Observatory)
> One-line: twin NASA spacecraft in Earth-leading (Ahead) and Earth-trailing (Behind) heliocentric orbits, giving off-Sun-Earth-line imaging of CMEs and in-situ solar wind at ~1 AU.

## Overview
- Launched 2006-10-26; STEREO-A (Ahead) still operating; STEREO-B (Behind) contact lost 2014-10-01 (brief 2016 recovery, then lost for good).
- Each drifts ~22 degrees/year from Earth; separation angle from Earth changes continuously — always compute the spacecraft position for your epoch before interpreting images.
- NASA; operated from APL/GSFC. The unique asset: side views of Earth-directed CMEs.

## Instruments that matter
- **SECCHI** suite: EUVI (EUV disk imager, 171/195/284/304 Å), COR1 (1.5-4 Rs) and COR2 (2.5-15 Rs) coronagraphs, HI-1 and HI-2 heliospheric imagers (tracking CMEs from ~15 Rs to beyond 1 AU).
- **IMPACT**: magnetometer (MAG) and solar wind electrons (SWEA), plus SEP suite (LET, HET, SEPT) for energetic particles.
- **PLASTIC**: solar wind proton/alpha moments and composition.
- **SWAVES**: radio spectrograph (type II/III bursts, interplanetary shocks).

## Key datasets and where to get them
- **Beacon vs science**: beacon data is real-time, low-resolution, lossy-compressed — for space weather ops only. Always use science-quality data for analysis; it arrives days later. Beacon lives under separate directories/IDs; do not mix.
- SECCHI science FITS via VSO (`Fido`, `a.Instrument("EUVI"/"COR2"/"HI1"...)`, `a.Source("STEREO_A")`) or the NRL/UKSSDC SECCHI archives. Typical cadences: EUVI 195 ~5 min (varies by channel/era), COR2 ~15 min, HI-1 ~40 min, HI-2 ~2 h.
- In-situ via CDAWeb: `STA_L2_MAGPLASMA_1M` (merged 1-min MAG+PLASTIC, convenient), `STA_L1_MAG_RTN` (magnetic field, RTN), PLASTIC and IMPACT/SEP level-2 IDs — verify exact IDs with a cdaweb dataset search. Substitute STB_ for Behind (through 2014 only).
- CME catalogs from STEREO: HELCATS catalogs (HIGeoCat etc.) for HI-tracked CMEs; COR2 CACTus.

## Analysis recipes
- **Earth-directed CME triangulation**: for an Earth-directed halo in LASCO, STEREO-A COR2 sees it near the limb — measure the plane-of-sky speed there for a much better radial speed than the LASCO halo gives. Combine with GCS (graduated cylindrical shell) forward modeling if two viewpoints exist.
- **CME arrival tracking**: HI-1/HI-2 time-elongation maps (J-maps) along the ecliptic; fit with fixed-phi or self-similar-expansion geometry to get speed and direction; propagate to 1 AU arrival.
- **In-situ at a different longitude**: load STA_L2_MAGPLASMA_1M around the event to see whether the CME/HSS also swept over STEREO-A — powerful for constraining CME angular width and CIR corotation timing (a stream seen at A arrives at Earth days later when A leads Earth... note: A leading means A sees corotating streams BEFORE Earth).

## Gotchas and judgment calls
- **STEREO-B is gone after 2014-10-01.** Any analysis plan invoking STEREO-B for later dates is wrong.
- **Solar conjunction gap**: both spacecraft passed behind the Sun ~2014-2016; STEREO-A data has gaps and reduced telemetry (2014-08 to 2015-11 roughly); side-lobe operations affected cadence into 2016.
- Spacecraft longitude changes constantly — "STEREO-A view" means nothing without the separation angle; get it from solarmap/sunpy coordinates (`get_horizons_coord` or spice kernels).
- HI images require careful background (F-corona/starfield) subtraction; use running-difference or the level-2 background-subtracted products from UKSSDC rather than DIY.
- STEREO-A post-2023 is again near Earth's line (passed between Sun-Earth line in 2023) — its "side view" advantage varies with epoch.
- PLASTIC proton moments have era-dependent quality issues; sanity-check density/speed against OMNI when the spacecraft was near Earth's longitude.

## Validation anchors
- **2012-07-23 extreme CME**: hit STEREO-A head-on; in-situ B exceeded 100 nT with ~2000+ km/s transit speed — a canonical extreme-event benchmark in STA MAG/PLASTIC data.
- **2008-12-12 CME**: classic HI-1/HI-2 Earth-directed tracking event used in many J-map method papers.
