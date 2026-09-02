# AI Heliophysicist — Architecture

Design transposed from the HEASARC **AI Astrophysicist** (Brian Powell,
NASA/GSFC) to heliophysics, with the data resources of NASA's **Heliophysics
Data and Reference Library** (HDRL: SDAC + SPDF + DISH — Thomas et al., 2026)
as the archive backbone and the **PyHC** ecosystem (heliopython.org) as the
trusted software base.

## The transferable pattern

> "Nothing in this stack is astrophysics-specific. Swap the software and the
> skills; keep the pattern." — AI Astrophysicist, slide 5

| Layer | AI Astrophysicist | AI Heliophysicist |
|---|---|---|
| Scientist | directs the question, owns the result | same |
| LLM | rented judgment: plans, selects, interprets | same (Claude Code session under `CLAUDE.md`) |
| Tool layer | 66 tools wrapping HEASoft, XSPEC, CIAO, SAS, Fermitools | 60 tools wrapping sunpy, pyspedas, plasmapy, geopack, cdasws, sscws, hapiclient, cdflib + HDRL/NOAA REST services |
| Environment | conda env, data trees, outputs, logs | `uv`-managed env; `workspace/{data,outputs,logs}` |
| Knowledge | 317 skill documents | 43 skill documents (missions / methods / datasources / tools), growing |
| Assurance | fabrication = hard failure, audit trail, validation vs published results | same: `CLAUDE.md` contract, `audit.jsonl`, `validation/run_validation.py` |

Core principle preserved: **minimize nondeterminism, maximize validation**.
The LLM writes no pipelines and computes no science numbers; tools are
deterministic (same inputs → same outputs) and each is anchored to a
published result before the agent may trust it.

## Domain translation

| Astrophysics capability | Heliophysics equivalent here |
|---|---|
| Query HEASARC, resolve targets, fetch obsids | CDAWeb/HelioData/VSO search, SSCWeb spacecraft, HEK/DONKI event catalogs |
| Mission pipelines (extract_spectrum, run_maxi_pipeline) | fetch_cdaweb_data / fetch_goes_xrs / fetch_vso / fetch_hapi / fetch_helioviewer_image + reduce family (fill-value handling, resampling, merging, gap-aware interpolation) |
| XSPEC spectral fitting, joint fits | measure family: flare detection & GOES classification, storm metrics (Dst), Lomb-Scargle, lagged cross-correlation, superposed epoch, polynomial fits (CME height-time), ballistic propagation |
| Light curves & variability across missions | multi-mission time series via CDAWeb/HAPI on a common workspace format (CSV, UTC index) |
| NASA ADS, arXiv, BibTeX | identical (search_ads, get_bibtex, search_arxiv, fetch_arxiv_pdf) |
| Publication figures, PDF reports | plot_timeseries, plot_stack (space-physics standard), plot_solar_map, plot_orbits, write_pdf_report |

Heliophysics additions with no astrophysics counterpart: spacecraft ephemeris
and conjunction geometry (SSCWeb), operational real-time space weather (NOAA
SWPC), the science-vs-operational data distinction (beacon/LL02/RTSW), and
geomagnetic index analysis.

## Data flow

```
question (scientist)
   │
   ▼  read skills (method + mission + datasource)
plan (LLM)
   │
   ▼  discover ──► retrieve ──► reduce ──► measure ──► report
   │    HDRL/NOAA     workspace/data/*.csv   science     workspace/outputs/
   │    catalogs      (UTC-indexed, NaN      numbers      figures + PDF
   │                   for fill values)
   └── every call → workspace/logs/audit.jsonl (args, status, artifacts, id)
```

The workspace CSV (UTC time index, NaN fill, units in tool result) is the
common interchange format: any retrieve output feeds any reduce/measure/report
tool, which is what lets one agent chain 60+ mission archives through a small
tool set.

## Validation

`validation/run_validation.py` — run on every dependency upgrade or tool change:

- **halloween2003** — OMNI2 Dst minimum −383 nT at 2003-10-30 ~22:30 UT
  (Kyoto WDC; Gopalswamy et al. 2005).
- **flare20170906** — X-flare peaks 09:10 and 12:02 UT from GOES XRS, largest
  in X8–X12 band (published X9.3 operational scale), plus DONKI cross-check.
- **rotation2017** — Lomb-Scargle peak near the 27.28 d synodic solar
  rotation in OMNI solar wind speed.
- **ephemeris** — ACE mean GSE-X ≈ 1.5×10⁶ km (L1).

## Growth path

- More retrieve targets: Solar Orbiter LL02 and STEREO beacon (URLs in
  `skills/datasources/solar_orbiter_stereo_lowlatency.md`), JSOC bulk AIA/HMI,
  Madrigal (ground-based), viresclient (Swarm).
- pyspedas-backed loaders for MMS/THEMIS burst products (optional-deps group
  `heavy` is already declared).
- A critic/reviewer role and MCP exposure of the tool registry (the PPTX's
  MCP direction: CDAWeb/SSCWeb already ship MCP-era clients) so any MCP-aware
  client can drive the same audited tools.
