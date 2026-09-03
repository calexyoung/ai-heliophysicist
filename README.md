# The AI Heliophysicist

[![validation](https://github.com/calexyoung/ai-heliophysicist/actions/workflows/validate.yml/badge.svg)](https://github.com/calexyoung/ai-heliophysicist/actions/workflows/validate.yml)

An AI-supported heliophysics research and data-analysis system, started as a heliophysics agent harness, a personal analysis system, then branched off and built on the
pattern of NASA HEASARC's **AI Astrophysicist**: an LLM supplies judgment
(planning, tool selection, interpretation) while a layer of deterministic,
validated Python tools does every computation, over NASA HDRL's archives
(CDAWeb, OMNI, SSCWeb, VSO, Helioviewer, HEK, DONKI, HelioData, NOAA SWPC,
Kyoto WDC, GFZ Potsdam) and the PyHC software ecosystem (sunpy, pySPEDAS,
PlasmaPy, geopack, aiapy, hapiclient, cdflib).

**The LLM writes no pipelines and computes no science numbers itself.**
Every result is audit-logged and traceable to the exact tool call that
produced it; every tool is anchored to a published result before use —
21 live validation checks run on every push.

## Quick start

```bash
uv sync                                     # one-time: build the environment
uv run helio-agent list                     # 61 tools in six families
uv run helio-agent run fetch_omni '{"start":"2024-05-10T00:00:00Z","end":"2024-05-14T00:00:00Z"}'
uv run python validation/run_validation.py  # prove the stack against known results
uv run helio-agent report sun-news          # today's space-weather report (PDF)
uv run helio-agent monitor                  # standing watch: CME forecasts + scored ledger
uv run helio-agent replay <audit-id>        # re-execute a recorded call from cache
```

Then open this directory in Claude Code: `CLAUDE.md` makes the session the
AI Heliophysicist (contract: refuse with a reason, no fabrication, read
skills before acting, cross-check, everything on disk).

**→ Walkthroughs: [docs/USAGE.md](docs/USAGE.md) · every tool: [docs/TOOLS.md](docs/TOOLS.md) · every skill: [docs/SKILLS.md](docs/SKILLS.md) · internals: [docs/MODULES.md](docs/MODULES.md)**

## What it does

- **Archive to answer**: discover → retrieve → reduce → measure → report
  across 60+ mission archives, with a common workspace-CSV interchange format.
- **Physics models with error budgets**: O'Brien–McPherron Dst nowcast,
  drag-based CME arrival ensembles, peaks-over-threshold extreme-value
  statistics — each backtested against real storms.
- **Standing operations**: a daily monitor that imports new CMEs, issues
  arrival forecasts, and scores them hit/miss in a persistent ledger; a
  one-flag daily report (`report sun-news --archive`) producing markdown,
  self-hosted HTML, and PDF editions.
- **Paper reproduction**: extract claims → recompute like-for-like →
  `verify_claim` (refuses unit-mismatched comparisons rather than reporting
  false mismatches). Worked example: the 2012-07-23 extreme CME
  ([users/cayoung/analyses/](users/cayoung/analyses/2012-07-23-extreme-cme/analysis.md)).
- **Publishing**: analysis notes and reports as formatted pages — hosted
  templates (unmarkdown) or fully local/offline HTML with SRI-pinned
  Mermaid/Chart.js/KaTeX (`export_html`).
- **Reproducibility**: content-addressed HTTP cache with secret-stripped
  keys; audit entries carry git sha + artifact checksums; `replay` re-runs
  any recorded call from cache and verifies outputs.

## Layout

| Path | What |
|---|---|
| `CLAUDE.md` | The agent's operating contract (the judgment layer's rules) |
| `helio_agent/` | Tool layer: registry, audit, HTTP cache, CLI, monitor, reports, six tool families |
| `skills/` | 43 knowledge documents: missions, methods, datasources, software — read before acting |
| `validation/` | 21 checks anchored to published results (Halloween 2003, 2017 X9.3, 2012-07-23 CME, ...) |
| `tests/` | Offline CI guards: schema lock, docs-current, cache behavior, user-tool scoping |
| `workspace/` | Persistent environment: `data/`, `outputs/`, `cache/` (shared), `logs/audit.jsonl` |
| `users/` | Per-user profiles (`HELIO_AGENT_USER=<name>`): one-off tools/skills/analyses; core stays general — see [users/README.md](users/README.md) |
| `docs/USAGE.md` | **Detailed usage documentation** — setup, CLI, workflows, troubleshooting |
| `docs/TOOLS.md` | **Every tool**: signature + docstring, generated from the registry (drift fails CI) |
| `docs/SKILLS.md` | **Every skill document**, cataloged with its one-line summary (generated) |
| `docs/MODULES.md` | The `helio_agent` package module by module: registry, audit, cache, monitor, reports, tool modules |
| `docs/ARCHITECTURE.md` | Full design, mapping to the AI Astrophysicist model |
| `CHANGELOG.md` | Release history |

## Tool families

- **discover** — CDAWeb dataset/variable search, HelioData freetext search,
  SSCWeb spacecraft catalog, VSO search, HEK + DONKI event queries, NOAA SWPC
  real-time conditions + solar regions, pySPEDAS mission/loader listing
- **retrieve** — CDAWeb/OMNI/GOES-XRS/HAPI/pySPEDAS time series, VSO FITS,
  Helioviewer imagery, SSCWeb ephemerides, NOAA SWPC operational feeds,
  Kyoto Dst (by revision), GFZ Kp/Hp indices, solar-cycle progression
  → workspace CSVs (UTC index, NaN fills)
- **reduce** — series description, resampling, merging, gap-aware
  interpolation, derived columns, time shifting, solar map loading,
  coordinate transforms (GSE/GSM/SM/GEO/MAG...), AIA degradation correction
- **measure** — flare detection + GOES classification, storm metrics,
  Lomb-Scargle, cross-correlation, superposed epoch, field-line tracing
  (T89), Dst nowcast, CME arrival (DBM), extreme-value statistics,
  plasma parameters (PlasmaPy), claim verification
- **literature** — NASA ADS (token via `ADS_API_TOKEN`), arXiv search + PDF fetch, BibTeX
- **report** — publication-styled time-series/stack/solar-map/orbit plots
  (CVD-validated palette), seaborn statistical plots, PDF reports,
  self-hosted HTML export

## Provenance

Model: Started by C. Alex Young, then checked against *The AI Astrophysicist* (B. Powell, NASA/GSFC HEASARC) as a model. Separate from the heliophysics agent harness, helio-agent
Resources: *How HDRL can support Space Weather* (B. Thomas et al., NASA/GSFC
HDRL, 2026) and the [Python in Heliophysics Community](https://heliopython.org/projects/).
