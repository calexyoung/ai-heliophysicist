# Skills catalog

*Generated from `skills/` by `scripts/gen_docs.py` — do not edit by hand.*

45 knowledge documents the agent must read before acting
(see `skills/README.md` for the composition rule: method + mission +
datasource). Each entry shows the document's own one-line summary.

## Mission guides (`skills/missions/`, 14)

| Document | Summary |
|---|---|
| [ACE (Advanced Composition Explorer)](../skills/missions/ace.md) | NASA solar wind and energetic-particle monitor at L1 since 1997 — the long-baseline workhorse for upstream field, plasma, and composition. |
| [DSCOVR (Deep Space Climate Observatory)](../skills/missions/dscovr.md) | NOAA's operational real-time solar wind monitor at L1 (launched 2015), the source of the live upstream data behind SWPC forecasts. |
| [GOES (Geostationary Operational Environmental Satellites)](../skills/missions/goes.md) | NOAA's geostationary fleet whose XRS soft X-ray fluxes define flare classes (C/M/X), plus energetic particle, magnetometer, and (GOES-R era) EUV imaging. |
| [Hinode and IRIS](../skills/missions/hinode_iris.md) | two Sun-pointing spectroscopy/high-resolution imaging observatories in sun-synchronous LEO — Hinode (JAXA/NASA/ESA, 2006-) for photospheric magnetism, X-ray corona, and EUV spectroscopy; IRIS (NASA SMEX, 2013-) for the chromosphere-transition-region interface. |
| [IMAP (Interstellar Mapping and Acceleration Probe)](../skills/missions/imap.md) | NASA's newest L1 mission (launched 2025-09-24) mapping the heliosphere's boundary via energetic neutral atoms while serving as a next-generation real-time solar wind monitor. |
| [MMS (Magnetospheric Multiscale)](../skills/missions/mms.md) | four identical NASA spacecraft flying in a tight tetrahedron through Earth's magnetopause and magnetotail, resolving magnetic reconnection at electron scales. |
| [OMNI](../skills/missions/omni.md) | not a spacecraft — NASA/SPDF's multi-source compilation of near-Earth solar wind field/plasma data, time-shifted to the bow shock nose, plus geomagnetic and solar indices. |
| [Parker Solar Probe (PSP)](../skills/missions/parker_solar_probe.md) | NASA probe diving repeatedly into the solar corona (perihelia now inside 10 solar radii), measuring nascent solar wind fields, particles, and white-light structure in situ. |
| [SDO (Solar Dynamics Observatory)](../skills/missions/sdo.md) | NASA's flagship solar imager in geosynchronous orbit, staring at the full solar disk continuously in EUV/UV/visible plus magnetograms. |
| [SOHO (Solar and Heliospheric Observatory)](../skills/missions/soho.md) | ESA/NASA workhorse at L1 since 1996; today primarily valued for LASCO coronagraph CME imaging. |
| [Solar Orbiter](../skills/missions/solar_orbiter.md) | ESA/NASA encounter mission in an elliptical heliocentric orbit (perihelia ~0.28-0.5 AU, inclination rising over time), combining remote sensing and in-situ instruments off the Sun-Earth line. |
| [STEREO (Solar TErrestrial RElations Observatory)](../skills/missions/stereo.md) | twin NASA spacecraft in Earth-leading (Ahead) and Earth-trailing (Behind) heliocentric orbits, giving off-Sun-Earth-line imaging of CMEs and in-situ solar wind at ~1 AU. |
| [THEMIS / ARTEMIS](../skills/missions/themis.md) | five NASA probes launched to time substorm onset in Earth's magnetotail; three (THEMIS A/D/E) still orbit Earth, two (ARTEMIS P1/P2, formerly B/C) moved to lunar orbit in 2011. |
| [Wind](../skills/missions/wind.md) | NASA solar wind spacecraft, at L1 since 2004 (complex orbits before that), with arguably the best-calibrated long-baseline plasma and field measurements at 1 AU. |

## Method recipes (`skills/methods/`, 13)

| Document | Summary |
|---|---|
| [CME Analysis](../skills/methods/cme_analysis.md) | Measure CME kinematics from coronagraph height-time data and estimate Earth arrival, with catalog cross-checks. |
| [Heliophysics Coordinate Systems](../skills/methods/coordinate_systems.md) | Know which frame a quantity is in, which frame the physics wants, and where transforms bite. |
| [Cross-Spacecraft Analysis](../skills/methods/cross_spacecraft.md) | Relate observations of the same plasma or structure at two spacecraft: lag correlation, ballistic mapping, and their limits. |
| [Error Estimation](../skills/methods/error_estimation.md) | Decide what the real uncertainty is, propagate it honestly, and admit when error bars are fiction. |
| [Solar Flare Analysis](../skills/methods/flare_analysis.md) | Classify and time solar flares from GOES XRS soft X-ray flux, then cross-check against catalogs and imagery. |
| [Geomagnetic Storm Analysis](../skills/methods/geomagnetic_storm_analysis.md) | Characterize storms with Dst/SYM-H and Kp, classify intensity, and attribute the interplanetary driver. |
| [Paper reproduction](../skills/methods/paper_reproduction.md) | Reproduce a paper's numbers with the tool layer, refusing dishonest comparisons. |
| [Solar Radio Burst Analysis (type II / type III)](../skills/methods/radio_burst_analysis.md) | Detect and classify type III electron-beam and type II shock bursts in WIND/WAVES dynamic spectra, convert their frequency drift to a source speed, and tie them to the flare and CME. |
| [Solar Energetic Particle (SEP) Event Analysis](../skills/methods/sep_analysis.md) | Detect and grade radiation storms (NOAA S scale) in >10 MeV proton flux, measure fluence and hardness, and test the onset against flare timing and Parker-spiral connection. |
| [Solar Wind Analysis](../skills/methods/solar_wind_analysis.md) | Read L1 plasma/field data, distinguish slow/fast wind, and recognize ICME, magnetic cloud, and shock signatures. |
| [Superposed Epoch Analysis](../skills/methods/superposed_epoch.md) | Stack many events on a common time axis to extract the average behavior and its uncertainty. |
| [Timing and Periodicity Analysis](../skills/methods/timing_periodicity.md) | Find and validate periodic signals in solar and solar-wind time series, including gappy data. |
| [Troubleshooting Data Retrieval and Processing](../skills/methods/troubleshooting.md) | Failure signatures in heliophysics data work, and whether to retry, fix, or re-plan. |

## Data source guides (`skills/datasources/`, 11)

| Document | Summary |
|---|---|
| [CDAWeb](../skills/datasources/cdaweb.md) | NASA's Coordinated Data Analysis Web — the workhorse archive for heliophysics in-situ time series. |
| [DONKI](../skills/datasources/donki.md) | NASA CCMC's Space Weather Database Of Notifications, Knowledge, Information — human-curated space weather event catalog with linkages. |
| [HAPI (Heliophysics Application Programmer's Interface)](../skills/datasources/hapi.md) | A standard REST interface for time-series data adopted by many heliophysics servers — one client, many archives. |
| [HEK (Heliophysics Event Knowledgebase)](../skills/datasources/hek.md) | Searchable catalog of solar events and features (flares, CMEs, active regions, coronal holes...) hosted at LMSAL. |
| [Helio Data Portal (helio.data.nasa.gov)](../skills/datasources/heliodata.md) | NASA's new unified heliophysics data discovery portal — search >7800 datasets across the division from one place. |
| [Helioviewer](../skills/datasources/helioviewer.md) | Fast browse imagery of the Sun (JPEG2000) via a simple API — for context and visualization, never photometry. |
| [NOAA SWPC Real-Time Data](../skills/datasources/noaa_swpc.md) | Operational, real-time space weather feeds from the NOAA Space Weather Prediction Center — freshest data, operational-grade caveats. |
| [OMNI / OMNIWeb](../skills/datasources/omniweb.md) | Multi-source solar wind and geomagnetic-index dataset, time-shifted to Earth's bow-shock nose — the default for solar wind context at Earth. |
| [Solar Orbiter Low-Latency and STEREO Beacon Data](../skills/datasources/solar_orbiter_stereo_lowlatency.md) | Quick-look data from off-Sun-Earth-line spacecraft — hours-fresh, NOT science quality. |
| [SSCWeb](../skills/datasources/sscweb.md) | Satellite Situation Center — ephemeris (positions) for ~200 heliophysics-relevant spacecraft, plus conjunction finding. |
| [VSO (Virtual Solar Observatory)](../skills/datasources/vso.md) | Federated search/download across solar data archives — the sunpy Fido route to SDO, SOHO, and ground-based solar data. |

## Software notes (`skills/tools/`, 7)

| Document | Summary |
|---|---|
| [Analysis notes: format and publishing](../skills/tools/analysis_notes.md) | The canonical structure for an analysis note and how to publish it as a formatted page (unmarkdown), with seven vetted templates. |
| [CDF Files](../skills/tools/cdf_files.md) | Reading NASA Common Data Format files with cdflib, and the ISTP conventions that make them self-describing. |
| [hapiclient](../skills/tools/hapiclient.md) | The reference Python client for HAPI time-series servers. |
| [Heliophysics Plotting Conventions](../skills/tools/plotting_conventions.md) | Make plots the field recognizes: UTC time axes, labeled datasets and units, event markers, stacked panels, standard colormaps. |
| [PyHC ecosystem map](../skills/tools/pyhc_ecosystem.md) | Which PyHC package answers which need; core-package docs federate at https://heliopython.org/pyhc-docs/. |
| [pySPEDAS and PyTplot](../skills/tools/pyspedas_pytplot.md) | Mission-aware load routines plus the tplot variable/plot ecosystem — the IDL SPEDAS workflow in Python. |
| [sunpy](../skills/tools/sunpy.md) | The core Python library for solar data: unified search/fetch (Fido), images (Map), and time series (TimeSeries). |

