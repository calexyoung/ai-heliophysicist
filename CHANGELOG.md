# Changelog

## Unreleased

- **README docs index is generated**: `scripts/gen_docs.py` now also rewrites
  the block between the `gen_docs:docs-index` markers in `README.md`, linking
  every file in `docs/` with a one-line description (curated in `DOC_BLURB`,
  otherwise derived from the document's first prose line). `--check` covers
  it, so adding a doc without linking it fails CI the way a stale
  `docs/TOOLS.md` does. Picked up two previously unlinked documents
  (`helio_agent_review.md`, `helio_agent_merge_analysis.md`).

## v0.3.0 — 2026-09-03

- **Deterministic trust hardening**: generated paths are contained after
  symlink resolution; audits retain canonical results and input hashes;
  replay compares status/results/inputs/artifact sets and reports
  `match`/`mismatch`/`unverifiable`; claim verification requires a real
  successful audit containing the computed value; BibTeX and hosted export
  POSTs use the replay-safe cache without persisting bodies or secrets;
  monitor cycles expose `ok`/`degraded`/`error` health and atomically persist
  state without turning an unavailable IPS feed into a false miss.
- **Paper reproduction manifests**: three core tools create, validate, and
  render schema-version-1, audit-linked claim records. Documentation now
  distinguishes the 29 tools directly exercised by 28 live checks from
  supporting tools covered through offline tests and validated composition.

- **`magnetogram_metrics`** (measure): fifth port from helio-agent
  (`analysis.magnetogram` v1.0.0). Unsigned/signed flux, max |B| and a
  strong polarity-inversion-line proxy (length + threaded flux) for a
  heliographic box on an HMI LOS magnetogram, plus disk unsigned flux;
  annotated plot. `fetch_vso` gained `physobs` so an HMI query can ask for
  the magnetogram instead of the continuum. Validation anchor: AR 12673 on
  2017-09-06 (2.8e22 Mx, 2255 G, 586 Mm strong PIL vs none in a quiet box).
  Six offline tests on synthetic bipoles. Skill note in `skills/missions/sdo.md`.

- **`hindcast_forecasts`** (measure): fourth port from helio-agent
  (`campaign.hindcast` v1.2.0), rewired to THIS repo's monitor rule. Replays
  the DONKI cone import, Earth-cone test, highest-speed-fit selection and
  `cme_arrival` drag window over a historical range, scores every window
  against DONKI Earth IPS shocks (hits / false alarms / timing MAE, split
  by the empirical alert-confidence tier), and storm recall against DONKI
  GST. Markdown table + three-panel figure. Validation anchor: May 2024 —
  the Gannon G5 storm covered by a high-confidence window, the 05-08T22:24
  halo (1257 km/s) hit within 5 h, high tier 7/7, hit MAE 12.5 h. Ten
  offline tests on a planted DONKI record. Skill note in
  `skills/methods/cme_analysis.md`. The severity prior was not ported.

- **`radio_bursts`** (measure) + **`fetch_cdaweb_spectrogram`** (retrieve):
  third port from helio-agent (`analysis.radio_bursts` v1.0.0). The fetcher
  keeps the channel axis of 2-D CDAWeb variables (columns `c<Hz>`; default
  WIND/WAVES `WI_K0_WAV` / `E_Average`, 76 channels, 3-min). The detector
  finds simultaneous multi-channel enhancements, merges them across gaps,
  inverts the log-frequency centroid drift through the Leblanc et al. 1998
  density model for a radial speed, and classifies type III (electron beam)
  vs type II candidate (shock) vs unclassified; labeled dynamic spectrum.
  Validation anchor: 2017-09-06 X9.3 (burst from 11:58, 52 dB peak at
  12:10, 6.7 MHz to 30 kHz, 2160 km/s type II candidate). Eleven offline
  tests. New skill `skills/methods/radio_burst_analysis.md` (K0 cadence
  merges the type III group into the type II; 2017-09-10 is a WAVES gap).

- **`characterize_sep`** (measure): second port from helio-agent
  (`analysis.characterize_sep` v1.2.0). NOAA S-scale radiation-storm
  detection on >10 MeV integral proton flux (events merged across
  `gap_hours`, first event is the primary), per-channel peak and fluence,
  >30/>10 MeV hardness ratio, and with flare context the onset physics:
  delay vs Parker-spiral free-streaming expectation, >30 MeV velocity
  dispersion, connection angle to the Parker footpoint. Log-flux figure.
  Validation anchor: 2017-09-10 X8.2 / S3 event on hourly OMNI (peak 1208
  pfu at 11:30 vs GOES 1490 at 11:45; onset within an hour; >30 MeV led by
  60 min). Twelve offline tests. New skill `skills/methods/sep_analysis.md`
  (OMNI proton fluxes end 2020-03; the 40 deg connection gate is strict at
  measured wind speeds).

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
