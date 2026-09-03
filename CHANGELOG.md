# Changelog

## Unreleased

- **`detect_icme`** (measure): first capability port from helio-agent
  (`analysis.detect_icme` v1.3.0). Low-proton-temperature ICME intervals
  (Lopez 1987 Texp(V)), shock gate against cold slow wind, clock-angle
  flux-rope proxy, sheath vs ejecta southward-field attribution, near-miss
  diagnostics on refusal, four-panel diagnostic figure. Validation anchor:
  2015 St. Patrick's Day storm vs the Richardson & Cane list (shock within
  4 min, boundaries within 45 min on 1-min OMNI). Nine offline tests.
  Skill note in `skills/methods/solar_wind_analysis.md` (hourly OMNI
  temperature is too patchy for the default gate — use 1-min).

## v0.2.1 — 2026-09-02

Docs and fixes patch.

- **docs/USAGE.md**: full usage guide — setup, CLI reference, tool-driving
  conventions, five worked workflows, profiles, audit/cache/replay, adding
  a tool, scheduling, troubleshooting table. README refreshed to match.
- Fix: SWPC alerts feed is newest-first — `get_noaa_realtime` now sorts
  list-of-dict feeds by timestamp explicitly (the fix immediately surfaced
  a live Type II radio-emission alert).
- Fix: RTSW feeds repeat timestamps — deduped in `fetch_swpc_timeseries`.
- Skills: curated worked-example maps for sunpy, pySPEDAS, MMS, THEMIS
  (validated in-repo code first, then upstream galleries/notebooks).
- `export_html`: `embed_assets` (SRI-hash-verified inlined libraries,
  fully offline pages) and `engine="local"` (on-machine markdown
  conversion + built-in stylesheet — no external API in the path).
- Ignore user workspaces wholesale (per-user runtime state).

## v0.2.0 — 2026-09-02

Publishing pipeline & user profiles. 21/21 validation.

- **User profiles** (`users/<name>/`, `HELIO_AGENT_USER`): scoped one-off
  tools (auto-loaded, non-shadowing, lock-excluded), per-profile workspace
  and audit, promotion policy ("could the next paper use it?").
- **Analysis-notes format** (`skills/tools/analysis_notes.md`): canonical
  structure + seven vetted publishing templates with live samples
  (default: research).
- **`export_html`**: self-hosted templated pages with SRI-pinned
  Mermaid/Chart.js/KaTeX runtime.
- **`report sun-news --archive`**: four editions (markdown with live
  charts, self-hosted HTML, PDF, README) filed per-user in one flag.
- Worked paper reproduction: the 2012-07-23 extreme CME at STEREO-A
  (3 claims matched incl. peak B 109 nT at 0.08%; impact-speed claim
  honestly blocked by the documented L2 plasma gap) + permanent
  validation case.
- Operations: daily monitor LaunchAgent + wrapper; NOAA feed-format fixes.

## v0.1.0 — 2026-09-02

First release: the AI Astrophysicist pattern transposed to heliophysics.

- 60 core tools in six families over HDRL archives (CDAWeb, OMNI, SSCWeb,
  VSO, Helioviewer, HEK, DONKI, HelioData, NOAA SWPC incl. IMAP RTSW and
  Solar Cycle Progression), Kyoto Dst, GFZ Kp/Hp, and the PyHC stack
  (sunpy, pySPEDAS, PlasmaPy, geopack, aiapy, hapiclient, cdflib).
- Science: flare detection with operational-scaling handling, storm
  metrics, Lomb–Scargle, superposed epoch, cross-correlation, coordinate
  transforms (cross-validated to 10⁻⁴ nT), T89 field-line tracing,
  O'Brien–McPherron Dst nowcast, drag-based CME arrival, extreme-value
  statistics, AIA degradation correction, unit-aware claim verification.
- Assurance: 20 live validation checks anchored to published results;
  append-only audit manifests (git sha, cache keys, artifact checksums);
  content-addressed HTTP cache with secret-stripped keys; `replay`; CI
  with offline guards (schema lock, docs-current) + live suite;
  CLAUDE.md operating contract.
- 42 skill documents; publication figure styling (CVD-validated palette,
  journal geometry, editable vector output); standing monitor with scored
  forecast ledger; saved rerunnable daily report.
