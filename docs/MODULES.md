# `helio_agent` package reference

The tool layer's internals, module by module. For the per-tool reference
see [TOOLS.md](TOOLS.md) (generated); for the knowledge layer see
[SKILLS.md](SKILLS.md) (generated); for how to drive it see
[USAGE.md](USAGE.md).

```
helio_agent/
  __init__.py     package version; re-exports tool/get_tool/list_tools/run_tool
  registry.py     @tool decorator, Tool records, run_tool (audit wrapper), replay, user-tool loading
  audit.py        append-only JSONL manifests (args, status, git sha, cache keys, artifact sha256)
  http.py         content-addressed HTTP cache (GET/POST), modes, TTLs, touched-key tracking
  reproduction.py versioned paper manifests, deterministic validation, Markdown rendering
  workspace.py    paths: ROOT/WORKSPACE/DATA/OUTPUT/LOG/CACHE; .env loading; user-profile routing
  style.py        publication figure styling: palette, rcParams, figsize, seaborn theme, event lines
  cli.py          `helio-agent` entry point: list/describe/run/replay/audit/monitor/report
  monitor.py      standing watch cycle with the scored forecast ledger
  reports.py      saved rerunnable report chains (sun-news) incl. web edition + archive
  tools/          the six families (one module per concern; see below)
```

Design rule that shapes every module: **tools compute, the agent judges.**
Nothing in this package calls an LLM; nothing here embeds scientific
judgment beyond the deterministic method a tool's docstring states.

---

## Core modules

### `registry.py`
- `@tool(family, name=None)` registers a plain function. Its signature
  becomes the interface (`Tool.params` holds annotations; the schema lock in
  `tests/` hashes them). Families are fixed: `discover retrieve reduce
  measure literature report`.
- `run_tool(name, **kwargs)` is the only sanctioned way to invoke a tool:
  it resets the HTTP touched-key list, calls the function, normalizes the
  result to a dict with `status` (default `"ok"`), writes the audit entry
  (with the touched cache keys and artifact checksums), and injects
  `audit_id`. Exceptions become `status: "error"` results — a tool never
  crashes the agent.
- `replay(entry_id, readonly_cache=True)` re-executes a recorded call with
  `HELIO_CACHE_MODE=readonly` and compares status, canonical result, pre-run
  input hashes, artifact path sets, and artifact hashes. Verdicts are
  `match`, `mismatch`, or `unverifiable` for legacy records lacking enough
  evidence; the response names each affected dimension.
- `_load_all()` imports `helio_agent.tools` (core) and, if a user profile is
  active, every `users/<name>/tools/*.py`, tagging those `scope="user:<name>"`
  and refusing name collisions with core tools.

### `audit.py`
- `record(...)` appends one JSON line per call to `workspace/logs/audit.jsonl`
  (or the active profile's log): id, timestamp, tool, args, status, elapsed,
  result summary, canonical full **result**, error, artifacts, **git_sha**
  (with `-dirty`), **cache_keys** touched, **input_sha256** for file inputs,
  and **artifact_sha256** per output. This is the evidence that `replay`
  verifies and reproduction manifests cite.
- `find_entry(id)`, `hash_file(path)`, `hash_input_files(args)`,
  `canonical_result(value)`, and `git_sha()` helpers.

### `http.py`
- `cached_request(method, url, params, json_body, headers, ...)` — the HTTP
  path for tools that call REST endpoints directly; `cached_get(...)` is its
  compatible GET wrapper. Sources include CDAWeb
  REST, DONKI, NOAA SWPC, Helioviewer, HelioData, arXiv, Kyoto, GFZ, CDN
  assets). Key = sha256(method, URL, sorted *public* params, canonical JSON
  body hash). Credential-like fields are excluded and request bodies are
  never written to metadata. Store: `workspace/cache/<2ch>/<key>.json`
  (status, url, fetched_at, base64 body).
- Modes via `HELIO_CACHE_MODE`: `readwrite` (default), `readonly` (a miss
  raises `CacheMiss` — used by replay), `bypass`.
- `ttl_seconds` marks real-time feeds stale (SWPC 5 min, DONKI 30 min,
  catalogs 24 h); replay ignores TTL so it always uses what was recorded.
- Library-managed transfers (cdasws, sunpy Fido, sscws, pyspedas) bypass
  this cache and keep their own on-disk caches under `workspace/data`;
  replay covers them at the artifact-checksum level.

### `workspace.py`
- `ROOT` (overridable via `HELIO_AGENT_ROOT`), `load_env()` (reads `.env`
  once; existing environment wins), then the path constants. With
  `HELIO_AGENT_USER` set, `WORKSPACE` becomes `users/<name>/workspace`;
  `CACHE_DIR` is always the shared `workspace/cache`.
- `active_user()`, `user_dir()`, `ensure_dirs()`, `output_path(name)`,
  `data_path(name)`. Generated names must be relative and remain below their
  resolved workspace root; traversal, absolute paths, and symlink escapes are
  refused before parent directories are created.

### `reproduction.py`
Owns schema-version-1 paper reproduction manifests. `validate_manifest`
accumulates stable, path-addressed errors and checks required paper/claim/data
fields, capability/verdict enums, unique IDs, successful recipe audits, and
agreement with the recorded `verify_claim` result. Three registered tools
create JSON under workspace data, validate existing JSON, and render a
deterministic Markdown report under workspace outputs. Extracting claims from
arbitrary papers remains agent/scientist work, not an automated guarantee.

### `style.py`
- `PALETTE` (Okabe–Ito in a CVD-validated order), `EVENT_COLOR`,
  colormap choices, `RC` (matplotlib rcParams: journal fonts/sizes, boxed
  axes with inward major+minor ticks, recessive grid, frameless legends,
  300 dpi, fonttype 42), `apply_style()`, `figsize("column"|"page"|"slide",
  aspect)`, `seaborn_theme()`, `style_event_lines(ax, times, labels)`.
  Every report tool calls `apply_style()` first.

### `cli.py`
Thin dispatcher over the registry: `list [family]` (marks user-scoped tools),
`describe`, `run` (JSON kwargs), `replay`, `audit [n]`, `monitor`,
`report <name> [--date] [--archive]`. Exit code 1 on tool error or
replay mismatch/unverifiable result, or monitor `error`, so shell pipelines
can gate on it. Monitor `degraded` remains visible but exits zero.

### `monitor.py`
`cycle(lookback_days=3)`: reads Kp and long-channel XRS conditions, groups
DONKI CME analyses by CME and forecasts the fastest Earth-directed-cone fit
(|lon| ≤ 60°) via `cme_arrival`, matures pending forecasts whose window +
12 h grace has passed by searching DONKI Earth IPS arrivals (hit/miss into
`state["ledger"]`), records new GST ids. A cycle reports `ok`, `degraded`
(optional condition feed failed), or `error` (required event ingestion
failed), with `failed_sources`; unavailable IPS data never becomes a false
miss. State records attempt and successful-ingestion timestamps and is saved
by atomic sibling replacement. Every access is audited.

### `reports.py`
`sun_news(date, archive)`: the saved daily-report chain — ~16 audited
tool calls from operational feeds to figures + PDF; with `archive=True`,
also the markdown web edition (`_markdown_edition` builds Chart.js blocks
from the same CSVs), `export_html`, and a README, filed under the active
profile's `analyses/sun-news-<date>/`. `REPORTS` maps CLI names to builders;
adding a report = adding a function here.

---

## Tool modules (`helio_agent/tools/`)

`tools/__init__.py` imports every module below so registration runs on
first use. Per-tool signatures and docstrings: [TOOLS.md](TOOLS.md).

| Module | Family(ies) | Contents |
|---|---|---|
| `discover.py` | discover | CDAWeb dataset/variable search (REST, cached 24 h), HelioData search, SSCWeb spacecraft list, VSO search (sunpy Fido), HEK events, DONKI (30-min TTL), NOAA real-time products with timestamp-sorted latest records |
| `retrieve.py` | retrieve | `fetch_cdaweb_data` (cdasws → xarray → CSV with FILLVAL→NaN and a coverage pre-check that refuses out-of-range windows), `fetch_omni` defaults, `fetch_goes_xrs` (sunpy, science-quality netcdf), `fetch_vso` (capped), `fetch_helioviewer_image`, `fetch_spacecraft_ephemeris` (sscws), `fetch_hapi`, `save_json` |
| `swpc.py` | retrieve, discover | NOAA operational feeds: `fetch_swpc_timeseries` (xray/plasma/mag/kp; 2026 dict-format RTSW endpoints sourced from IMAP; dedupes repeated timestamps), `fetch_solar_cycle` (monthly/smoothed SSN + F10.7 with peak summary), `get_solar_regions` |
| `indices.py` | retrieve | `fetch_kyoto_dst` (final/provisional/realtime with the revision reported), `fetch_gfz_index` (Kp/ap/Hp30/Hp60/…) |
| `spedas.py` | discover, retrieve | pySPEDAS 2.x integration: mission/loader listing and `fetch_pyspedas` (tplot → CSV; spectrogram-like variables skipped) |
| `reduce.py` | reduce | describe / resample / merge / gap-limited interpolate / derived columns via `pandas.eval` / time shift / `load_solar_map` |
| `geospace.py` | reduce, measure | `transform_coordinates` (pySPEDAS cotrans, gei/gse/gsm/sm/geo/mag/j2000; resolution-proof epoch handling), `trace_field_line` (geopack T89+IGRF footpoints, topology) |
| `aia.py` | reduce | `aia_degradation` factors and `correct_aia_map` (aiapy) |
| `measure.py` | measure | `find_flares` (1-min SWPC-style detector with the operational-scaling switch), `find_extrema`, `storm_metrics`, `lomb_scargle` (astropy), `cross_correlate`, `superposed_epoch`, `propagation_delay`, `plasma_parameters` (PlasmaPy), `linear_fit` |
| `models.py` | measure | `model_dst` (O'Brien–McPherron 2000 with pressure correction and skill scores), `cme_arrival` (Vršnak drag-based model with a γ × wind ensemble window) |
| `extremes.py` | measure | `extreme_value` (POT/GPD, runs declustering, closed-form method of moments, return levels), `extreme_value_sweep` (threshold × declustering grid) |
| `verify.py` | measure | `verify_claim` — unit normalization, refusal on unit mismatch or missing audit id, match/mismatch with relative difference |
| `literature.py` | literature | ADS search (needs `ADS_API_TOKEN`), BibTeX export, arXiv search (defusedxml), arXiv PDF fetch |
| `report.py` | report | `plot_timeseries`, `plot_stack`, `plot_solar_map`, `plot_orbits`, seaborn `plot_distribution`/`plot_scatter`, `write_pdf_report` (fpdf2) |
| `export.py` | report | `export_html`: unmarkdown-template or local (markdown-it-py) conversion, SRI-pinned Mermaid/Chart.js/KaTeX runtime, optional hash-verified asset embedding for offline pages |
| `reproduction.py` | measure, report | create/validate schema-version-1 reproduction manifests and render deterministic audit-linked Markdown summaries |

### Conventions every tool module follows
- Heavy imports (sunpy, pyspedas, geopack…) happen *inside* the tool
  function so `helio-agent list` stays fast and a broken optional stack
  breaks only the tools that need it.
- Inputs that reference data are **file paths to workspace CSVs**; outputs
  that produce data return `file` + `artifacts` and describe columns/units.
- Refuse early with `{"status": "error", "error": "refusing: ..."}`; never
  silently substitute or return partial results dressed as complete.
- Real-time sources say so in their result (`quality`, notes) so downstream
  text can carry the caveat.

---

## Supporting trees

- `validation/run_validation.py` — 28 live checks in 21 cases, directly
  referencing 29 core tools. Supporting tools use offline guards (schema
  lock, docs-current, cache/provenance/path behavior, user-tool scoping) and
  validated composition; a new scientific method still needs an appropriate
  anchor.
- `scripts/gen_docs.py` — regenerates TOOLS.md/SKILLS.md; `--check` is run
  by the tests. `scripts/monitor_cron.sh` — the daily monitor wrapper.
- `skills/` — the knowledge layer (43 documents; catalog in SKILLS.md).
- `users/` — profiles; `users/_template/` to copy.
