# Heliophysics Coordinate Systems
> Know which frame a quantity is in, which frame the physics wants, and where transforms bite.

## What it is / When to use it
Read this before comparing vector quantities across datasets, before any geoeffectiveness argument (Bz!), and before mapping solar features to in-situ data.

Frames and what they're for:
- GEO: Earth-fixed, rotates with Earth. Ground stations, geodetic locations.
- GSE (Geocentric Solar Ecliptic): X to Sun, Z ecliptic north. Natural for solar wind flow at Earth.
- GSM (Geocentric Solar Magnetospheric): X to Sun, Z chosen so Earth's dipole axis lies in the X-Z plane. THE frame for magnetospheric coupling — "southward Bz" means Bz_GSM < 0. Rotates about X relative to GSE by the diurnally/seasonally varying dipole tilt.
- HGS / Stonyhurst heliographic: solar lat/lon with lon 0 at the central meridian as seen from Earth. Flare/AR positions like "N15W30".
- HGC / Carrington heliographic: solar lat/lon rotating with the Sun (Carrington rotation period ~25.38 d sidereal / 27.2753 d synodic). Long-lived features, synoptic maps.
- HEE (Heliocentric Earth Ecliptic): Sun-centered, X toward Earth. CME propagation toward Earth.
- RTN (Radial-Tangential-Normal): spacecraft-centered; R radial from Sun, T = omega x R direction, N completes. Standard for interplanetary spacecraft field/plasma data (Parker Solar Probe, Solar Orbiter, STEREO, Ulysses).

## How to use it
- Always check the dataset's coordinate metadata (CDF variable attributes, OMNI docs) rather than assuming. OMNI provides B in both GSE and GSM.
- Python: `sunpy.coordinates` handles solar frames (HGS, HGC, HEE, and others) via astropy frames; SpacePy and geopack handle GEO/GSE/GSM; SSCWeb can return spacecraft ephemeris in your choice of frame (see sscweb skill).
- GSE -> GSM is a time-dependent rotation about the X axis; Bx is identical in both, By/Bz mix. The difference is largest around solstices and varies through the day.

## Gotchas and judgment calls
- When GSM matters: any statement about geoeffectiveness, reconnection, or "southward field" MUST use GSM Bz. Bz_GSE can differ from Bz_GSM by several nT with the dipole tilt — enough to flip marginal south/north calls.
- "Longitude" is ambiguous on the Sun: Stonyhurst W30 is not Carrington longitude; mixing them misplaces features by the rotation elapsed since the Carrington-rotation start.
- Earth-based solar longitude drifts: a fixed Stonyhurst longitude corresponds to different physical solar locations as the Sun rotates (~13.2 deg/day).
- RTN at different spacecraft are different frames (each spacecraft has its own R); comparing B components between PSP and L1 requires care, though Br sign (polarity) compares fine.
- Sign conventions differ: some old datasets use GSE with different Z handedness claims — sanity-check against a known event.
- Light-travel time and aberration are usually negligible for these purposes; dipole-axis secular drift is handled inside good libraries — use libraries, don't hand-roll GSM.

## Cross-checks
- Transform a quantity with two independent tools (e.g., sunpy/astropy vs SpacePy) and compare.
- Sanity anchors: at equinoxes GSE≈GSM differences are smallest; Bx_GSE must equal Bx_GSM exactly always.
- For solar positions, overlay the coordinate on an AIA/HMI image with sunpy Map and confirm the feature is where you think it is.
