# The standing watch, in plain language

What `helio-agent monitor` does, why it is built this way, and how to read
its output without knowing the codebase. The terse operator reference is
[USAGE.md §6](USAGE.md#6-workflow-monitoring-and-forecasts); this is the
explanation behind it.

## What it is for

It watches for solar eruptions, predicts when each one will reach Earth, and
then goes back later to check whether it was right.

**The checking is the point.** Anyone can make predictions. This keeps a
permanent scorecard so you can tell whether the predictions are any good —
and so a rule change can be argued from evidence instead of intuition.

It runs once a day and remembers everything in a file between runs. There is
no background process; each run is a self-contained cycle.

## What one cycle does

Four things, in order.

**1. Reads current conditions.** How disturbed Earth's magnetic field is, and
how bright the Sun is in X-rays. This is context for a human reading the
output. Nothing else depends on it, and if these feeds fail the cycle carries
on and reports itself as `degraded` rather than failing.

**2. Looks for new eruptions.** It asks NASA's event database what was
catalogued in the last three days, skipping anything it has already seen.

For each new one it asks: *is this aimed anywhere near Earth?* If yes, a
physics model turns the eruption's launch speed into an arrival estimate plus
a range around it, and that prediction is filed as **waiting**.

An eruption pointed too far off to one side gets no prediction at all. That
is a deliberate choice: no forecast is better than a forecast that will
certainly be wrong.

**3. Grades predictions whose deadline has passed.** For each one whose time
window has fully elapsed, it asks the same database whether anything actually
arrived at Earth during that window. Something arrived → **hit**. Nothing
arrived → **miss**.

Predictions are never quietly dropped. Each one is either still waiting or
carries a permanent grade. And if the *observation* source is unavailable,
the prediction goes back to waiting rather than being scored a miss — an
outage is not evidence that nothing arrived.

**4. Notes any new geomagnetic storms.**

## How to read the output

| Field | Plain meaning |
|---|---|
| `new_cmes` | eruptions seen for the first time this cycle |
| `new_forecasts` | of those, the ones aimed near enough to Earth to predict |
| `matured` | predictions whose deadline passed this cycle, with their grades |
| `pending` | predictions still waiting for their window to close |
| `n_scored` / `hits` | the running scorecard |
| `v0_kms` | how fast the eruption was moving when launched |
| `longitude` | how far off the Sun-Earth line it was aimed, in degrees; 0 is straight at us, the sign is which side |
| `observed_arrival` | when something actually arrived, or empty if nothing did |
| `status` | `ok`, `degraded` (an optional feed failed), or `error` (a required one did) |

**The most important distinction in the whole output** is a miss with an
empty `observed_arrival`. That does not mean "we predicted Tuesday and it
came Wednesday." It means nothing showed up at all — we predicted an arrival
for something that never reached Earth. Those two failures have completely
different causes and completely different fixes.

## A worked example: why the aim test is 45 degrees

On 2026-09-04 the scorecard read **0 hits out of 3**, and all three failures
had an empty arrival time.

| Eruption | Speed | Aim | Grade |
|---|---|---|---|
| 2026-08-30 17:23 | 462 km/s | 59° off | miss |
| 2026-08-31 07:24 | 841 km/s | 48° off | miss |
| 2026-08-31 01:36 | 411 km/s | 5° off | miss |

The aim test at the time accepted anything within **60 degrees** of the
Sun-Earth line, which is generous. Two of the three were aimed 48 and 59
degrees to one side: inside the limit, but pointed well away from us, so at
best we would catch a glancing edge. The third was aimed almost straight at
us but was slow — roughly the speed of the ordinary solar wind always blowing
past Earth. Something moving at the same speed as the background does not
push through it, so there was likely nothing distinct to detect on arrival.

The filter was letting through eruptions that were never going to hit, and
each one became a wrong prediction on the scorecard.

**The fix was measured, not guessed.** `hindcast_forecasts` replays the exact
same rule over months of past data without touching the live scorecard. Over
four months it showed 45 degrees cuts false alarms by about a quarter while
covering exactly the same storms — so the cone is now 45.

**And it showed where the obvious next step would have been a disaster.**
Tightening to 30 degrees, or adding a minimum speed, looks excellent on the
month with the big storm in it. In a different month it loses the only storm
that was caught at all, because that storm came from a slow eruption aimed
well off-centre. Missing a storm costs far more than a false alarm, so the
constraint on this threshold is *not missing storms*, not precision. A
validation check now enforces exactly that; see
[`skills/methods/cme_analysis.md`](../skills/methods/cme_analysis.md).

## Things worth knowing before you trust a number

- **The scorecard can be mixed-rule.** Predictions are graded against the
  window they were issued with, so after a rule change the scorecard contains
  both old-rule and new-rule predictions until the old ones clear.
- **Quote the hit rate and the storm coverage together.** A rule can raise
  one while wrecking the other, which is the entire lesson above.
- **Some storms are not caused by eruptions at all.** A few in the historical
  record have no catalogued Earth-directed eruption behind them; they are
  most likely driven by fast solar-wind streams instead. No setting of this
  rule can catch those, so overall coverage is capped by something the
  threshold does not control.
- **Everything goes through audited tools.** A cycle can be reconstructed
  from `workspace/logs/audit.jsonl` afterwards; the monitor itself computes
  nothing.

## Running it daily

`scripts/monitor_cron.sh` wraps one cycle for a scheduler. On macOS it is
installed as a LaunchAgent (`com.helio-agent.monitor`), which has the useful
property that a run missed while the machine was asleep fires on wake. See
[USAGE.md §12](USAGE.md) for the plist and the Linux cron equivalent.

The script writes to the active user's workspace when `HELIO_AGENT_USER` is
set, and logs which profile and workspace it resolved at the top of every
cycle — so the log always answers "where did this state go".
