# SDO (Solar Dynamics Observatory)
> One-line: NASA's flagship solar imager in geosynchronous orbit, staring at the full solar disk continuously in EUV/UV/visible plus magnetograms.

## Overview
- Launched 2010-02-11; science data from ~2010-05-01 to present. NASA (GSFC operates; instrument teams at LMSAL and Stanford).
- Inclined geosynchronous orbit over White Sands ground station — near-continuous downlink, very high data volume (~1.5 TB/day).
- The default source for "what did the Sun look like" for any event after mid-2010.

## Instruments that matter
- **AIA** (Atmospheric Imaging Assembly): full-disk EUV/UV images, 4096x4096, 12 s cadence for EUV channels (94, 131, 171, 193, 211, 304, 335 Å), 24 s for UV (1600, 1700 Å), plus 4500 Å visible at low cadence. ~0.6 arcsec/pixel.
- **HMI** (Helioseismic and Magnetic Imager): full-disk line-of-sight magnetograms (45 s cadence), vector magnetograms (720 s), continuum intensity, Dopplergrams. Source of SHARP active-region patches.
- **EVE** (EUV Variability Experiment): disk-integrated EUV irradiance spectra. MEGS-A failed 2014-05-26 (lost 6-37 nm high cadence); MEGS-B still operating with limited duty cycle.

## Key datasets and where to get them
- **JSOC** (jsoc.stanford.edu) is the authoritative archive. Key series: `aia.lev1_euv_12s`, `aia.lev1_uv_24s`, `hmi.M_45s`, `hmi.M_720s`, `hmi.B_720s` (vector), `hmi.sharp_cea_720s` (SHARPs), `hmi.Ic_45s`. Access via drms Python package (needs a registered email for exports) or sunpy `Fido` with the JSOC client.
- **VSO** (via `sunpy.net.Fido`, `a.Instrument("AIA")`, `a.Wavelength(171*u.angstrom)`) works well for modest AIA/HMI requests and needs no registration.
- Synoptic reduced-resolution AIA (1024x1024, 2-min) at `jsoc.stanford.edu/data/aia/synoptic/` — good for quicklook/movies without the full data volume.
- EVE data at LASP (lasp.colorado.edu/eve) and via CDAWeb/VSO; verify with a cdaweb dataset search for specific IDs.

## Analysis recipes
- **Flare context imagery**: AIA 131 and 94 Å for hot flare plasma (~10 MK), 171/193 for the surrounding corona and post-flare loops, 1600 Å for flare ribbons in the chromosphere, 304 Å for filament material. Fetch a +-30 min window at reduced cadence first; only pull 12 s cadence for the impulsive phase.
- **Active region magnetic context**: pull `hmi.sharp_cea_720s` for the flaring AR (match by NOAA AR number in keywords); use USFLUX, TOTUSJH keywords for flare-productivity context rather than recomputing.
- **CME/dimming**: AIA 211 and 193 base-difference images reveal coronal dimmings and EUV waves; use running-difference cautiously (it exaggerates wave speeds).
- Standard pipeline: `aiapy` for level 1 -> 1.5 (`register`, `update_pointing`), exposure normalization (`normalize_exposure`), and degradation correction (`correct_degradation`).

## Gotchas and judgment calls
- **AIA degradation**: EUV channel sensitivity has degraded severely (304 Å worst, down to a few percent of launch throughput). Any photometric or DEM work MUST apply `aiapy.calibrate.correct_degradation` with a recent calibration version; images "looking dim" in 304 late in the mission is degradation, not the Sun.
- **Saturation and blooming**: big flares saturate AIA 131/94 with diffraction spikes and bleed columns; use short-exposure frames (AIA interleaves them automatically during flares — check the EXPTIME keyword) or accept saturated cores.
- **Level 1 vs 1.5**: level 1 images from JSOC/VSO are not co-aligned across channels; always promote to 1.5 before multi-channel work.
- **Eclipse seasons**: twice yearly (near equinoxes) SDO passes through Earth eclipse, giving daily data gaps of up to ~72 min for several weeks; also occasional lunar transits. Don't interpret these gaps as instrument problems.
- HMI vector field (`hmi.B_720s`) has the 180-degree azimuth ambiguity resolved in SHARPs but noise in weak-field pixels is substantial; don't trust vector data outside strong-field regions.
- JSOC exports can queue for minutes to hours; for bulk work, request cutouts (im_patch) rather than full disks.

## Validation anchors
- **2017-09-06 X9.3 flare** (AR 12673, peak ~12:02 UT): AIA 131 shows saturated flare core at SOL location S09W34; ribbons clear in 1600 Å; SHARP for HARPNUM 7115 shows the delta-spot. Cross-check timing against GOES XRS peak.
- **2012-08-31 filament eruption** (~19:00 UT): the famous 304 Å eruption movie; a good end-to-end test of AIA fetching, prep, and movie generation.

## Degradation tooling (added 2026-09-02)
`aia_degradation(date, channels)` returns per-channel sensitivity factors
(fraction of 2010 sensitivity; aiapy/SSW series) and `correct_aia_map`
applies the correction to an AIA FITS. 304 A is the severe case: it fell to
~0.89 within weeks of first light and ~0.06 by 2020 — never compare 304 A
intensities across epochs uncorrected. Validation case `aia`.
