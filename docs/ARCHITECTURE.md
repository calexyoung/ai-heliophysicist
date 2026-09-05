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
| Tool layer | 67 tools wrapping HEASoft, XSPEC, CIAO, SAS, Fermitools | 80 tools wrapping sunpy, solarmach, pyspedas, plasmapy, geopack, cdasws, sscws, hapiclient, cdflib + HDRL/NOAA REST services |
| Environment | conda env, data trees, outputs, logs | `uv`-managed env; `workspace/{data,outputs,logs}` |
| Knowledge | 317 skill documents | 45 skill documents (missions / methods / datasources / tools), growing |
| Assurance | fabrication = hard failure, audit trail, validation vs published results | same: `CLAUDE.md` contract, `audit.jsonl`, `validation/run_validation.py` |

Core principle preserved: **minimize nondeterminism, maximize validation**.
The LLM writes no pipelines and computes no science numbers; tools are
deterministic (same inputs → same outputs). Scientific tools need an
appropriate published, analytic, or cross-implementation anchor before the
agent may trust their scientific conclusions; supporting tools are covered by
offline behavioral tests and validated compositions.

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
   └── every call → workspace/logs/audit.jsonl
       (args, input hashes, full result, status, artifacts + hashes, id)
```

The workspace CSV (UTC time index, NaN fill, units in tool result) is the
common interchange format: any retrieve output feeds any reduce/measure/report
tool, which is what lets one agent chain 60+ mission archives through a small
tool set.

## Validation

`validation/run_validation.py` — 28 checks in 21 cases, run on every push
(CI), dependency upgrade, or tool change. It directly references 29 of the 70
core tools; the remaining supporting tools are covered by offline tests,
schema locks, and use inside validated workflows. Anchor types:

- **Published-event anchors**: Halloween 2003 Dst −383 nT exact; 2017-09-06
  X-flare timing exact + DONKI cross-check; 2012-07-12 CME arrival within
  1.9 h of the observed shock; 2015 St. Patrick storm Dst-model skill;
  March 1989 −589 nT as the 61-year extreme-value record; solar-cycle 24/25
  smoothed maxima; Kyoto final Dst and GFZ Kp for known storms.
- **Cross-implementation anchors**: pySPEDAS vs CDAWeb pipelines (0.01%);
  cotrans vs geopack rotations (10⁻⁴ nT) — this check caught a real
  pandas-3 epoch bug that single-implementation tests shared.
- **Analytic anchors**: PlasmaPy Alfvén speed / beta against closed-form
  values; T89 footpoints in the auroral zone.
- **Behavioral anchors**: verify_claim's match/mismatch/refusal logic;
  export_html rendering (and its keyless refusal in CI); the 2012-07-23
  reproduction case guards the documented L2 plasma gap so a future
  reprocessing flags the stale caveat instead of hiding it.

Engineering guards live separately in `tests/` (offline, every push):
schema lock (tool-interface drift fails CI unless deliberately
regenerated), docs-current (README counts must match the registry), HTTP
cache behavior (secrets never on disk), user-tool scoping.

## Beyond the original pattern

Adopted from the author's helio-agent harness (see
`docs/helio_agent_review.md`, now largely implemented): content-addressed
GET/POST cache, exact result/input/artifact replay, coverage-aware refusals,
monitor health plus a scored forecast ledger, saved rerunnable reports,
versioned paper-reproduction manifests, physics models with population
backtests, extreme-value convention sweeps, and the
refuse-rather-than-false-mismatch claim verifier.

## Growth path

- More retrieve targets: Solar Orbiter LL02 and STEREO beacon (URLs in
  `skills/datasources/solar_orbiter_stereo_lowlatency.md`), JSOC bulk
  AIA/HMI, Madrigal (ground-based), viresclient (Swarm).
- Hindcast machinery over the accumulating forecast ledger
  (precision/recall, reliability diagrams) once it holds enough verdicts;
  refinement of the monitor's crude |longitude| ≤ 60° cone test.
- Higher-fidelity field models (T96/TS04) behind trace_field_line for
  storm-time work; spectrogram-capable pySPEDAS retrieval.
- A critic/reviewer role and MCP exposure of the tool registry (the PPTX's
  MCP direction: CDAWeb/SSCWeb already ship MCP-era clients) so any
  MCP-aware client can drive the same audited tools.
