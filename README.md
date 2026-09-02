# The AI Heliophysicist

[![validation](https://github.com/calexyoung/ai-heliophysicist/actions/workflows/validate.yml/badge.svg)](https://github.com/calexyoung/ai-heliophysicist/actions/workflows/validate.yml)

An AI-supported heliophysics research and data-analysis system, started as a heliophysics agent harness, a personal analysis system, then branched off and built on the
pattern of NASA HEASARC's **AI Astrophysicist**: an LLM supplies judgment
(planning, tool selection, interpretation) while a layer of deterministic,
validated Python tools does every computation, over NASA HDRL's archives
(CDAWeb, OMNI, SSCWeb, VSO, Helioviewer, HEK, DONKI, HelioData, NOAA SWPC)
and the PyHC software ecosystem.

**The LLM writes no pipelines and computes no science numbers itself.**
Every result is audit-logged and traceable to the exact tool call that
produced it; every tool is anchored to a published result before use.

## Quick start

```bash
uv sync                                   # one-time: build the environment
uv run helio-agent list                   # 53 tools in six families
uv run helio-agent run fetch_omni '{"start":"2024-05-10T00:00:00Z","end":"2024-05-14T00:00:00Z"}'
uv run python validation/run_validation.py  # prove the stack against known results
```

Then open this directory in Claude Code: `CLAUDE.md` makes the session the
AI Heliophysicist (contract: no fabrication, read skills before acting,
cross-check, everything on disk).

## Layout

| Path | What |
|---|---|
| `CLAUDE.md` | The agent's operating contract (the judgment layer's rules) |
| `helio_agent/` | Tool layer: registry, audit trail, CLI, six tool families |
| `skills/` | 48 knowledge documents: missions, methods, datasources, software |
| `validation/` | Canonical-result test suite (Halloween 2003 storm, 2017 X9.3 flare, ...) |
| `workspace/` | Persistent environment: `data/`, `outputs/`, `logs/audit.jsonl` |
| `docs/ARCHITECTURE.md` | Full design, mapping to the AI Astrophysicist model |

## Tool families

- **discover** — CDAWeb dataset/variable search, HelioData freetext search,
  SSCWeb spacecraft catalog, VSO search, HEK + DONKI event queries, NOAA SWPC
  real-time conditions
- **retrieve** — CDAWeb/OMNI/GOES-XRS/HAPI time series, VSO FITS files,
  Helioviewer imagery, SSCWeb ephemerides → workspace CSVs (UTC index, NaN fills)
- **reduce** — series description, resampling, merging, gap-aware
  interpolation, derived columns, time shifting, solar map loading
- **measure** — flare detection + GOES classification, geomagnetic storm
  metrics, Lomb-Scargle periodograms, lagged cross-correlation, superposed
  epoch analysis, ballistic propagation delay, polynomial fits
- **literature** — NASA ADS (token via `ADS_API_TOKEN`), arXiv search + PDF fetch, BibTeX
- **report** — time-series and stacked panels, solar maps, orbit plots, PDF reports

## Provenance

Model: Started by C. Alex Young, then checked against *The AI Astrophysicist* (B. Powell, NASA/GSFC HEASARC) as a model. Separate from the heliophysics agent harness, helio-agent
Resources: *How HDRL can support Space Weather* (B. Thomas et al., NASA/GSFC
HDRL, 2026) and the [Python in Heliophysics Community](https://heliopython.org/projects/).
