# AI Heliophysicist — Usage Guide

Everything you need to install, drive, extend, and operate the system.
Companion references: [TOOLS.md](TOOLS.md) (every tool, generated),
[SKILLS.md](SKILLS.md) (every skill document, generated), [MODULES.md](MODULES.md)
(package internals), [ARCHITECTURE.md](ARCHITECTURE.md) (design rationale);
the agent's behavioral contract is [../CLAUDE.md](../CLAUDE.md).

## Contents

1. [Setup](#1-setup)
2. [CLI reference](#2-cli-reference)
3. [Driving tools](#3-driving-tools)
4. [Workflow: from question to figure](#4-workflow-from-question-to-figure)
5. [Workflow: the daily report](#5-workflow-the-daily-report)
6. [Workflow: monitoring and forecasts](#6-workflow-monitoring-and-forecasts)
7. [Workflow: paper reproduction](#7-workflow-paper-reproduction)
8. [Publishing analysis output](#8-publishing-analysis-output)
9. [User profiles](#9-user-profiles)
10. [Reproducibility: audit, cache, replay](#10-reproducibility-audit-cache-replay)
11. [Adding a tool](#11-adding-a-tool)
12. [Scheduling](#12-scheduling)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Setup

Requirements: Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/calexyoung/ai-heliophysicist
cd ai-heliophysicist
uv sync
uv run python validation/run_validation.py   # ~3 min, live against NASA services
```

A green validation run proves your environment end to end — it reproduces
published results (the Halloween 2003 Dst minimum, the 2017 X9.3 flare
timing, the 2012-07-23 extreme CME) from live archives.

### Optional keys (`.env` in the repo root, gitignored)

```
ADS_API_TOKEN=...          # NASA ADS literature search (free: ui.adsabs.harvard.edu/user/settings/token)
UNMARKDOWN_API_KEY=...     # hosted publishing templates (export_html engine="local" needs no key)
HELIO_AGENT_USER=<name>    # activate your user profile durably (see §9)
```

Tools that need a missing key refuse with a reason — nothing fails silently.

### Using it as an AI agent

Open the directory in Claude Code (or any agent harness that reads
`CLAUDE.md`). The contract makes the session the AI Heliophysicist: the
LLM plans and interprets, tools compute, everything is audited. Four levels
of delegation are defined in CLAUDE.md — from "find and fetch" to "carry a
question to a finished, checked result."

---

## 2. CLI reference

```
uv run helio-agent list [family]        # all tools, or one family
uv run helio-agent describe <tool>      # signature + full docstring
uv run helio-agent run <tool> '<json>'  # invoke with JSON kwargs (audited)
uv run helio-agent replay <audit-id>    # re-execute a recorded call from cache
uv run helio-agent audit [n]            # last n audit entries (default 10)
uv run helio-agent monitor              # one standing-watch cycle (see §6)
uv run helio-agent report sun-news [--date YYYY-MM-DD] [--archive]
```

Families: `discover`, `retrieve`, `reduce`, `measure`, `literature`,
`report`. Every `run` returns JSON including `status`, an `audit_id`, and
(for file-producing tools) `artifacts` paths.

Python access for longer pipelines:

```python
from helio_agent.registry import run_tool
r = run_tool("fetch_omni", start="2024-05-10T00:00:00Z", end="2024-05-14T00:00:00Z")
```

Each `run_tool` call is one audit entry, same as the CLI.

---

## 3. Driving tools

### The interchange format

Every retrieve tool writes a **workspace CSV**: UTC `time` index, NaN for
fill values, units reported in the tool result. Any reduce/measure/report
tool consumes that format — this is what lets one small tool set chain 60+
mission archives.

### Finding data

```bash
uv run helio-agent run search_cdaweb_datasets '{"keyword":"OMNI"}'
uv run helio-agent run list_cdaweb_variables '{"dataset":"OMNI2_H0_MRG1HR"}'
uv run helio-agent run search_heliodata '{"query":"solar wind proton"}'
uv run helio-agent run list_pyspedas_missions '{}'
uv run helio-agent run list_pyspedas_loaders '{"mission":"mms"}'
uv run helio-agent run list_spacecraft '{}'
```

Events and context:

```bash
uv run helio-agent run search_hek_events '{"start":"2017-09-06T00:00:00","end":"2017-09-07T00:00:00","event_type":"FL"}'
uv run helio-agent run search_donki '{"start_date":"2017-09-06","end_date":"2017-09-07","kind":"FLR"}'
uv run helio-agent run get_noaa_realtime '{"product":"alerts"}'
uv run helio-agent run get_solar_regions '{}'
```

### Refusals are features

Tools refuse with a reason instead of guessing: a window outside a
dataset's coverage names the actual coverage; a missing key names the key;
`verify_claim` refuses unit-mismatched comparisons. When you see
`"refusing: ..."`, the message tells you what to do instead.

### Data-quality tiers

Beacon / low-latency / real-time sources (NOAA SWPC feeds, STEREO beacon,
Solar Orbiter LL02) are **operational, not science quality** — tool results
say so, and conclusions built on them should too. Science-quality archives
(CDAWeb level-2, Kyoto final Dst) are the citable tier.

---

## 4. Workflow: from question to figure

*"How strong was the May 2024 storm?"* — the canonical
discover → retrieve → measure → report chain:

```bash
# retrieve: OMNI hourly with defaults (|B|, Bz, V, n, Dst, Kp)
uv run helio-agent run fetch_omni '{"start":"2024-05-09T00:00:00Z","end":"2024-05-15T00:00:00Z"}'
# → workspace/data/OMNI2_H0_MRG1HR_2024-05-09_2024-05-15.csv

# measure: storm characterization
uv run helio-agent run storm_metrics '{"file":"<that csv>","dst_column":"DST1800"}'
# → {"dst_min_nT": -406.0, "time_of_min": "2024-05-11 02:30:00", "classification": "extreme...", "audit_id": "..."}

# cross-check against the index producer (revision-aware)
uv run helio-agent run fetch_gfz_index '{"index":"Hp30","start":"2024-05-10","end":"2024-05-12"}'

# report: the standard space-physics stack plot
uv run helio-agent run plot_stack '{"files_columns":[
  {"file":"<csv>","column":"ABS_B1800","label":"|B| (nT)"},
  {"file":"<csv>","column":"BZ_GSM1800","label":"Bz GSM (nT)"},
  {"file":"<csv>","column":"V1800","label":"Vsw (km s$^{-1}$)"},
  {"file":"<csv>","column":"DST1800","label":"Dst (nT)"}],
  "title":"May 2024 (Gannon) superstorm","out_name":"gannon.png"}'
```

Figures come out publication-styled by default (journal geometry, boxed
axes with inward minor ticks, CVD-validated Okabe-Ito palette, 300 dpi;
save `.pdf`/`.svg` in `out_name` for editable vector output). See
`skills/tools/plotting_conventions.md`.

Models when you need them:

```bash
uv run helio-agent run model_dst '{"file":"<csv>","v_column":"V1800","bz_column":"BZ_GSM1800","density_column":"N1800","dst_column":"DST1800"}'
uv run helio-agent run cme_arrival '{"v0_kms":1400,"launch_time":"2012-07-12T19:35Z","w_kms":400}'
uv run helio-agent run extreme_value '{"file":"<61yr dst csv>","column":"DST1800","threshold":-100,"direction":"min"}'
```

Each model reports its assumptions and typical accuracy; `extreme_value_sweep`
shows how much a return period depends on threshold/declustering choices —
quote the spread, not one cell.

---

## 5. Workflow: the daily report

```bash
uv run helio-agent report sun-news                       # today, PDF + figures
uv run helio-agent report sun-news --date 2026-09-02     # specific day (within feed windows)
HELIO_AGENT_USER=<you> uv run helio-agent report sun-news --archive
```

The report is a saved, rerunnable chain of ~16 audited tool calls: GOES XRS
+ flare detection, RTSW solar wind, Kp, NOAA region analysis, DONKI CMEs,
solar-cycle progression → figures + PDF. `--archive` additionally builds
the markdown web edition (live Chart.js blocks from the same CSVs) and the
self-hosted HTML, filing all editions + README under
`users/<you>/analyses/sun-news-<date>/`. Archive refuses without an active
user profile; the HTML step degrades gracefully without the publishing key.

Note: NOAA operational feeds roll (3–7 days), so `--date` older than that
refuses.

---

## 6. Workflow: monitoring and forecasts

```bash
uv run helio-agent monitor
```

One cycle: reads current Kp/X-ray conditions, imports new DONKI CMEs,
issues drag-based arrival forecasts for Earth-directed analyses
(|longitude| ≤ 60°), **matures past windows against observed DONKI Earth
shocks into a persistent hit/miss ledger** (`workspace/monitor_state.json`),
and records new geomagnetic storms. Forecasts are never silently forgotten —
every one is eventually scored.

Run it from cron/launchd daily (see §12). Read the ledger for forecast
skill; as it accumulates, precision/recall analysis becomes possible.

---

## 7. Workflow: paper reproduction

Full method: `skills/methods/paper_reproduction.md`. The loop:

1. **Extract claims** from the paper (fetch via `search_ads` /
   `fetch_arxiv_pdf`): value, units, dataset, cadence, processing level.
2. **Triage** each claim: `ready` / `method_gap` (propose a tool, don't
   improvise) / `blocked` (data not public).
3. **Recompute like-for-like** — match cadence, dataset version, and
   conventions (GOES scaling, Dst revision, AIA degradation).
4. **Verify**:

```bash
uv run helio-agent run verify_claim '{"claimed_value":109.0,"computed_value":109.086,
  "claimed_units":"nT","computed_units":"nT","tolerance_percent":1.0,
  "claim_description":"Russell et al. 2013: peak B","computed_audit_id":"<id>"}'
```

`verify_claim` refuses unit mismatches and audit-untraceable values; a
`mismatch` verdict is a finding to investigate, never an immediate "the
paper is wrong."

5. **Report** per claim: verdict, difference, audit ids, caveats.
   Unverified claims are listed as unverified, not omitted.

Worked example (3 matches, 1 honestly blocked by an instrument data gap):
[users/cayoung/analyses/2012-07-23-extreme-cme/](../users/cayoung/analyses/2012-07-23-extreme-cme/analysis.md).
A fully reproduced paper deserves a permanent validation case.

---

## 8. Publishing analysis output

Full conventions: `skills/tools/analysis_notes.md` (canonical note
structure, 7 vetted templates with live samples; default template:
`research`).

**Self-hosted HTML** (no external hosting):

```bash
# hosted-template styling via the unmarkdown API (needs UNMARKDOWN_API_KEY)
uv run helio-agent run export_html '{"markdown_file":"note.md"}'

# fully local: conversion + styling on-machine, no API, no key
uv run helio-agent run export_html '{"markdown_file":"note.md","engine":"local"}'

# fully offline page: libraries hash-verified against SRI pins and inlined (~3.3 MB)
uv run helio-agent run export_html '{"markdown_file":"note.md","engine":"local","embed_assets":true}'
```

Pages render Mermaid diagrams, Chart.js blocks, and KaTeX math client-side.
Hosted share links (unmarkdown.com pages) are created via the unmarkdown
MCP tools from an agent session; remember that updating a document does
**not** update its published page — republish after edits.

---

## 9. User profiles

The repo is shared; one-off work is personal. Full policy:
[users/README.md](../users/README.md).

```bash
export HELIO_AGENT_USER=<name>     # or put it in .env for durability
cp -r users/_template users/<name>
```

With a profile active: data/outputs/audit route to
`users/<name>/workspace/`; any `.py` in `users/<name>/tools/` auto-loads
(tagged `[user:<name>]`, cannot shadow core names, excluded from the core
schema lock); completed analyses live in `users/<name>/analyses/<slug>/`
with an `analysis.md` citing audit ids. The shared HTTP cache stays global.

**Promotion policy** — the one question: *could the next paper use it?*
Yes → core (`helio_agent/` + validation case + skill note + schema-lock
regen). No → your profile.

---

## 10. Reproducibility: audit, cache, replay

- **Audit trail** (`workspace/logs/audit.jsonl`, per-profile when active):
  every call records args, status, elapsed, git sha, touched HTTP cache
  keys, and sha256 of every artifact. Cite audit ids for headline numbers.
- **HTTP cache** (`workspace/cache/`, always shared): content-addressed by
  sha256(method + URL + public params); credentials never touch keys or
  disk; real-time feeds carry TTLs so nowcasts never serve stale data.
  Modes via `HELIO_CACHE_MODE`: `readwrite` (default), `readonly` (replay),
  `bypass`.
- **Replay**:

```bash
uv run helio-agent replay <audit-id>
# → verdict "match" if the re-run reproduces artifact checksums from cache alone
```

A `mismatch` means the code or upstream data changed since the recording —
either way, you know.

---

## 11. Adding a tool

1. Write the function in `helio_agent/tools/<family>.py` with the `@tool`
   decorator (params must be JSON-serializable; return a dict; include
   `artifacts` for files; refuse with a reason on bad input).
2. Add a **validation case** in `validation/run_validation.py` anchored to
   a published/known result. A tool without an anchor is a draft — its
   results must be labeled unvalidated.
3. Record any craft in a skill (`skills/`), and regenerate the schema lock:

```bash
uv run python tests/test_schema_lock.py --update
uv run pytest tests/ -q
uv run python validation/run_validation.py
```

CI enforces the lock and README/registry consistency, then runs the live
suite — interface drift and docs drift both fail the build.

---

## 12. Scheduling

macOS launchd (survives sleep — a missed run fires on wake), using the
committed wrapper:

```xml
<!-- ~/Library/LaunchAgents/com.helio-agent.monitor.plist -->
<key>ProgramArguments</key>
<array><string>/bin/bash</string>
<string>/path/to/ai-heliophysicist/scripts/monitor_cron.sh</string></array>
<key>StartCalendarInterval</key>
<dict><key>Hour</key><integer>7</integer><key>Minute</key><integer>15</integer></dict>
```

```bash
launchctl load ~/Library/LaunchAgents/com.helio-agent.monitor.plist
tail -f workspace/logs/monitor_cron.log
```

Linux cron equivalent: `15 7 * * * /path/to/scripts/monitor_cron.sh`.
The same pattern works for a daily `report sun-news --archive`.

---

## 13. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `refusing: requested window ... outside coverage` | The dataset doesn't span your dates — the message names actual coverage; pick another window or dataset. |
| `CacheMiss` during replay | The original call predates the HTTP cache or bypassed it; re-run live first. |
| `ADS_API_TOKEN not set` / `UNMARKDOWN_API_KEY not set` | Add to `.env`; or for export use `engine="local"` (no key). |
| GOES flare classes ~30-40% above published values | Science-quality netcdf is TRUE flux; historical classes use SWPC-scaled flux. `find_flares(swpc_scale=true)` (default) matches the operational record; see `skills/missions/goes.md`. |
| `--date` older than a few days refuses on sun-news | NOAA operational feeds roll (3-7 days); use archival tools (`fetch_goes_xrs`, `fetch_omni`) for history. |
| Outputs landing in `users/<name>/workspace/` unexpectedly | `HELIO_AGENT_USER` is set (possibly in `.env`) — that's profile routing working; unset it for core-workspace runs. |
| Duplicate/odd timestamps from real-time feeds | Handled: RTSW dedupe and newest-first alert sorting are built in; if a NEW feed misbehaves, check its raw JSON before blaming the tool. |
| Charts/mermaid missing in exported HTML opened offline | Default export loads libraries from CDNs; use `embed_assets: true` for a fully offline page. |
| A validation check fails after a dependency upgrade | That's the suite doing its job. Diagnose with `replay` on the case's audit ids; fix the tool or (if upstream data legitimately changed) re-anchor the check with a comment explaining why. |

Epoch-handling rule that has bitten before (recorded in
`skills/methods/coordinate_systems.md`): derive unix seconds as
`(t - pd.Timestamp(0)) / pd.Timedelta(seconds=1)`, treat naive times as
UTC, and never trust `.view('int64')` or naive `.timestamp()`.
