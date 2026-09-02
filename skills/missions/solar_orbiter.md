# Solar Orbiter
> One-line: ESA/NASA encounter mission in an elliptical heliocentric orbit (perihelia ~0.28-0.5 AU, inclination rising over time), combining remote sensing and in-situ instruments off the Sun-Earth line.

## Overview
- Launched 2020-02-10; nominal science phase since ~2021-11. ESA-led with NASA participation; science archive at ESA (ESAC).
- Venus gravity assists progressively raise orbital inclination toward ~25-33 degrees for out-of-ecliptic views of the poles (late 2020s).
- Remote-sensing instruments operate mainly in ~3 windows per orbit (around perihelion); in-situ instruments run continuously. Do not assume imaging coverage for arbitrary dates.

## Instruments that matter
- **EUI**: EUV imagers — FSI (full Sun, 174 and 304 Å) and HRI (high-resolution, 174 Å and Lyman-alpha); highest-resolution EUV images of the corona during close perihelia.
- **PHI**: photospheric magnetograms (full-disk and high-res) — the only magnetograph that will ever see the solar poles well.
- **Metis**: coronagraph (visible + UV Lyman-alpha).
- **SPICE**: EUV spectrometer (plasma diagnostics, composition/FIP bias for linkage science).
- **SWA**: solar wind analyzer — PAS (proton/alpha moments), EAS (electrons), HIS (heavy ion composition).
- **MAG**: fluxgate magnetometer, the workhorse in-situ instrument.
- **EPD**: energetic particle detector suite (STEP, EPT, HET, SIS).
- **RPW**: radio and plasma waves.

## Key datasets and where to get them
- **Solar Orbiter Archive (SOAR)** at soar.esac.esa.int is authoritative; Python access via `sunpy-soar` (adds `a.soar.Product` to Fido). Data levels: L2 is the analysis level for most instruments.
- **Low-latency (LL) vs science**: LL02 products exist for ops/planning — compressed, coarse, not calibrated for science. Use them only for event scouting; redo everything with L2 science data (which can lag weeks to months due to limited downlink).
- Typical L2 product names follow patterns like `mag-rtn-normal` (1 Hz-ish normal mode), `swa-pas-grnd-mom` (PAS ground moments), `eui-fsi174-image`, `epd-ept-*-rates`. Search SOAR by instrument + level rather than guessing full IDs.
- Some in-situ L2 data are mirrored on CDAWeb (`SOLO_L2_MAG-RTN-NORMAL`, `SOLO_L2_SWA-PAS-GRND-MOM` — verify with a cdaweb dataset search).

## Analysis recipes
- **In-situ context at another heliocentric distance**: load MAG RTN + SWA-PAS moments for your interval; always fetch the spacecraft ephemeris (distance and longitude) first — scaling B and n by expected r-dependence (B ~ r^-2 radial, n ~ r^-2) before comparing to 1 AU data.
- **Connectivity/linkage**: for an SEP event, combine EPD onset times with a ballistic back-mapping using the measured solar wind speed from PAS to estimate the magnetic footpoint; compare against flare location from EUI FSI or Earth-side imagery.
- **High-res EUV fine structure**: EUI HRI 174 during perihelion windows (campfires, fine loops); check the observation timeline first — HRI runs only in short campaigns.

## Gotchas and judgment calls
- **Coverage is windowed and downlink-limited**: absence of EUI/PHI/SPICE data for a date usually means no observation was scheduled, not data loss. Check SOAR before promising imagery.
- Varying heliocentric distance means cadence and telemetry modes change constantly; time axes are spacecraft UTC — light-travel-time to Earth differs from Earth-based observations by minutes, and radial position matters for event timing comparisons.
- SWA-PAS has had operational gaps and quality flags matter (`quality_factor` in the CDF); moments during spacecraft maneuvers/thruster firings are suspect.
- PHI magnetograms have different calibration heritage than HMI; do not blindly cross-calibrate flux values.
- LL data in plots circulating on social media often disagree with final L2 calibration — never cite LL numbers.
- RTN coordinates at large longitudinal separation from Earth are not comparable component-by-component to GSE/GSM data at L1.

## Validation anchors
- **2022-03 perihelion (first close pass, ~0.32 AU)**: EUI HRI imagery and the widely published full-Sun mosaic; MAG/SWA show clear switchback patches — good end-to-end SOAR retrieval test.
- **2021-10-28 GLE event**: EPD observed the SEP event also seen at Earth (GLE73) — cross-check EPD HET onset vs GOES proton onset with appropriate path-length reasoning.
