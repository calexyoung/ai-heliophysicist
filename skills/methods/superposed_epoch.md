# Superposed Epoch Analysis
> Stack many events on a common time axis to extract the average behavior and its uncertainty.

## What it is / When to use it
Superposed epoch analysis (SEA, a.k.a. Chree analysis) aligns time series from N events at a chosen zero epoch and averages across events at each relative time. Use it to ask "what does a typical X look like?" — e.g., Dst around CIR stream interfaces, density around shocks — when individual events are noisy.

## How to use it
1. Event list: assemble epochs from a defensible catalog (your own detection, or published lists — Richardson & Cane ICMEs, SWPC flare lists, etc.). Document selection criteria; SEA conclusions are only as good as the list.
2. Zero-epoch choice matters most. Align on the physically meaningful boundary: shock arrival, stream interface, storm main-phase onset, flare peak — not just "event start" from a catalog whose start definition is fuzzy. A sloppy alignment smears sharp features into gradual ramps.
3. Window: pick pre/post durations covering the phenomenon plus quiet baseline (e.g., -2 to +4 days for ICMEs at 1 AU). Resample all events onto a common relative-time grid (be explicit about the resampling; see troubleshooting for NaN handling).
4. Central tendency: prefer the MEDIAN over the mean — solar wind and index distributions are heavy-tailed and one extreme event can dominate a mean. Show mean too if comparing with older literature. Also plot quartiles (25th/75th) to convey spread, not just the center.
5. Confidence: bootstrap over events — resample the N events with replacement, recompute the median trace, repeat ~1000x, take the 2.5/97.5 percentiles at each time bin. This gives confidence on the central trace. It does not test significance against "no effect"; for that, compare against an SEA of N random epochs drawn from the same period.
6. Optional: normalize the time axis per event (e.g., stretch each ICME to unit duration) when durations vary widely and you care about internal structure rather than absolute timing.

## Gotchas and judgment calls
- Overlapping events contaminate windows: a second shock inside another event's window belongs to both stacks. Either exclude overlaps or acknowledge them.
- Selection bias: lists built by requiring a response (e.g., "storms") then examined for the driver will show the driver by construction. Keep selection and measurement variables independent.
- Autocorrelation: adjacent time bins are not independent; don't do per-bin t-tests as if they were. Bootstrap over events handles this correctly.
- N matters: below ~20 events the median trace is jumpy and bootstrap intervals are wide; report N prominently, and report N per bin if data gaps make it vary.
- Mean vs median disagreement is itself informative — it flags skew driven by a few extreme events; look at those events individually.

## Cross-checks
- Random-epoch control: rerun with randomized epochs; your signal should vanish.
- Split-half test: divide the event list in two (odd/even, or early/late years) — a real feature appears in both halves.
- Compare against published SEA of the same phenomenon if one exists; alignment-choice differences explain most discrepancies.
