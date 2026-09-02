# GOES (Geostationary Operational Environmental Satellites)
> One-line: NOAA's geostationary fleet whose XRS soft X-ray fluxes define flare classes (C/M/X), plus energetic particle, magnetometer, and (GOES-R era) EUV imaging.

## Overview
- Continuous series since 1975; the space-weather-relevant generations: GOES 8-12, GOES 13-15 (NOP era, ~2006-2020), GOES 16-19 (GOES-R era, 2017-present, with SUVI and improved XRS/EXIS). NOAA operates; data via NCEI and SWPC.
- Geostationary orbit (6.6 Re) — inside the magnetosphere; particle data are trapped+SEP mixed, X-ray data are disk-integrated solar.

## Instruments that matter
- **XRS**: soft X-ray irradiance in two bands — XRS-B "long" 1-8 Å (defines flare class: X = 1e-4 W/m^2) and XRS-A "short" 0.5-4 Å. Cadence 1-3 s (GOES-R), ~2 s (13-15).
- **SUVI** (GOES-16+): full-disk EUV imager, 6 channels (94/131/171/195/284/304 Å), ~4 min per-channel cadence — operational AIA-lite; wider FOV than AIA (good for big eruptions off-limb).
- **EPS/SEISS**: energetic protons (>10, >50, >100 MeV integral channels define S-scale radiation storms) and electrons (>2 MeV fluence for satellite charging).
- **MAG**: geostationary magnetic field — magnetopause crossings, storm sudden commencements.
- **EUVS (EXIS)**: solar EUV irradiance lines.

## Key datasets and where to get them
- **XRS via sunpy Fido**: `Fido.search(a.Time(...), a.Instrument("XRS"), a.goes.SatelliteNumber(16))` fetches NCEI netCDF; `ts.TimeSeries(...)` handles it natively. Science-quality 1-s and 1-min averaged files at NCEI (ngdc/ncei "goes-r xrs" paths).
- **SWPC real-time**: services.swpc.noaa.gov/json/goes/primary/xrays-*.json (rolling), plus proton/electron JSON — nowcast only.
- **Flare event lists**: SWPC daily event reports; the (discontinued 2017+authority varies) NOAA flare lists; HEK (`Fido` HEK client, `a.hek.FL`) for flare start/peak/end and locations.
- SUVI level-2 composites via NCEI; also `Fido` with `a.Instrument("SUVI")`.
- Particle data: NCEI netCDF (SEISS for GOES-R; EPS for earlier). Verify specific dataset paths per satellite generation.

## Analysis recipes
- **Flare identification and classing**: load XRS 1-min for the day; flare class = peak XRS-B flux (A/B/C/M/X = 1e-8...1e-4 W/m^2 decades). Background-subtract for weak flares near an elevated background. Ratio XRS-A/XRS-B gives an isothermal temperature proxy (harder = hotter).
- **SEP radiation storm**: >10 MeV integral proton flux crossing 10 pfu = S1 onset; log-plot the three integral channels; onset time vs flare time gives a connectivity/transit constraint.
- **Flare location when AIA is unavailable**: SUVI 131/94 for the flare kernel (GOES-16+ era).

## Gotchas and judgment calls
- **Scaling factors changed between generations**: GOES 8-15 XRS fluxes were divided by ~0.7 (long) and ~0.85 (short) "SWPC scaling factors" for operational continuity; GOES-R science data are TRUE fluxes with no scaling. A flare classed X9.3 operationally (2017-09-06, GOES-15 era convention) is ~30% larger in true GOES-16 flux. NOAA re-baselined flare classes to unscaled values — be explicit about which convention any archival flare class uses, or cross-era statistics will be silently inconsistent by ~1/0.7.
- **Saturation**: GOES 13-15 XRS saturated near X17-X20 class; GOES-R does not (measured X45 in legacy units unclear — the 2003-11-04 event, est. X28-X45, saturated GOES-12).
- Big flares contaminate the proton channels (X-ray crosstalk) on older EPS; conversely SEP storms can slightly contaminate XRS.
- Eclipse seasons: geostationary satellites pass through Earth's shadow near equinoxes — short nightly XRS gaps.
- Multiple satellites operate simultaneously; "primary" designation changes — SWPC JSON gives the primary; for science pick one satellite explicitly and state it.
- Proton channels are integral, and geostationary local time/magnetic shielding modulates lower-energy channels; >10 MeV is fairly clean, lower energies are not pure SEP.

## Validation anchors
- **2017-09-06 X9.3 flare**, peak 12:02 UT (GOES-15 scaled convention; ~X13 in true-flux re-baselined units): the largest of cycle 24 — your XRS pipeline must reproduce class, peak time, and the earlier X2.2 the same day.
- **2003-10-28 X17** (~11:10 UT) followed by the saturated 2003-11-04 event — a good test that your code flags saturation instead of reporting a fake peak.
