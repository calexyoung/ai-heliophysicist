# May 2024 (Gannon) storm: two Dst models against the measurement

Computed 2026-09-04. Companion to
[insitu-icme-detection.md](insitu-icme-detection.md), which established what
actually hit. This asks a narrower question: **how well did the models do?**

Three series on one hourly grid, 2024-05-09 to 05-15:

| Series | What it is |
|---|---|
| `SYM_H` | **Measured.** OMNI 1-min, averaged to hourly. |
| `dst_model` | **Analytic.** O'Brien & McPherron (2000) ring-current integral, driven by the same OMNI solar wind. |
| `swmf_dst` | **MHD.** CCMC SWMF 2023 real-time run, via ISWA. Driven by L1 data as it arrived in May 2024. |

Figure: `workspace/outputs/gannon_dst_threeway.png` (audit `7cbed49a2bac`).

## Why hourly

O'Brien & McPherron was fitted at hourly cadence and its tool docstring says
so, so hourly is the honest common grid. It has a consequence worth stating
up front: **the observed minimum on this grid is -436.0 nT, not the -518.0 nT
quoted in the in-situ write-up.** Same data — hourly averaging shallows a
one-minute spike by 82 nT. Every percentage below is against -436; against
the 1-min value the models come out proportionally worse (SWMF 61%, analytic
53%).

## Chain

| Step | Tool | Audit |
|---|---|---|
| OMNI 1-min, 8 variables | `fetch_omni` | `44d0053ebf6c` |
| resample to hourly | `resample_series` | `75f607ebee22` |
| analytic Dst + skill | `model_dst` | `aa9a2754878b` |
| SWMF 2023 RT Dst | `fetch_model_output` | `887e0b2df178` |
| SWMF to hourly | `resample_series` | `4ad8897490ce` |
| join the three | `merge_series` | `934d6434c213` |
| minima | `find_extrema` | `bca198681da1`, `31d3f99cb0c4`, `70b6a68cbbb1` |
| lagged correlation | `cross_correlate` | `376a7d132901`, `f00247ef7430` |
| residual columns | `compute_derived` | `e9417569e253`, `7b8e79f2a87d` |
| residual statistics | `describe_series` | `f89c49c5a7c4` |
| daily means | `resample_series` | `8efbf4596d36` |
| figure | `plot_timeseries` | `7cbed49a2bac` |

One step was **not** a tool call when this was first run: the SWMF CSV
carried a UTC-aware index and the OMNI CSV a naive one, `merge_series` could
not join those, and the SWMF index was localised in a one-line pandas step.
No value was altered — index bookkeeping — but it was a gap in the tool layer.

**That gap has since been closed.** `fetch_hapi` now writes naive UTC like
every other retrieve tool, and `merge_series` converts any tz-aware index to
UTC before stripping it, listing every conversion in `tz_normalized` so it is
never silent. Re-running the chain needs no hand editing and reproduces the
same values (observed minimum -436.03 nT, SWMF -308.4 nT). The manual step is
recorded here because it is what actually happened, not because it is still
required.

## 1. Minima

| | Minimum | Time | Depth vs observed | Timing error |
|---|---|---|---|---|
| Observed SYM-H | **-436.0 nT** | 05-11 02:00 | — | — |
| SWMF 2023 RT | -308.4 nT | 05-11 03:00 | **71%** | +1 h |
| O'Brien & McPherron | -272.9 nT | 05-11 04:00 | **63%** | +2 h |

Both models see a great storm and both put it in the right place. Neither
gets near the depth.

## 2. Correlation

`cross_correlate` over +/-12 h on the hourly grid:

- Analytic: **r = 0.973** at a **+1 h** lag (the model trails the measurement).
- SWMF: **r = 0.948** at **zero lag**.

`model_dst`'s own skill block (audit `aa9a2754878b`) reports corr 0.965,
RMSE 48.0 nT and a minimum error of 163.2 nT against the hourly SYM-H.

So the analytic model tracks the *shape* marginally better but is an hour
late; the MHD is in phase. Neither difference is large enough to call a
winner from one storm.

## 3. Residuals — both models are biased shallow

Residual = model - observed, so **positive means the model is not deep
enough** (audit `f89c49c5a7c4`):

| | mean | min | max |
|---|---|---|---|
| Analytic | **+27.1 nT** | -29.9 | +198.2 |
| SWMF | **+34.1 nT** | -55.9 | +219.0 |

The peak residual of ~200 nT is the main-phase underprediction visible in the
figure. The mean of +27 to +34 nT is the more interesting number, because it
says the shortfall is not confined to the peak.

## 4. The recovery phase separates them

Daily means (audit `8efbf4596d36`):

| Day | Observed | Residual, analytic | Residual, SWMF |
|---|---|---|---|
| 05-10 | -46.5 | +19.7 | -7.9 |
| 05-11 (main phase) | -295.1 | +75.5 | +71.9 |
| 05-12 | -114.9 | +26.6 | +51.2 |
| 05-13 | -70.0 | +18.8 | +40.9 |
| 05-14 | -53.3 | +29.1 | **+51.8** |

**During the main phase the two models are indistinguishable** (+75.5 vs
+71.9). They part company afterwards. The analytic model holds a roughly flat
+19 to +29 nT bias through recovery. SWMF's bias *grows*: by 05-14 it has
returned essentially to zero (-1.4 nT daily mean) while the ring current was
still at -53 nT, a +52 nT error two days after the minimum and larger than
its own error on 05-12.

Read plainly: the real-time MHD **decays its ring current too fast**. The
analytic model, whose whole content is an injection term and a
velocity-dependent decay time, sustains it better. That is a fair result for
an integral fitted to exactly this behaviour, and an unflattering one for a
first-principles simulation — but it is one storm, and one storm is an
anecdote, not a skill score.

## What this is not

- **Not a skill assessment.** One event, no baseline, no bootstrap. A real
  comparison needs many storms and the `hindcast_forecasts` treatment.
- **SWMF here is archive, not nowcast.** Every SWMF Dst run on ISWA has
  stopped — the 2023 log ended 2025-12-16 — so `allow_stale=True` was
  required. These numbers describe a run that existed in May 2024; they say
  nothing about what CCMC would produce today.
- **The two models were not driven identically.** The analytic model was fed
  the OMNI reanalysis, which is bow-shock-nose shifted and quality-controlled
  after the fact. SWMF was driven by whatever L1 data arrived in real time.
  Some of SWMF's disadvantage is that input difference, not model physics,
  and this comparison cannot separate the two.
- **A modelled Dst is not an index.** Both columns are simulations of Dst.
  Only `SYM_H` is a measurement.

## Summary

Against the hourly-averaged measurement, SWMF reached 71% of the storm depth
and the analytic model 63%, both within two hours of the right time and both
correlating above 0.94. Their main-phase errors are the same to within 4 nT.
The difference is in the recovery: the analytic model's bias stays flat while
SWMF's grows to +52 nT by 05-14, because it lets the ring current go too
early. For this storm, a two-parameter integral from 2000 beat a global MHD
simulation where it mattered least, and matched it where it mattered most.

## Reproduction record — 2026-09-04

The whole chain was re-run from `fetch_omni` after the timezone fix landed,
with no hand editing at any step, and checked value by value against what is
published above.

| Check | Result |
|---|---|
| `merge_series` conversions needed | **none** — `tz_normalized: []`, because `fetch_hapi` now writes naive UTC at source |
| Published numbers reproduced | **28 of 28**, exactly — three minima and their times, two correlations and their lags, six residual statistics, twelve daily means |
| `model_dst` skill block | corr 0.965, RMSE 48.0 nT, obs min -436.0 nT, min error 163.2 nT — unchanged |
| Merged file, all ten shared columns | **max abs difference 0.000e+00**, identical index, identical NaN pattern |
| Figure | **byte-identical** (SHA-256 `4d585626adf3b642…`) |

Re-run audit ids: `fetch_omni` `4abad982788e`, `resample_series`
`b65ad883f66d`, `model_dst` `cfa2662ba740`, `fetch_model_output`
`f020a737d85e`, `resample_series` `e25aa995f8ed`, `merge_series`
`d94d6743d636`, `plot_timeseries` `672a023cf49a`.

This shows the chain is **deterministic** and that removing the manual step
changed nothing — the hand-localised index really was bookkeeping. It does
not by itself re-verify the inputs, since the HTTP cache is content-addressed
and served them. So the cold run below was done as well.

### Cold-cache run

`workspace/cache` (160 entries, 350 MB) was moved aside, leaving an empty
cache directory, and the chain re-run in the normal `readwrite` mode so every
request had to reach the network. The cache came back with **3 entries**,
which is the proof that those requests were served remotely rather than from
disk. The directory was then restored intact.

| Check | Result |
|---|---|
| Cache state at start | **empty** (0 files) |
| Entries written during the run | 3 — the requests that actually hit the network |
| Published numbers reproduced | **28 of 28**, exactly |
| `model_dst` skill block | corr 0.965, RMSE 48.0 nT, obs min -436.0, min error 163.2 — unchanged |
| Merged file, ten shared columns | **max abs difference 0.000e+00**, identical index |
| Figure | **byte-identical**, SHA-256 `4d585626adf3b642…` |

Cold audit ids: `fetch_omni` `d529f6de8184`, `model_dst` `dcd24e45d268`,
`fetch_model_output` `9f3b7dd8df31`, `merge_series` `d5930f6bd40d`,
`plot_timeseries` `fc6f7ddfc31e`.

One thing the cold run exposed that the warm one hid: **`fetch_omni` never
used our cache at all.** CDAWeb data arrives through `cdasws`, a
library-managed transfer that the content-addressed HTTP cache does not
cover — the module docstring says so, and the timings confirm it (a warm
fetch of the same window took 3.0 s against 5.4 s cold, far too little
difference for 8641 records to have been on disk). Reproducibility for the
OMNI half therefore rests on CDAWeb serving the same reanalysis, not on a
local cache. The SWMF half is an archived run that stopped in December 2025,
so it is fixed by construction.
