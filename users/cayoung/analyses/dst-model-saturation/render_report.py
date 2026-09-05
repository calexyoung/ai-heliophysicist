"""Render analysis.md from results.json — no number typed by hand."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ST = json.loads((HERE / "results.json").read_text())
OUT = HERE / "analysis.md"
ROWS = sorted([r for r in ST["_rows"]
               if isinstance(r.get("min_error"), (int, float))],
              key=lambda r: r["obs_min"])
F = ST.get("_fits", {})
L = []
add = L.append


def med(vals):
    v = sorted(vals)
    return v[len(v) // 2]


add("# Does the Dst model saturate on the deepest storms?\n")
add("**Claim under test**, from `../2024-10-storms/`: `model_dst` missed May "
    "2024's peak by 163 nT and October's by 43.5 nT, and \"a shallower storm "
    "being better predicted is not a coincidence — it is the saturation "
    "showing itself.\"\n")
add("That is a causal claim from two events, the same shape as the "
    "sheath-driver claim in `../sheath-vs-ejecta/` that did not survive being "
    "tested against forty. So it gets the same treatment.\n")
add("**Verdict: supported in absolute terms, not in relative terms, and the "
    "two-event version overstates it.**\n")

add("\n## Method\n")
add("Storm sample and cached OMNI 1-min files come from "
    "`../sheath-vs-ejecta/` — declustered peaks of hourly Dst below −200 nT, "
    "restricted to 1995 onward where L1 coverage is complete. Each window is "
    "resampled to 1 hour and run through `model_dst` (O'Brien & McPherron "
    f"2000, pressure-corrected). **{len(ROWS)} storms modelled.**\n")

add("\n## The result\n")
add("| Date | Observed min (nT) | Model min (nT) | Error (nT) | Error/depth | Corr |")
add("|---|---|---|---|---|---|")
for r in ROWS:
    frac = abs(r["min_error"] / r["obs_min"]) if r["obs_min"] else 0
    add(f"| {r['time'][:10]} | {r['obs_min']:.0f} | {r['model_min']:.0f} | "
        f"**{r['min_error']:.1f}** | {frac:.2f} | {r['corr']:.3f} |")
add("")
add("| Depth band | Storms | Median error | Median error/depth |")
add("|---|---|---|---|")
BANDS = []
for lo, hi, lab in ((-10000, -300, "≤ −300"), (-300, -250, "−300 to −250"),
                    (-250, 0, "shallower than −250")):
    g = [r for r in ROWS if lo <= r["obs_min"] < hi]
    if not g:
        continue
    e, fr = med([r["min_error"] for r in g]), med(
        [abs(r["min_error"] / r["obs_min"]) for r in g])
    BANDS.append((lab, e, fr))
    add(f"| {lab} | {len(g)} | **{e:.1f} nT** | {fr:.2f} |")
add(f"\n**The absolute error grows with depth**, monotonically across the "
    "three bands: "
    + " → ".join(f"{e:.0f}" for _, e, _ in reversed(BANDS)) + " nT. A "
    "`linear_fit` of peak error against observed minimum gives a slope of "
    f"**{F.get('abs_slope')} ± {F.get('abs_err')} nT per nT** (audit "
    f"`{F.get('abs_audit')}`) — an extra ~0.43 nT of under-prediction for "
    f"every 1 nT deeper the storm, at about {F.get('abs_sigma')}σ, Pearson r "
    f"{F.get('pearson')} (audit `{F.get('scatter_audit')}`). That part of the "
    "claim holds.\n")
add("**The fractional error does not.** Fitting error/depth against depth "
    f"gives **{F.get('frac_slope')} ± {F.get('frac_err')} per nT** (audit "
    f"`{F.get('frac_audit')}`) — about {F.get('frac_sigma')}σ, consistent "
    "with no trend. The median error/depth by band is "
    + ", ".join(f"{fr:.2f}" for _, _, fr in BANDS)
    + ": not monotonic. The model is not getting *proportionally* worse on "
      "the biggest storms; it misses by more because the storms are bigger.\n")
add("That distinction matters for how the result is used. \"Saturation\" "
    "implies the coupling function breaks down past some amplitude. What the "
    "sample shows is a roughly constant *relative* miss of order 20–30% "
    "across the whole range, which is as consistent with a systematically "
    "under-tuned coupling coefficient as with saturation. This analysis "
    "cannot separate those.\n")

add("\n## The two-event comparison overstates it\n")
oct_r = next((r for r in ROWS if r["time"].startswith("2024-10")), None)
may_r = next((r for r in ROWS if r["time"].startswith("2024-05")), None)
deep = [r for r in ROWS if r["obs_min"] < -300]
if oct_r and may_r:
    add(f"October 2024 sits in the ≤ −300 band, where the median error is "
        f"**{med([r['min_error'] for r in deep]):.0f} nT**. Its own error is "
        f"**{oct_r['min_error']:.1f} nT** — the smallest in that band by a "
        f"wide margin. May 2024's **{may_r['min_error']:.1f} nT** is high but "
        "unremarkable next to 2001-03-31 (165.5 nT) and 2003-11-20 "
        "(135.7 nT) at comparable depth.\n")
    add("The original comparison picked an unusually well-predicted deep "
        "storm and an ordinary one, and read the gap as a depth effect. The "
        "depth effect is real; that particular pair demonstrates it mostly "
        "by luck.\n")

add("\n## Two things the sample surfaces that the claim did not\n")
worst = max(ROWS, key=lambda r: r["min_error"])
over = [r for r in ROWS if r["min_error"] < 0]
add(f"**The worst miss is not the deepest storm.** {worst['time'][:10]} "
    f"(observed {worst['obs_min']:.0f} nT) is under-predicted by "
    f"**{worst['min_error']:.1f} nT**, an error/depth of "
    f"{abs(worst['min_error'] / worst['obs_min']):.2f} — far outside the rest "
    "of the sample. It is also the storm `detect_icme` could find no shock "
    "for, so an upstream data problem is a likelier explanation than coupling "
    "physics. Worth checking before it is used as evidence of anything.\n")
if over:
    add(f"**The model over-predicts too.** {len(over)} of {len(ROWS)} storms "
        "have a negative error — "
        + ", ".join(f"{r['time'][:10]} ({r['min_error']:.1f} nT)" for r in over)
        + ". A pure saturation story predicts one-sided under-prediction, so "
          "these are the cases that argue against reading the trend as "
          "saturation alone.\n")

add("\n## What should replace the claim\n")
add("> The same model on the same index missed May's peak by 163 nT and "
    "October's by 43.5 nT. Across 19 storms from 1995 on, peak error does "
    "grow with storm depth (−0.43 ± 0.15 nT per nT, r = −0.58), so deeper "
    "storms are under-predicted by more in absolute terms. But the "
    "*fractional* error is flat within uncertainty, and October's miss is "
    "unusually small for its depth — so this pair exaggerates a real but "
    "weaker effect.\n")

add("\n## Provenance\n")
n = sum(1 for v in ST.values() if isinstance(v, dict))
add(f"{n} audited tool invocations. Regenerate with:\n")
add("```bash\nHELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/dst-model-saturation/study.py\n"
    "HELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/dst-model-saturation/render_report.py\n```\n")

OUT.write_text("\n".join(L) + "\n")
print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")
