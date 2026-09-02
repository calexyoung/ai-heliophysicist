# What helio-agent can teach ai-heliophysicist

> **Status (2026-09-02): implemented.** Tiers 1-3 landed the same day
> (HTTP cache + replay, coverage refusals, cotrans/tracing, Kyoto/GFZ
> indices, Dst nowcast + CME arrival with backtests, monitor ledger, saved
> reports, CI guards, EVT, AIA degradation, verify_claim). Deliberately
> excluded: HELIO4CAST catalogs (user decision: paper-specific) and
> agent-evals-in-CI (needs an LLM key in CI). Still open: hindcast
> machinery over the accumulating ledger. Kept as the design record.

A review of `~/Developer/helio-agent` (v1.1.0, 70 skills, ~930 recorded runs)
looking for features that would improve this project. helio-agent has a
different architecture (skill protocol + pipelines + FastAPI/web UI + an
embedded LLM orchestrator); the goal here is to harvest *ideas*, not to
reproduce its structure. Paths cited below are in the helio-agent repo.

## Tier 1 — adopt soon (high value, fits the current design directly)

### 1. Content-addressed HTTP cache with secret-stripped keys
`core/cache.py`: every HTTP response is cached under a sha256 of
(method, URL, sorted public params), with credentials excluded from the key
and from disk; non-2xx responses can be recorded too so fallback chains
replay identically. This is the single highest-leverage idea: our retrieve
tools re-hit CDAWeb/NOAA on every call, validation reruns are slow and
network-fragile, and offline testing is impossible. A small
`helio_agent/http.py` wrapper used by all tools would give us caching,
offline test fixtures, and replay in one move.

### 2. Replay, not just audit
`core/runner.py` + `core/manifest.py`: each run records harness version,
git sha, input params, the HTTP cache keys it touched, and sha256 of every
output file — and `runs replay` re-executes from cache alone, failing loudly
on divergence (`ReplayMismatch`). Our JSONL audit trail records *what
happened*; a manifest lets you *re-execute and verify* it. Extension path:
enrich audit entries with git sha + output checksums + cache keys, add
`helio-agent replay <audit_id>`.

### 3. Coverage-aware dataset registry + refuse-with-reason
`data/registry.py` maps (domain, observable) → datasets across ~44 missions
with *measured* coverage windows, so a request outside coverage fails
immediately with a useful message instead of an empty download. The idiom
"refuse with a reason rather than assert" (their CLAUDE.md) is worth adopting
verbatim in our contract. Cheap version: add coverage dates to our mission
skills (partly done) and teach fetch tools to pre-check the requested window
against dataset start/stop from the CDAWeb catalog.

### 4. Coordinate transforms and field-line tracing
`skills/analysis/cotrans.py` (GSE/GSM/SM/GEO/MAG with the dipole recomputed
per sample) and `skills/analysis/field_line_trace.py` (Tsyganenko T89
footpoints, open/closed flag, via geopack). We have a coordinate_systems
*skill document* but no transform *tool* — a real science gap. geopack is a
PyHC-evaluated package; both tools come with obvious validation anchors
(round-trip transforms; known conjugate points).

### 5. Cheap, high-value data sources we lack
- Kyoto Dst by revision (final/provisional/real-time) — `fetch_kyoto_dst`;
  our storm metrics currently ride on OMNI's copy only.
- GFZ Hp30/Hp60/Kp — keyless, higher-cadence activity indices (`fetch_gfz_index`).
- HELIO4CAST catalogs: ICMECAT (ICME list), HIGeoCAT (STEREO-HI CME
  geometry), ARRCAT (predicted arrivals) — three fetchers, instant access to
  curated CME/ICME populations for statistics and cross-checks.

## Tier 2 — high value, more work

### 6. Physics models with backtests: CME arrival + Dst nowcast
`cme_arrival.py` (drag-based-model ensemble → L1 arrival windows) and
`nowcast.py` (O'Brien–McPherron ring-current Dst model driven by L1 data,
~60 min lead), each paired with a *population-level* backtest
(`pipelines/backtest.py`, `pipelines/nowcast_backtest.py`) that tunes free
parameters (drag γ, injection gain) with out-of-sample holdout. This is the
model-layer our measure family stops short of, and the backtest-as-validation
pattern generalizes our single-anchor validation suite to whole populations.

### 7. Forecast verification discipline
`pipelines/hindcast.py`: score the live forecast rule over history —
precision/recall, timing errors, reliability diagram, confidence tiers
calibrated on a severity prior. If we ever emit forward-looking statements
(our Sun News "outlook" section), this is how they stay honest.

### 8. Monitoring mode with a persistent ledger
`pipelines/monitor.py` + `monitor_state.json`: a standing watch (one cron
entry point) that imports new DONKI storms, runs campaigns on unseen events,
posts tiered webhook alerts (alert transport kept *out* of the deterministic
core), and — critically — keeps a forward ledger of predictions that are
later scored hit/miss when they mature. Fits naturally onto our daily Sun
News flow: state file + `helio-agent monitor` command.

### 9. Engineering guards we should copy
- **Schema lock in CI** (`tests/test_schema_lock.py` + a lockfile): any tool
  output-shape change without a version bump fails the build.
- **Docs-current test** (`tests/test_docs_current.py`): README tool counts
  must match the live registry — we drifted on exactly this three times
  (37→41→43→47) before wiring the count to `helio-agent list`.
- **Offline tests against recorded fixtures** (86 test files, all network
  from recorded HTTP fixtures; weekly scheduled *live* smoke separately).
  Falls out nearly free once idea #1 exists. Our CI currently runs the live
  suite on every push — better: offline on push, live on schedule.

### 10. Saved campaign specs → rerunnable reports
`pipelines/saved.py` + `campaigns/`: a named, typed spec (parse once, rerun
many) that drives a multi-skill run ending in `report.md` + a self-contained
`report.html` with embedded figures. Our Sun News report was assembled from
an ad-hoc JSON in /tmp — the daily report should be a saved spec:
`helio-agent report sun-news --date 2026-09-02`. Self-contained HTML (images
inlined) is also a better sharing format than PDF for the web pipeline.

## Tier 3 — later / optional

- **Paper reproduction loop** (`agent/reproduce.py` → deterministic triage
  against a 1532-line capability inventory with measured coverage →
  `verify.py`, which *refuses* comparisons across mismatched cadence/units
  rather than reporting a false mismatch → `critique.py` where every
  suggestion must name a registered tool). The refuse-rather-than-false-
  mismatch verifier is the deepest idea here.
- **Extreme-value statistics** (`extreme_value.py`: POT/GPD with declustering,
  return periods; plus `evt_sweep.py` showing how much a published return
  period is a methodological choice) — strong fit for storm/flare statistics.
- **AIA degradation correction** (`correct_degradation.py` via aiapy — we
  already list aiapy as an optional extra).
- **Agent evals verified from manifests, run in CI** (`agent/evals.py`).
- FastAPI/web UI — only if this project ever needs non-CLI users.

## What ai-heliophysicist already does that helio-agent doesn't
For balance: a written skills/knowledge library the agent must read before
acting, validation anchored to *published* results (their tests are
schema/replay-focused), publication figure styling with a CVD-validated
palette, seaborn statistical plots, solar-cycle progression, SSCWeb
multi-spacecraft ephemerides, superposed epoch, and Lomb-Scargle. The two
projects converge from opposite ends: helio-agent is engineering-first
(replay, schema locks, backtests), this project is knowledge-first
(skills, anchors, style). The Tier 1–2 list above is mostly helio-agent's
engineering spine grafted onto this project's knowledge spine.

## Suggested order of attack
1. HTTP cache wrapper (#1) — unlocks #2 and #9's offline tests.
2. Docs-current + schema-lock tests (#9) — hours, prevents recurring drift.
3. cotrans + field-line tracing tools (#4) with validation anchors.
4. Kyoto Dst / GFZ indices / HELIO4CAST fetchers (#5).
5. Saved report specs for Sun News (#10).
6. Dst nowcast + CME arrival with backtests (#6), then monitoring (#8) and
   hindcast verification (#7).
