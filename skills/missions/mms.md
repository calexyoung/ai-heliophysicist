# MMS (Magnetospheric Multiscale)
> One-line: four identical NASA spacecraft flying in a tight tetrahedron through Earth's magnetopause and magnetotail, resolving magnetic reconnection at electron scales.

## Overview
- Launched 2015-03-12; four spacecraft (MMS1-4) in highly elliptical orbits — Phase 1 apogee ~12 Re (dayside magnetopause), later raised to ~25 Re for magnetotail reconnection; still operating. NASA/GSFC; SDC at LASP.
- The point is multi-spacecraft, ultra-high-cadence measurements in small regions — NOT a solar wind monitor. Use MMS for reconnection, boundary layers, waves, and (opportunistically) pristine solar wind when the orbit exits the bow shock.

## Instruments that matter
- **FGM**: fluxgate magnetometer (8-16 S/s survey, 128 S/s burst).
- **FPI**: fast plasma investigation — DIS (ions) and DES (electrons); burst cadence 150 ms (ions) / 30 ms (electrons) — the revolutionary capability.
- **EDP**: electric field double probes; **SCM**: search coil.
- **HPCA**: hot plasma composition (H+, He+, He++, O+).
- **EPD (FEEPS/EIS)**: energetic particles.

## Key datasets and where to get them
- **MMS Science Data Center** (lasp.colorado.edu/mms/sdc) is authoritative; `pyspedas.mms` loaders are the standard access path and handle the file naming.
- CDAWeb mirrors L2: IDs follow `MMS1_FGM_SRVY_L2`, `MMS1_FPI_FAST_L2_DIS-MOMS`, `MMS1_FPI_BRST_L2_DES-MOMS`, etc. (spacecraft number 1-4; rate srvy/fast/brst) — verify with a cdaweb dataset search; the pyspedas route is less error-prone.
- **Data rates matter**: survey (continuous, low cadence), fast (in the region of interest), burst (tiny selected windows at full cadence, chosen by scientists-in-the-loop via the SITL system). Burst coverage is sparse and event-selected — check the burst segment list before assuming coverage.
- Curated event lists: the SITL reports and published reconnection-event lists are the practical entry points.

## Analysis recipes
- **Magnetopause crossing overview**: load FGM srvy + FPI fast moments for one spacecraft around the crossing; identify the boundary from Bz rotation, density jump (magnetosheath ~10-30 /cc vs magnetosphere ~0.1-1 /cc), and ion velocity shear.
- **Reconnection diffusion-region hunt**: within a burst window, look for ion/electron jets (v reversals), Hall B/E fields, crescent-shaped electron distributions (FPI DES); compare all four spacecraft — curlometer (four-point) gives current density.
- **Solar wind/bow shock opportunistic use**: when apogee is sunward of the bow shock, FPI+FGM give high-cadence solar wind/foreshock data — but FPI is optimized for hot magnetospheric plasma; cold solar wind beams are marginally resolved (narrow beam vs angular resolution) — prefer OMNI for solar wind context.

## Gotchas and judgment calls
- **Burst data are not continuous** — analysis plans must consult burst segment availability; absence of 30-ms data is the norm, not a gap.
- FPI moments in the solar wind and in cold dense plasmas are unreliable (cold beams, photoelectron contamination for DES at low energies; spacecraft potential corrections matter — use the EDP spacecraft potential).
- Data volume: FPI burst distributions are enormous; download moments first, distributions only for identified intervals.
- Tetrahedron quality varies along the orbit (elongated formations near perigee); four-spacecraft techniques (curlometer, timing) are only valid with good tetrahedron quality factors.
- Orbit phase determines region: dayside season vs tail season alternates annually — check where MMS actually was before searching for a phenomenon.
- Coordinate systems: GSE vs GSM vs boundary-normal (LMN) — reconnection work is done in LMN; deriving LMN (MVA or model normal) is itself a judgment call.

## Validation anchors
- **2015-10-16 13:07 UT electron diffusion region event (Burch et al. 2016)**: MMS2/3/4 magnetopause EDR with the famous electron crescents — reproduce the burst-mode overview panels.
- **2017-07-11 22:34 UT magnetotail EDR (Torbert et al. 2018)**: the canonical tail reconnection event — a good test of burst retrieval and multi-spacecraft alignment.
