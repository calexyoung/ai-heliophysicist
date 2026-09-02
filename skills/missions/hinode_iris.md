# Hinode and IRIS
> One-line: two Sun-pointing spectroscopy/high-resolution imaging observatories in sun-synchronous LEO — Hinode (JAXA/NASA/ESA, 2006-) for photospheric magnetism, X-ray corona, and EUV spectroscopy; IRIS (NASA SMEX, 2013-) for the chromosphere-transition-region interface.

## Overview
- **Hinode**: launched 2006-09-22; JAXA-led with NASA/ESA/UKSA. Instruments: SOT (optical telescope + spectropolarimeter), XRT (X-ray telescope), EIS (EUV imaging spectrometer).
- **IRIS**: launched 2013-06-27; NASA SMEX operated by LMSAL. FUV/NUV imaging spectrograph + slit-jaw imager.
- Both are pointed, targeted observatories — they observe a chosen region with a chosen program, NOT full-disk synoptics. Coverage for your event exists only if a plan targeted it; check the observation catalogs first, always.
- Both fly sun-synchronous LEO; eclipse seasons and SAA passages punctuate the data.

## Instruments that matter
- **Hinode/SOT-SP** (spectropolarimeter): precision photospheric vector magnetograms from Fe I 6301/6302 Å — the gold standard for small-FOV field measurements (better than HMI within its patch). SOT filtergraph (FG) failed 2016-02; SP still works.
- **Hinode/XRT**: soft X-ray corona imaging, multiple filters — hot plasma (>2 MK) that AIA sees poorly.
- **Hinode/EIS**: EUV slit spectra (~170-210, 250-290 Å) — Doppler velocities, densities (line ratios), abundances/FIP bias in the corona.
- **IRIS spectrograph**: Mg II h/k (chromosphere), C II, Si IV (transition region), plus O IV density diagnostics; rasters (sit-and-stare, sparse, dense) with slit-jaw imaging in Mg II/Si IV/C II passbands.

## Key datasets and where to get them
- **IRIS**: level-2 FITS (calibrated rasters + SJI) from LMSAL (iris.lmsal.com, search by OBSID via the "IRIS data search"); also via VSO/`Fido` (`a.Instrument("IRIS")`). `irispy-lmsal` reads L2. Each observation has an OBSID encoding the program (raster type, exposure, binning).
- **Hinode**: the Hinode SDC (Oslo) and DARTS (JAXA) archives; VSO carries much of it (`a.Instrument("EIS"/"XRT"/"SOT")`). EIS analysis traditionally in SolarSoft (`eis_prep`); Python via `eispac` (uses re-calibrated HDF5 files from NRL). SOT-SP level-2 inversions (Milne-Eddington, from HAO) are downloadable — use those rather than re-inverting Stokes profiles.
- Cadences/coverage are program-defined; consult the Hinode operation plans and IRIS timeline rather than assuming.

## Analysis recipes
- **Was my event observed?**: query the IRIS search by time+coordinates and the Hinode SDC/EIS catalog before designing anything. If pointing missed the region, stop.
- **Flare chromospheric response**: IRIS Mg II k line — reversals, redshifted ribbons (chromospheric condensation ~20-40 km/s downflows in Si IV/Mg II); slit position vs ribbon location determines what you can claim.
- **Coronal Doppler shifts pre-flare/eruption**: EIS Fe XII 195.12 velocity maps; blueshifted outflows at AR edges; density from Fe XII 186/195 ratio via eispac.
- **Precision AR field**: SOT-SP scan inverted vector field for the target AR patch; compare with the co-temporal HMI SHARP to calibrate expectations of HMI noise.

## Gotchas and judgment calls
- **Targeted pointing is the number one trap**: no catalog hit = no data; near-misses (slit 20" from the ribbon) silently produce null results.
- IRIS OBSID decoding matters — exposure times and raster geometry vary hugely; deep exposures saturate in flares (flare programs use short exposures + lossy compression choices).
- EIS wavelength calibration has orbital thermal drift; velocity zero-points must be established per raster (e.g., quiet-Sun reference) — absolute Doppler velocities below ~5 km/s are not free.
- SOT FG (filtergrams/movies) unavailable after 2016-02; SP scan durations mean a "magnetogram" is not a snapshot (tens of minutes per map).
- South Atlantic Anomaly and eclipse-season gaps pepper the light curves of both missions; spikes in IRIS/EIS detectors from particle hits need despiking.
- IRIS Mg II is optically thick — naive Gaussian fitting of the line core is wrong; use standard moment/feature measures (k2/k3 features) or inversion tools (IRIS^2).

## Validation anchors
- **2014-03-29 X1 flare (SOL2014-03-29T17:48)**: the best-observed flare in history — IRIS, Hinode/EIS+SOT, SDO simultaneously; reproduce the IRIS Si IV redshifted ribbon spectra from the published studies.
- **EIS AR outflows (e.g., AR 10978, 2007-12)**: canonical blueshifted-outflow velocity maps — validates the eispac fitting + velocity calibration chain.
