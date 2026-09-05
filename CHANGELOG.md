# Changelog

## v0.6.0 — 2026-09-05

Six new tools, all of them forced by real analyses rather than designed in
advance: reproducing a summer-school notebook on the May 2024 Gannon storm,
then surveying October 2024 and carrying its superstorm from Sun to ground.
Every one of them exists because a route that should have worked did not.
Tools 77 to 83; validation 55 checks to 64; tests 216.

### Added

- **`fetch_aia_synoptic`** — SDO/AIA from the JSOC synoptic archive. The VSO
  AIA export provider (`sdo7.nascom.nasa.gov` drms_export.cgi) times out on
  every request; the synoptic archive is plain static HTTP and answers in
  seconds. Level 1.5, 1024x1024 at ~2.4 arcsec/pix, on a strict 2-minute
  grid. Right for morphology and context, wrong for native resolution.
- **`fetch_aia_level1`** — native 4096x4096 level-1 AIA from JSOC through
  `drms`, for when the science needs the real plate scale. Requires a
  JSOC-registered export email (`JSOC_EMAIL` in `.env`); without one it
  refuses by name rather than handing back a 16x smaller image under the
  same call. Level 1 is not 1.5: `CROTA2` is nonzero and `aiapy.calibrate.
  register` still has to run. The validation case pins that.
- **`fetch_dscovr_l2`** — DSCOVR Level 2 from NOAA NCEI, which CDAWeb cannot
  serve. `DSCOVR_H1_FC` plasma stops in June 2019 and `DSCOVR_H0_MAG`
  carries no GSM component at all, so Bz at L1 from DSCOVR was unobtainable
  through CDAWeb. The archive lives at
  `archive.data.noaa.gov/satellite-spaceweather`, an S3 bucket behind a JS
  explorer; the older ngdc and ncei paths are dead.
- **`track_cme_front`** — measures a CME leading edge frame by frame so
  `cme_height_time` has real input instead of hand-typed heights. Noise is
  referenced to the same radius at other position angles, the sector
  statistic is the 90th percentile, and sector choice scores monotonic
  outward motion. Each of those failed the obvious way first.
- **`plot_coronagraph_sequence`** — exposure-normalised running-difference
  panels. Refuses a sequence whose exposure metadata is missing, because
  differencing raw counts turns the shutter pattern into a fake disturbance.
- **`cme_height_time`** and **`plot_heliospheric_config`** — linear
  height-time fit that refuses fewer than three points or non-monotonic
  heights, and a solarmach constellation that returns the position table.

### Changed

- **`fetch_vso` errors when a search matches but downloads nothing.** It used
  to return `status: "ok"` with an empty file list on a provider timeout,
  which reads as "no such data exists".
- **`fetch_vso` gained `detector`** (LASCO C2/C3, SECCHI COR1/COR2/EUVI), so
  a coronagraph sequence does not interleave two fields of view.
- **`track_cme_front` refuses halos and saturations.** A full halo brightens
  every position angle, leaving no quiet reference; a CME faster than the
  field can follow pins every height at the outer bound. Both reach the end
  of the routine with three or more *monotonic* detections — equal values
  are non-decreasing — so both need their own check. Found on the
  2024-10-09 CME, which returned four identical heights at the C3 field edge
  and called it a track.
- **`merge_series` and `resample_series` normalise timezones**, converting
  tz-aware input to UTC before stripping rather than after.

### Fixed

- Region labels on `plot_solar_regions` were drawn ~14.5 degrees west of the
  regions: SWPC's `location` is valid at 2400 UT of `observed_date`, not
  0000. `get_solar_regions` now returns `coordinates_epoch` and the plot uses
  it. Fitted from 388 station reports (24.07 h, 14.50 deg/day, rms 0.27).

### Documented

- **`skills/missions/ace.md`** — ACE plasma Level 2 stops at 2024-07-09 on
  CDAWeb, both hourly and 64-second. Any recipe written against an earlier
  event silently fails on a later one; Wind SWE and DSCOVR L2 are the
  replacements.
- **`skills/missions/dscovr.md`** — the Faraday cup under-read the May 2024
  storm by ~200 km/s while reporting `overall_quality` 0 on every affected
  minute. The signal is `reduced_proton_quality_flag`, and it is
  event-dependent: 58% of the May window against 39% in October, where the
  speeds agreed with OMNI. Check it per event.
- **`skills/methods/cme_analysis.md`** — the two tracker artefacts, why the
  search window must open at the flare peak (C2 spans only 2.4-5.8 Rsun),
  and how to read the launch-time extrapolation against the acceleration
  sign.
- **`skills/missions/sdo.md`** — the two AIA routes and what each one costs.

### Analyses

- `users/cayoung/analyses/2024-05-gannon-notebook-repro/` — the notebook
  reproduced through audited tools, with the three places its own code
  raised an error or fabricated its input recorded and measured instead.
  Solar Orbiter was 167.6 degrees from Earth, not the ~45 its fallback
  printed.
- `users/cayoung/analyses/2024-10-storms/` — October 2024 surveyed and its
  superstorm carried Sun to ground, compared against 24 papers. Agrees with
  the literature on Dst to 2 nT; disagrees on a quoted SYM-H value that
  matches the Dst series, and on a G5 classification that Kp 8.67 does not
  support. Both superstorms of 2024 turn out to be sheath-driven.

## v0.5.0 — 2026-09-05

The forecast rule changed on evidence, the monitor got a plain-language
guide, and every tool in the registry now has a worked, audit-logged example
with real figures. Validation 49 checks to 50; tests 206.

### Changed

- **The Earth-directed cone is 45 degrees, down from 60.** The live ledger
  had reached 0 hits in 3 scored, every miss an eruption that never arrived —
  two of them launched 48–59° off the Sun–Earth line. A four-month hindcast
  (163 windows, 12 storms) shows 45° cuts false alarms 74 → 55 while covering
  exactly the same 9/12 storms. Tighter is *not* safe: 30°, or any
  launch-speed floor, takes June 2025 to zero recall by dropping the
  249 km/s CME at 41° that drove its only covered storm. Recall neutrality is
  now pinned by `hindcast.recall_neutral`, and `hindcast_forecasts` defaults
  its cone to the monitor's constant so the replay cannot drift from the
  deployed rule. Ledger note: forecasts issued before this change score
  against the old rule until they clear.
- **The monitor cycle log lives beside its state** in the active profile's
  workspace instead of a hardcoded shared path, and `monitor_cron.sh`
  resolves `HELIO_AGENT_USER` explicitly (no profile hardcoded), logging the
  resolved profile and workspace at the top of every cycle. Verified under
  `env -i` the way launchd invokes it.

### Added

- **`docs/EXAMPLES.md`** — one real, executed invocation for each of the 77
  tools (coverage asserted at build), all 46 skills mapped to the examples
  that exercise them, and the Python API of every supporting module. Built by
  `scripts/gen_examples.py`, which runs everything against live archives and
  embeds each call's audit id; 16 figures/artifacts committed under
  `docs/examples/`. Not a CI step.
- **`docs/MONITOR.md`** — the standing watch in plain language: what a cycle
  does, how to read the scorecard (a miss with an empty arrival means
  *nothing arrived*, which is a different failure from wrong timing), and the
  worked example behind the 45° threshold.

### Fixed

- `run_tool` could not invoke any tool with a `name` parameter (`save_json`);
  its first argument is now positional-only.
- `plot_solar_map` crashed on HMI magnetograms whose sunpy plot settings
  carry a norm; it now passes an explicit `Normalize`, signed for
  magnetograms.
- `superposed_epoch` crashed on timezone-aware epoch strings against the
  naive-UTC workspace convention; aware epochs are converted.
- `search_heliodata` adapted to an upstream break: the alpha HelioData API
  now answers 405 to any query parameter, so the tool fetches the bare
  catalog (cached a day) and filters client-side.

## v0.4.0 — 2026-09-04

Six new tools, one bug that had been silently misplacing every active region,
and input pins on all four data transports the HTTP cache cannot reach.
70 tools to 76; validation 28 checks to 49; tests 104 to 206.

### Fixed

- **SWPC region positions are valid at 2400 UT, not 0000 UT.** SWPC rotates
  each station measurement forward to the end of the report day, so
  `location` leads `observed_date` by a full 24 hours. Anything plotting
  those coordinates against a same-date image put every region **~14.5° too
  far west** — a quarter of a solar radius at disk centre. Measured rather
  than assumed: regressing `Location` against `Report_Location` and `Obstime`
  over 388 station reports gives a correction epoch of 24.07 h at
  14.50°/day, rms 0.27°. `get_solar_regions` now returns
  `coordinates_epoch`; `plot_solar_regions` uses it and refuses a mismatched
  image. Two validation checks pin the derivation.
- **`fetch_hapi` could not read most of ISWA.** ISWA declares
  `"type": "float"`, which the HAPI spec does not define, so `hapiclient`
  dies building its dtype. `fetch_hapi` now falls back to reading the
  server's `/data` CSV directly and reports the path in `reader`; conformant
  servers still go through `hapiclient`.
- **`merge_series` refused to join timezone-aware and naive indices.** It now
  converts to UTC *before* stripping the offset — a `+02:00` stamp lands on
  02:00 UTC, not 04:00 — and lists every conversion in `tz_normalized`.
  `fetch_hapi` also writes naive UTC now, matching every other retrieve tool.
  `merge_series` additionally refuses duplicate column names across files
  instead of letting pandas suffix them into an unreadable frame.

### Added

- **`fetch_goes_protons`** — GOES integral proton flux, 1986 to present.
  Measured EPEAD channels through 2020-03-04; after that the GOES-R archive
  has no >10 MeV integral channel at all, so a piecewise power law through
  the SGPS differential spectrum is integrated instead and flagged
  `derived`. The SGPS bands overlap and leave gaps, so a naive rectangular
  sum runs 1.25x high at >10 MeV — the power-law integral lands at 0.95x.
- **`plot_solar_regions`** — NOAA regions annotated onto any solar map,
  projected through the map's own WCS so B0 and P are handled by sunpy.
  Validated against the analytic identity
  `r/R = sin(arccos(sin φ sin B0 + cos φ cos B0 cos λ))` to better than
  0.006 R_sun.
- **`flare_probability`** — per-region C/M/X from the McIntosh class, since
  SWPC publishes whole-disk probabilities only. Poisson complement on
  McCloskey, Gallagher & Bloomfield (2016) Tables 5, 7 and 9. All three
  McIntosh letters are read, each from its own table, and **never
  multiplied**: they are marginal distributions, not factors of a joint one.
  The components can disagree tenfold, which is reported as
  `component_span`.
- **`get_sunspot_reports`** — raw per-observatory sunspot reports, ~1 month
  deep. Observatories disagree on the McIntosh class for **65% of
  region-days**, and a Zurich-letter tie leaves `zurich_consensus` None
  rather than picking between letters that can differ fourfold in flare
  probability.
- **`list_model_outputs` / `fetch_model_output`** — CCMC SWMF and ENLIL
  output via ISWA. Coverage is read live because catalog presence is not
  currency: every SWMF Dst run has stopped, and a stale run is refused
  unless `allow_stale`. ENLIL on this server is historical only; the tool
  says so and points at DONKI.

### Validation

- Six new **input pins** covering the four library-managed transports
  `helio_agent/http.py` names, none of which the content-addressed HTTP
  cache reaches: `omnipin` (cdasws/OMNI), `hmipin` (Fido/VSO, upstream FITS
  checksum), `radiopin` (cdasws/WAVES, full-array CSV checksum) and
  `libpins` (sscws, and pyspedas pinned at both the source CDFs — including
  their version suffix — and the derived CSV). Each layer was verified to
  trip by perturbing it. Before these, an upstream reprocessing would have
  moved published numbers with nothing to notice.
- New cases for the model tools, the McIntosh three-component read, the
  SWPC position epoch, and the station-report consensus.

## v0.3.1 — 2026-09-03

- **README docs index is generated**: `scripts/gen_docs.py` now also rewrites
  the block between the `gen_docs:docs-index` markers in `README.md`, linking
  every file in `docs/` with a one-line description (curated in `DOC_BLURB`,
  otherwise derived from the document's first prose line). `--check` covers
  it, so adding a doc without linking it fails CI the way a stale
  `docs/TOOLS.md` does. Picked up two previously unlinked documents
  (`helio_agent_review.md`, `helio_agent_merge_analysis.md`). The short
  pointer line above the index is generated from the same script
  (`DOC_LEAD`), which refuses to run if it names a document that no longer
  exists.

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
