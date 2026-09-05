# Does the Dst model saturate on the deepest storms?

**Claim under test**, from `../2024-10-storms/`: `model_dst` missed May 2024's peak by 163 nT and October's by 43.5 nT, and "a shallower storm being better predicted is not a coincidence — it is the saturation showing itself."

That is a causal claim from two events, the same shape as the sheath-driver claim in `../sheath-vs-ejecta/` that did not survive being tested against forty. So it gets the same treatment.

**Verdict: supported in absolute terms, not in relative terms, and the two-event version overstates it.**


## Method

Storm sample and cached OMNI 1-min files come from `../sheath-vs-ejecta/` — declustered peaks of hourly Dst below −200 nT, restricted to 1995 onward where L1 coverage is complete. Each window is resampled to 1 hour and run through `model_dst` (O'Brien & McPherron 2000, pressure-corrected). **19 storms modelled.**


## The result

| Date | Observed min (nT) | Model min (nT) | Error (nT) | Error/depth | Corr |
|---|---|---|---|---|---|
| 2003-11-20 | -461 | -326 | **135.7** | 0.29 | 0.977 |
| 2024-05-11 | -436 | -273 | **163.2** | 0.37 | 0.969 |
| 2001-03-31 | -412 | -246 | **165.5** | 0.40 | 0.958 |
| 2004-11-08 | -379 | -291 | **88.2** | 0.23 | 0.949 |
| 2003-10-30 | -374 | -292 | **82.2** | 0.22 | 0.780 |
| 2024-10-11 | -334 | -290 | **43.5** | 0.13 | 0.921 |
| 2001-11-06 | -299 | -77 | **222.4** | 0.74 | 0.773 |
| 2000-07-16 | -296 | -350 | **-53.6** | 0.18 | 0.966 |
| 2000-04-07 | -293 | -197 | **96.1** | 0.33 | 0.970 |
| 2005-05-15 | -271 | -199 | **71.6** | 0.26 | 0.904 |
| 2001-04-11 | -246 | -167 | **79.2** | 0.32 | 0.920 |
| 2000-08-12 | -225 | -216 | **9.1** | 0.04 | 0.941 |
| 1998-05-04 | -222 | -193 | **29.3** | 0.13 | 0.930 |
| 2015-03-17 | -215 | -171 | **44.5** | 0.21 | 0.955 |
| 2023-04-24 | -214 | -225 | **-10.9** | 0.05 | 0.917 |
| 2001-11-24 | -213 | -137 | **76.7** | 0.36 | 0.940 |
| 1999-10-22 | -206 | -172 | **33.9** | 0.16 | 0.958 |
| 1998-09-25 | -196 | -176 | **19.4** | 0.10 | 0.872 |
| 2000-09-17 | -173 | -106 | **67.8** | 0.39 | 0.879 |

| Depth band | Storms | Median error | Median error/depth |
|---|---|---|---|
| ≤ −300 | 6 | **135.7 nT** | 0.29 |
| −300 to −250 | 4 | **96.1 nT** | 0.33 |
| shallower than −250 | 9 | **33.9 nT** | 0.16 |

**The absolute error grows with depth**, monotonically across the three bands: 34 → 96 → 136 nT. A `linear_fit` of peak error against observed minimum gives a slope of **-0.432 ± 0.149 nT per nT** (audit `e219187516cd`) — an extra ~0.43 nT of under-prediction for every 1 nT deeper the storm, at about 2.9σ, Pearson r -0.576 (audit `633e9ad79d55`). That part of the claim holds.

**The fractional error does not.** Fitting error/depth against depth gives **-0.00052 ± 0.00043 per nT** (audit `f582dab37efc`) — about 1.2σ, consistent with no trend. The median error/depth by band is 0.29, 0.33, 0.16: not monotonic. The model is not getting *proportionally* worse on the biggest storms; it misses by more because the storms are bigger.

That distinction matters for how the result is used. "Saturation" implies the coupling function breaks down past some amplitude. What the sample shows is a roughly constant *relative* miss of order 20–30% across the whole range, which is as consistent with a systematically under-tuned coupling coefficient as with saturation. This analysis cannot separate those.


## The two-event comparison overstates it

October 2024 sits in the ≤ −300 band, where the median error is **136 nT**. Its own error is **43.5 nT** — the smallest in that band by a wide margin. May 2024's **163.2 nT** is high but unremarkable next to 2001-03-31 (165.5 nT) and 2003-11-20 (135.7 nT) at comparable depth.

The original comparison picked an unusually well-predicted deep storm and an ordinary one, and read the gap as a depth effect. The depth effect is real; that particular pair demonstrates it mostly by luck.


## Two things the sample surfaces that the claim did not

**The worst miss is not the deepest storm.** 2001-11-06 (observed -299 nT) is under-predicted by **222.4 nT**, an error/depth of 0.74 — far outside the rest of the sample. It is also the storm `detect_icme` could find no shock for, so an upstream data problem is a likelier explanation than coupling physics. Worth checking before it is used as evidence of anything.

**The model over-predicts too.** 2 of 19 storms have a negative error — 2000-07-16 (-53.6 nT), 2023-04-24 (-10.9 nT). A pure saturation story predicts one-sided under-prediction, so these are the cases that argue against reading the trend as saturation alone.


## What should replace the claim

> The same model on the same index missed May's peak by 163 nT and October's by 43.5 nT. Across 19 storms from 1995 on, peak error does grow with storm depth (−0.43 ± 0.15 nT per nT, r = −0.58), so deeper storms are under-predicted by more in absolute terms. But the *fractional* error is flat within uncertainty, and October's miss is unusually small for its depth — so this pair exaggerates a real but weaker effect.


## Provenance

39 audited tool invocations. Regenerate with:

```bash
HELIO_AGENT_USER=cayoung uv run python \
  users/cayoung/analyses/dst-model-saturation/study.py
HELIO_AGENT_USER=cayoung uv run python \
  users/cayoung/analyses/dst-model-saturation/render_report.py
```

