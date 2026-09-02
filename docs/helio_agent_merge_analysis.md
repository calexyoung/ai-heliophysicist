# Should helio-agent and ai-heliophysicist be combined?

*Analysis report — 2026-09-02. No changes made to either codebase.*

## Bottom line

**Combining is possible but not recommended now.** The two repos have
converged on ~60% overlapping capability but from *opposite* architectural
commitments, and a full merge would cost more than it returns. The
higher-value move is a **deliberate two-repo split by role** — helio-agent
as the personal lab/runtime, ai-heliophysicist as the shareable product —
with a disciplined port-on-demand policy (which is already working: three
tiers ported in one day). A thin *bridge* is feasible later if the union of
tool inventories is ever needed in one session, but it requires renaming
one package first.

## The two systems at a glance

| | helio-agent (v1.1.0) | ai-heliophysicist (v0.2.1) |
|---|---|---|
| Role today | Personal research harness, 930+ recorded runs | Public, shareable system on the HEASARC pattern |
| Size | ~32,300 lines `src/`, 86 test files | ~3,800 lines `helio_agent/`, 5 test files + 21 live checks |
| Unit of capability | 70 `Skill`s: pydantic `Input`/`Output`, semver, `execute(params, ctx)` | 61 `@tool` functions: plain kwargs → dict, CSV interchange |
| Composition | pipelines (campaign/backtest/hindcast/monitor) as registered skills | saved report chains (`reports.py`), monitor module |
| LLM | **in-repo** orchestrator (Anthropic provider), NL→CampaignSpec parser, reproduce/verify/critique/narrate | **external** — the agent is Claude Code reading `CLAUDE.md`; no LLM code in the package |
| Knowledge | prompt assets (routing/refusal/narration guidance) | 43 markdown skills the agent must read before acting |
| Reproducibility | run manifests (git sha, cache keys, output sha256), exact replay w/ `ReplayMismatch` | audit manifests (same fields) + `replay`, added this week |
| Validation philosophy | offline fixture replay + schema lock + weekly live smoke | live anchors to *published* results on every push + schema lock |
| Interfaces | Typer CLI (20+ commands), FastAPI, static web UI | CLI (7 commands); publishing via unmarkdown/export_html |
| Deps | core: fastapi, uvicorn, httpx, pydantic, typer; science libs as **optional extras** | batteries-included: sunpy, pyspedas, plasmapy, geopack, aiapy, seaborn… all core |
| Sharing model | none (single user, `user_catalog.json`) | `users/<name>/` profiles + promotion policy |
| License | MIT (C. Alex Young) | MIT (C. Alex Young) |
| **Python package name** | `helio_agent` (under `src/`) | `helio_agent` |

## Capability overlap

**Shared (implemented in both, independently):** HAPI/CDAWeb/VSO/Helioviewer
fetch, pySPEDAS load, Kyoto Dst, GFZ indices, NOAA RTSW, DONKI events,
flare finding, storm characterization, cotrans, T89 tracing, plasma
parameters, Dst nowcast (OBM), drag-based CME arrival, extreme-value
statistics, AIA degradation, HTTP cache + replay, monitor with scored
forecast ledger, ADS search, claim verification, rerunnable reports.

**helio-agent only (would be gained by combining):**
- Deeper analysis: `detect_icme` (shock + sheath + magnetic-cloud
  identification), `characterize_sep` (S-scale, fluence, velocity
  dispersion), `radio_bursts` (WIND/WAVES type II/III), `ionosphere` (IGS
  TEC), `ground_response` (magnetometer chains, dB/dt), `keogram`,
  `magnetogram` (unsigned flux, PIL proxy), `mosaic`/`reproject_map`,
  `kamodo_interpolate`, `power_spectrum`/`spectrogram`, `solar_coordinates`,
  `running_difference` GIFs.
- Population science: campaign backtests with γ scans + holdout,
  `hindcast` (precision/recall, reliability diagrams, confidence tiers),
  `nowcast_backtest`, AR climatology, EVT convention sweep as a pipeline.
- Event knowledge: curated event catalog with aliases (`events.resolve`),
  storm/SEP climatologies, `ar_profile`.
- HELIO4CAST fetchers (ICMECAT/HIGeoCAT/ARRCAT) — excluded from
  ai-heliophysicist by decision.
- A 986-line dataset registry with *measured* coverage windows across ~44
  missions; deterministic full-catalog search over ~6,900 dataset ids.
- Research: OpenAlex, full-text fetch, dedupe/rank/export pipeline.
- Agentic: in-repo reproduce → verify → critique → narrate loop with a
  1,532-line capability inventory; agent evals; NL campaign parser.
- FastAPI + web UI.

**ai-heliophysicist only (would be gained the other way):**
- The written skills library (missions/methods/datasources/tools) as a
  first-class, agent-mandatory knowledge layer.
- Validation anchored to published results (not just replay fidelity).
- User profiles + promotion policy for multi-person sharing.
- Publication figure styling (CVD-validated palette, journal geometry,
  editable vector) and seaborn statistical plots.
- Publishing: analysis-note format, hosted templates, self-hosted/offline
  HTML export with SRI-pinned runtime, four-edition `--archive` reports.
- Solar-cycle progression, SSCWeb ephemerides/orbit plots, superposed
  epoch, Lomb–Scargle, GOES XRS science-quality fetch with the SWPC-scaling
  distinction made explicit.
- Harness-agnostic design: any CLAUDE.md-reading agent drives it; no LLM
  vendor lock in the package.

## What combining would buy

1. **One inventory, ~110 unique capabilities**, driven by one agent session
   — today a question needing `detect_icme` *and* publication output spans
   two repos and two conventions.
2. **No more parallel maintenance** of cache, replay, monitor, models, EVT,
   verify — each currently exists twice, and drift is inevitable (their
   monitor posts webhook alerts and has hindcast; ours has multi-analysis
   handling and DONKI TTLs; neither has both).
3. helio-agent's engineering rigor (fixture-based offline tests, schema
   versioning per skill, manifest-exact replay) applied to
   ai-heliophysicist's breadth; ai-heliophysicist's knowledge layer and
   published-result anchors applied to helio-agent's depth.
4. Single place for collaborators after the shared-account move.

## What combining would cost

1. **Package-name collision.** Both ship `helio_agent`. They cannot be
   installed in one environment; any merge or bridge starts with renaming
   one (touching ~32k lines of imports on the helio-agent side, or ~4k on
   ours). Mechanical but total.
2. **Two incompatible capability contracts.** Pydantic-typed Skills with
   versions and a `ctx.http` injection vs. plain `@tool` functions returning
   dicts. Unifying means either wrapping 70 skills as tools (losing typed
   I/O and schema-version semantics) or wrapping 61 tools as skills
   (writing 61 pydantic models). Either is a week of human work / a long
   day of CC work, plus re-validating everything.
3. **Two manifest/audit formats and two caches.** helio-agent's 930
   recorded runs and their replay guarantees are bound to its manifest
   schema; our audit ids are cited in analyses and validation. A merged
   history is not possible; a merged *format* means one side's replay
   promises break.
4. **Opposite dependency philosophies.** helio-agent keeps a tiny core and
   makes science libs optional (import-guarded per skill); we made them all
   core so every tool works out of the box. A merge must pick one — ours is
   simpler for the agent, theirs is friendlier to contributors and CI.
5. **LLM placement is a design fork, not a detail.** helio-agent embeds an
   Anthropic-specific orchestrator and NL parser; ai-heliophysicist
   deliberately keeps the LLM outside the package so the pattern is
   model-agnostic (the HEASARC "swappable brain" principle). Merging means
   either importing vendor lock into the shareable repo or amputating
   helio-agent's agent layer.
6. **Testing philosophies conflict on CI cost.** Their 86 offline
   fixture tests are fast and hermetic; our live suite is slow but proves
   science truth. Both are right; a merged CI needs both tiers wired.
7. **Interfaces.** FastAPI + web UI have no counterpart here and no stated
   need; they'd arrive as ~5k lines of surface to maintain.

## Feasibility of the options

| Option | What | Feasible? | Effort (human / CC) | Verdict |
|---|---|---|---|---|
| **A. Full merge** into one package | rename, unify contract + manifests + cache + CI, port both ways | Yes, technically | 2–3 weeks / 2–3 days, plus re-validation | Not worth it now; freezes both for the duration and forces the LLM-placement decision |
| **B. Bridge** | rename helio-agent's package (e.g. `helioharness`), install as optional dep, expose its skills as `[bridge:*]` tools with audit passthrough | Yes, moderate | 3–5 days / ~1 day | Viable *if* a real workflow needs both inventories in one session; typed I/O survives (tools pass dicts to pydantic models) |
| **C. Two repos by role + port-on-demand** (status quo, made explicit) | helio-agent = lab; ai-heliophysicist = product; capabilities cross via the promotion policy with validation anchors | Already working | hours per capability | **Recommended** |
| **D. Reverse absorb** — fold ai-heliophysicist into helio-agent | knowledge layer, profiles, publishing become helio-agent modules | Yes | 1–2 weeks / 1–2 days | Loses the shareable, harness-agnostic design goal; the public repo would become a personal harness |

## Recommendation

Adopt **C, explicitly**, and treat **B** as a documented future option:

1. Declare roles in both READMEs: helio-agent is the personal laboratory
   (embedded LLM experiments, campaigns, web UI, exhaustive offline tests);
   ai-heliophysicist is the shareable system (HEASARC pattern, external
   agent, published-result validation, profiles, publishing).
2. Keep porting by the existing rule — *could the next paper use it?* —
   each port arriving with a validation anchor. Highest-value next ports
   from helio-agent, in order:
   - `detect_icme` (shock/sheath/cloud identification — the missing link
     between our CME arrival forecasts and the ledger's verdicts; would let
     the monitor score arrivals from L1 data itself instead of relying on
     DONKI's IPS list),
   - `characterize_sep` + `radio_bursts` (today's Type II event would have
     been fully characterized in-house),
   - `hindcast` (precision/recall over our accumulating ledger),
   - `magnetogram`/PIL flux (the region-evolution story we narrate by hand),
   - the coverage-measured dataset registry idea (we refuse on coverage
     already; a curated observable→dataset map would make discovery faster).
3. Decide the one shared thing now: **rename helio-agent's package** at
   your next convenient moment (e.g. `helioharness`). It is cheap while the
   repo is single-user, and it unblocks option B forever; leaving both as
   `helio_agent` is the single decision that makes any future combination
   painful.
4. Revisit A only if a second maintainer wants helio-agent's engineering
   spine as the base — at that point the right move is probably to make
   helio-agent's core (skill protocol, manifests, cache) a small shared
   library both repos depend on, rather than merging the applications.

## Sanity checks on this analysis

- Overlap figures come from the registered-skill list in helio-agent
  (70 names, `src/helio_agent/skills/__init__.py` + pipelines) against our
  61-tool registry; "shared" means the same capability, not identical code.
- Effort estimates assume no new science; re-validation is the hidden cost
  in every option and is why C wins on risk.
- Both projects are MIT under the same author, so licensing is not a
  constraint in any direction.
