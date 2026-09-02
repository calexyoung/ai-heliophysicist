# Solar Orbiter Low-Latency and STEREO Beacon Data
> Quick-look data from off-Sun-Earth-line spacecraft — hours-fresh, NOT science quality.

## What it is / When to use it
Solar Orbiter and STEREO-A view the Sun/heliosphere from vantage points away from Earth. Both downlink small, quickly-processed data streams for space weather use, long before the full science telemetry arrives. Use these for: near-real-time context from another longitude (e.g., is that far-side region active?), early CME viewing geometry, and situational awareness — never for calibrated measurement.

## How to use it
- Solar Orbiter low latency (LL02 products): mirrored at `https://umbra.nascom.nasa.gov/solar_orbiter/` (SDAC mirror of ESA's low-latency products; ESA's Solar Orbiter Archive SOAR at https://soar.esac.esa.int is the primary archive for both LL and science data). LL02 covers in-situ (MAG, SWA, EPD) and remote-sensing quicklooks (EUI, others when operating). Latency: typically hours to ~1 day depending on ground-station passes.
- STEREO beacon: `https://stereo-ssc.nascom.nasa.gov/data/beacon/` — continuous low-rate real-time broadcast received by partner ground stations. Browse images at the STEREO Science Center. Beacon in-situ data are also on CDAWeb as `STA_LB_*` datasets (e.g., `STA_LB_IMPACT`, `STA_LB_PLASTIC` — list with cdasws to confirm exact IDs). STEREO-B has been lost since 2014; only STEREO-A ("STA") is live.
- Science-quality replacements arrive later: STEREO L1/L2 (`STA_L1_MAG_RTN`, etc.) days-weeks later; Solar Orbiter L2 via SOAR/CDAWeb weeks-months later. Re-run anything quantitative on those.

## Gotchas and judgment calls
- NOT science quality — this is the headline: beacon/LL data are heavily compressed, decimated, auto-calibrated with preliminary (sometimes wrong) calibration files, and gap-riddled. Magnetometer offsets in particular may be uncorrected; plasma moments can be systematically off. Treat every number as ±tens of percent and every gap as unremarkable.
- Beacon coverage depends on volunteer/partner antenna time — expect daily gaps.
- Solar Orbiter's distance and longitude change constantly (0.28-1.0 AU); always fetch ephemeris (SSCWeb/SPICE) before interpreting timing or comparing with 1 AU — do not assume it's near Earth.
- Remote-sensing instruments on Solar Orbiter only operate during designated windows; no images ≠ no activity.
- Time tags in LL products can be less rigorously corrected than science products.
- STA identifiers: "ahead" spacecraft; RTN frame for field data (see coordinate_systems).

## Cross-checks
- When the science-quality files land, re-pull and compare — expect noticeable calibration shifts.
- Cross-check STEREO-A beacon in-situ features against L1 monitors with a Parker-spiral/longitude mapping (see cross_spacecraft) when separation is small.
- Validate an LL "far-side active region" claim against helioseismic far-side maps (GONG/HMI) or wait for rotation onto the visible disk.
