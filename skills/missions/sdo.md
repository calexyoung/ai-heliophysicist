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

## Tool: `magnetogram_metrics` (ported from helio-agent 2026-09-03)
- Input: a full-disk HMI LOS magnetogram FITS. Fetch it with `fetch_vso instrument="HMI" physobs="LOS_magnetic_field"` — without `physobs` the VSO hands back the continuum (`hmi.ic_45s`) first, and the tool refuses non-Gauss files. One 4096x4096 file is ~16 MB; `max_files=1`.
- Region box in heliographic Stonyhurst degrees (DONKI/HEK flare convention, west positive), projected through the map WCS. Outputs: unsigned and signed flux (Mx), max |B|, strong-PIL length (pixel chain x pixel size) and the flux threaded through it, plus disk unsigned flux.
- Reference values from AR 12673 at 2017-09-06 11:01 UT (S09W33, 16-deg box): 2.8e22 Mx, max |B| 2255 G, strong PIL 586 Mm threading 3.1e20 Mx; the mirrored quiet box held 1.5e21 Mx and no PIL; full disk 3.1e23 Mx. A delta region shows hundreds of Mm of strong PIL; a simple bipole shows tens or none.
- Limits: LOS field only, no mu correction (flux is a lower bound away from disk center; at W33 the cos factor is ~0.84), 45 s magnetograms carry ~10 G noise (`noise_g` = 20 clips it), and the PIL is a pixel-chain proxy, not the Schrijver R value. For published-grade AR flux use the SHARP keywords (USFLUX) and cite them.
- Cross-check the box position against the HEK/DONKI flare location and the NOAA AR number; the box is 8 deg half-width by default and a large region can exceed it.

## Tool: `plot_solar_regions` (added 2026-09-04)
- Renders any solar FITS sunpy can read and marks NOAA-numbered regions on it, labelled with McIntosh (`spot_class`) and Mount Wilson (`mag_class`, printed as Greek). `regions` defaults to the live `get_solar_regions` summary; pass records explicitly for a historical date.
- **Positions go through the map's WCS**, so B0 and P are handled by sunpy. Do not sketch regions on a flat lat/lon disk instead: on 2017-09-06 (B0 = +7.24°) that error reaches 151 px — 0.08 R_sun — for a region near disk centre. Validated against the analytic identity r/R = sin(arccos(sin φ sin B0 + cos φ cos B0 cos λ)) to better than 0.006 R_sun; the small residual is SDO's finite distance, which the identity ignores.
- **The map and the region report must be contemporaneous.** SWPC stamps its daily summary at a synoptic time, and the Sun turns ~13.2°/day synodic, so `max_age_hours` (12 by default) refuses a stale pairing and names the drift. This bites in practice: VSO's HMI runs ~5 days behind real time, so annotating today's regions on the newest available HMI is refused at ~59° of drift. **AIA is current** — use AIA 1600 Å as the backdrop for a same-day figure, or accept HMI for retrospective work.
- Regions past the limb land in `off_disk` with their longitude rather than being clamped to the edge. Visibility is decided in heliocentric coordinates (z > 0), not guessed from longitude.
- SWPC nulls `spot_class`/`mag_class` for regions it has stopped classifying — in practice ones rotating off the west limb. Those label by number alone and the count appears in the result `note`; the tool never invents a class.
- **This is not a detection.** It draws where SWPC says a region is. Confirm against the image, or run `magnetogram_metrics` at the same coordinates for an independent measurement of whether field is actually there.
- Validation: `uv run python validation/run_validation.py regions`.

## Input pins (added 2026-09-04)
`fetch_vso` downloads through sunpy's Fido, a **library-managed transfer that the repo's content-addressed HTTP cache does not cover** (see `helio_agent/http.py`). Emptying `workspace/cache` does not make a VSO fetch cold, and nothing local pinned the file — so a JSOC reprocessing would move `magnetogram.ar12673` and `regions.project` silently.

`validation/run_validation.py hmipin` pins the 2017-09-06 11:01 TAI HMI magnetogram in three layers:
- **Bytes** — SHA-256 `d48aaffe…`. Confirmed meaningful, not trivially true: deleting the local copy and re-fetching from VSO returned byte-identical data, so the checksum tests the archive rather than the disk.
- **Header** — T_REC, `CRLT_OBS` 7.234973 (B0), `CROTA2` 179.929718, `CDELT1`, `RSUN_OBS`, 4096². The `regions` case's 0.006 R_sun agreement with analytic spherical geometry depends on that B0.
- **Derived science, exactly** rather than the order-of-magnitude bands `magnetogram.ar12673` asserts: disk flux 3.0785e23 Mx, AR-box flux 2.8429e22 Mx, max |B| 2255.3 G, PIL 585.9 Mm / 3.1439e20 Mx, and the quiet control box at 1.8397e21 Mx with no PIL.

Each layer was verified to trip by perturbing it. A failure most likely means the archive reissued the file, not that the code broke.

Note Fido does **not** skip a download when the file is already present (a repeat fetch still takes ~7 s), so these pins re-verify the remote copy on every validation run.

## Tool: `fetch_aia_synoptic` (added 2026-09-05)
- **The VSO AIA route is unreliable and fails loudly now.** `fetch_vso(instrument="AIA", ...)` searches fine but the export provider it hands off to (`sdo7.nascom.nasa.gov/cgi-bin/drms_export.cgi`) times out on the socket read after ~90 s, on every request tried during the May 2024 reproduction. `fetch_vso` previously returned `status: "ok"` with `files: []` in that case, which reads as "no data exists" — it now returns an error naming the provider and pointing here. HMI and LASCO go through different providers and are unaffected.
- `fetch_aia_synoptic` pulls from the JSOC synoptic archive (`jsoc1.stanford.edu/data/aia/synoptic`): plain static HTTP, ~1.3 MB per frame, answers in seconds.
- **What you get is level 1.5 synoptic, not level 1.** 1024×1024 at ~2.4 arcsec/pix instead of 4096² at ~0.6, already registered and rotated to solar north. Right for context imaging, morphology, eruption timing, multi-wavelength comparison. Wrong for native-resolution structure (fine loop widths) or pixel-level photometry — for those you need the level-1 records, which means waiting out VSO or going to JSOC/drms directly.
- The archive is on a strict **2-minute grid**; the requested time is floored onto it, so asking for 05:10:59 and 05:10:00 returns the same frame. `cadence_minutes` must be even.
- Channels carried: 94, 131, 171, 193, 211, 304, 335, 1600, 1700, 4500. **193, not 195** — asking for 195 (the EIT/EUVI line) is refused by name rather than fetched and failed.
- `aia_degradation` still applies: the synoptic product is not degradation-corrected, so a multi-year intensity comparison still needs the correction factor.
- Validation: `uv run python validation/run_validation.py aiasyn`.

## Tool: `fetch_aia_level1` (added 2026-09-05)
- Full-resolution AIA straight from JSOC through `drms`: 4096×4096 at ~0.6 arcsec/pix, the native product. Use it when the science needs native resolution or the level-1 calibration chain (loop widths, pixel photometry, precise flare morphology). `fetch_aia_synoptic` is ~10× smaller and much faster, and is the right choice for context imaging.
- **Needs a JSOC-registered email** (`JSOC_EMAIL` in `.env`, or the `jsoc_email` argument). Registered for this repo on 2026-09-05. Without it the tool refuses by name — it does **not** fall back to the synoptic product, because silently returning a 16× smaller image under the same call is exactly the substitution the contract forbids.
- Uses `method="url_quick"`, `protocol="as-is"`: JSOC serves files already on disk and answers immediately, no export queue. A record JSOC would have to stage is reported as such rather than waited on. One 171 Å frame is ~12 MB and downloads in ~20 s.
- **Level 1 is not level 1.5.** The file is neither registered to solar north nor plate-scale normalised — `CROTA2` is small but nonzero (0.019° on the validated frame). Run `aiapy.calibrate.register` before comparing channels pixel to pixel, and `correct_aia_map` for degradation. A `CROTA2` of exactly 0 means someone already registered it.
- Series are chosen by channel: `aia.lev1_euv_12s` (94–335 Å), `aia.lev1_uv_24s` (1600/1700), `aia.lev1_vis_1h` (4500). 195 Å is not an AIA channel and is refused by name.
- Check `QUALITY` in the header before using a frame; 0 is clean.
- Validation: `uv run python validation/run_validation.py aial1` (skips cleanly when `JSOC_EMAIL` is unset).
