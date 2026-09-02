# THEMIS / ARTEMIS
> One-line: five NASA probes launched to time substorm onset in Earth's magnetotail; three (THEMIS A/D/E) still orbit Earth, two (ARTEMIS P1/P2, formerly B/C) moved to lunar orbit in 2011.

## Overview
- Launched 2007-02-17; five identical spacecraft plus a dedicated ground-based all-sky imager (ASI) and magnetometer network across North America. NASA; SSL Berkeley runs operations and software.
- THEMIS A/D/E: elliptical Earth orbits (~10-12 Re apogee) sampling the magnetotail, dayside magnetosphere, and solar wind seasonally. ARTEMIS P1/P2: lunar-distance (~60 Re) — excellent solar wind and distant-tail monitors.
- Strengths: multi-point tail dynamics, conjugate ground-space substorm studies, and ARTEMIS as an upstream monitor at a different location than L1.

## Instruments that matter
- **FGM**: fluxgate magnetometer.
- **ESA**: electrostatic analyzer — ion and electron moments (~few eV to 30 keV).
- **SST**: solid state telescope — energetic particles (~25 keV to ~1 MeV).
- **EFI**: electric field; **SCM**: search coil (waves).
- **GBO ASIs**: white-light all-sky auroral imagers (3-s cadence, ~20 stations) — auroral substorm onset timing; **GMAGs**: ground magnetometers.

## Key datasets and where to get them
- Standard access: `pyspedas.themis` loaders (wrap the SSL Berkeley archive; also mirrored on CDAWeb as e.g. `THA_L2_FGM`, `THA_L2_ESA`, `THA_L2_SST`, `THA_L2_MOM` for THEMIS-A — substitute THB/THC (ARTEMIS) and THD/THE; verify with a cdaweb dataset search).
- L2 CDFs: FGM (fgs ~3-s spin-fit, fgl/fgh higher cadence), ESA moments (density, velocity, temperature), onboard moments (MOM).
- ASI data: `pyspedas.themis` ASI loaders / themis.ssl.berkeley.edu — keograms and full-sky frames.
- ARTEMIS solar wind: same instrument products for probes B and C after mid-2011 (in lunar orbit; solar wind when outside Earth's tail and the Moon's wake).

## Analysis recipes
- **Substorm timing chain**: pick a night with probes aligned down-tail; plot FGM Bx/Bz at each probe (dipolarization = sharp Bz increase), ESA ion flow (fast earthward flows / BBFs, v_x bursts of 400+ km/s), and the ASI keogram for auroral onset; order the timings to test inside-out vs outside-in onset.
- **ARTEMIS as upstream monitor**: load THB/THC ESA+FGM when the Moon is on the dayside; compare with OMNI to measure solar wind coherence over ~60 Re — or use it as the upstream input when L1 monitors have gaps (mind the different convection delay).
- **Dayside conjunctions**: seasonal dayside apogee gives magnetopause crossings — same recipe as MMS but at lower cadence.

## Gotchas and judgment calls
- **Probe naming trap**: THEMIS-B = ARTEMIS P1, THEMIS-C = ARTEMIS P2 — after ~2010/2011 these are at the Moon, not in the near-Earth tail. Tail studies post-2011 use A/D/E only.
- ESA moments contaminated in the solar wind: the ion beam is narrow and cold; solar wind density/velocity from ESA has known biases — use the calibrated "reduced" mode products and cross-check with OMNI.
- Orbit season matters: apogees precess through local time annually; tail alignment happens in northern winter — verify the orbit geometry (SSCWeb) before assuming region.
- ASI data: weather, moonlight, and station dropouts; keogram gaps are common — check station status maps.
- Spin-period (~3 s) artifacts appear in EFI/ESA products; use spin-fit products for DC quantities.
- Shadow seasons cause data gaps and attitude drifts near eclipses.

## Validation anchors
- **2008-02-26 substorm onset (Angelopoulos et al. 2008, Science)**: the mission's marquee result — tail reconnection at ~-20 Re preceding auroral onset by ~1.5 min; reproduce the multi-probe timing figure.
- **ARTEMIS vs OMNI**: any quiet interval with the Moon upstream — correlate THB FGM with OMNI B (shifted) to validate your ARTEMIS solar wind handling.
