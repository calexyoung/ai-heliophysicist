# Are the 2024 superstorms' sheath drivers a pattern?

**Short answer: the two attributions hold, the generalisation does not.** Both 2024 superstorms are sheath-driven by both measures used here. Across every intense storm in the OMNI record the split is close to even — and the deepest storms behave differently from the merely intense ones.

This study exists because a claim was made from two events. Testing it against 40 found three defects in the tool that produced it, each of which changed the answer. Those are documented in full below, because the claim was published in two analyses before they were found.


## The sample

Declustered peaks of hourly OMNI Dst below **−200 nT**, 44.0 years of record, 48-hour declustering (audit `a8e032efa81f`; the Dst series is audit `1997611e9092`). **40 storms**, 0.909 per year.

Each storm gets OMNI 1-min over ±4 days and one `detect_icme` call. **19 of 40 produced a sheath/ejecta attribution.** The section on selection below shows that the missing half is almost entirely a data-coverage effect rather than a physical one, and restricts the sample accordingly.


## What the record shows

| Driver (by total southward nT·h) | Storms | Share |
|---|---|---|
| sheath | **10** | 53% |
| ejecta | **8** | 42% |
| ambiguous | **1** | 5% |

That is not a sheath-driven population. It is close to even — and on the 1995-onward sample, where coverage is complete, it is exactly even (see selection, below).

### But it depends strongly on how deep the storm is

| Dst range | Storms | Sheath | Ejecta | Ambiguous |
|---|---|---|---|---|
| ≤ −300 (superstorm) | 6 | **4** | 2 | 0 |
| −300 to −250 | 4 | **4** | 0 | 0 |
| −250 to −200 | 9 | **2** | 6 | 1 |

Grouped: **8 of 10 storms below −250 nT are sheath-driven, against 2 of 9 between −250 and −200.** The trend runs the way the original claim assumed — sheaths matter more at the deep end — but the claim was made about storms in general, and there it fails.

**This is not a new result and should not be presented as one.** The relative importance of sheath fields against ejecta fields, and its variation with storm intensity and cycle phase, is established:

- **Gonzalez, Walter D. et al. (1999)**, *Interplanetary origin of geomagnetic storms*, Space Science Reviews [`1999SSRv...88..529G`], 574 citations
- **Gonzalez, Walter D. et al. (2011)**, *Interplanetary Origin of Intense, Superintense and Extreme Geomagnetic Storms*, Space Science Reviews [`2011SSRv..158...69G`], 111 citations
- **Zhang, Jichun et al. (2004)**, *A statistical study of the geoeffectiveness of magnetic clouds during high solar activity years*, Journal of Geophysical Research (Space Physics) [`2004JGRA..109.9101Z`], 102 citations
- **Huttunen, K. Emilia J. et al. (2002)**, *Variability of magnetospheric storms driven by different solar wind perturbations*, Journal of Geophysical Research (Space Physics) [`2002JGRA..107.1121H`], 125 citations

(audits `f6489bc56378`, `423c35a7fa5d`.) Gonzalez et al. (2011) review exactly this question for cycle 23 and treat superintense storms (Dst ≤ −250 nT) as a separate category, which is where the split above changes. Zhang et al. (2004) find only ~30% of storms are driven by magnetic clouds. The contribution here is not the finding; it is that an automated pipeline reproduces the known trend, and that doing so exposed three bugs in the tool.


## The selection: is the missing half a bias?

21 of 40 storms produce no attribution. If that were physical — if storms whose drivers are hard to classify were systematically one kind — the split above would be meaningless. It is not physical. It is almost entirely an era effect.

| Era | Attributable | of |
|---|---|---|
| pre-1995 | **2** | 21 |
| 1995–2009 | **13** | 15 |
| 2010+ | **4** | 4 |

**Before Wind (1994) and ACE (1997), OMNI 1-min plasma is sparse — and the ejecta test needs a proton temperature series, which is exactly what is missing.** These are not storms whose drivers were ambiguous; they are storms nobody was measuring at one-minute cadence. The right response is to state the sample as what it is:

**Restricted to 1995 onward: 17 of 19 storms attributable (89%)** — no meaningful selection loss — and the split is **8 sheath, 8 ejecta, 1 ambiguous**. Dead even, on a sample that is nearly complete for its era.

The depth dependence survives the restriction:

| Dst range | Sheath | Ejecta | Ambiguous |
|---|---|---|---|
| ≤ −250 | **6** | 2 | 0 |
| −250 to −200 | **2** | 6 | 1 |

### The two modern failures are thresholds, not physics

- **2003-11-20 (−422 nT, the second-deepest storm in the record)** has an ejecta of **5.3 h against a 6 h minimum**, with a minimum Tp/Texp of 0.123. That is unambiguously an ejecta, excluded by 42 minutes.
- **2001-11-06 (−292 nT)** has a clear 50-hour ejecta but **no detected shock**, so there is no sheath to compare it against. The shock test is over-rejecting here, which is the cost of making it strict enough to reject turbulence.

### Does the answer depend on those thresholds?

The modern sample re-run under three relaxed settings:

| Setting | Sheath | Ejecta | Ambiguous | No attribution |
|---|---|---|---|---|
| baseline | **8** | 8 | 1 | 2 |
| `min_hours` 6 → 4 | **8** | 9 | 1 | 1 |
| `shock_jump_kms` 60 → 40 | **9** | 7 | 1 | 2 |
| `temp_ratio_max` 0.5 → 0.6 | **8** | 9 | 1 | 1 |

**Every variant lands within one storm of the baseline, and none produces a sheath-dominated population.** Relaxing the ejecta duration or the temperature ratio recovers one more storm and it is ejecta-driven; relaxing the shock threshold recovers one and it is sheath-driven. The even split is not an artefact of where the thresholds sit.

The depth trend is steadier still — **6 sheath against 2–3 ejecta below −250 nT under every setting tested**, against 2–3 sheath and 5–6 ejecta above it. That is the one result here robust enough to quote without qualification, and it is also the one that was already in the literature.


## How fragile the attribution is

`detect_icme` attributes by **total** southward field-time, because ring-current injection integrates VBs over time. But a total rewards duration: a long weak sheath outscores a short intense ejecta. Running the same comparison on the **rate** (mean southward Bz) changes the verdict for **9 of 19 storms**.

Only **10 of 19** agree on both measures. Those are the attributions worth trusting:

| Date | Dst (nT) | By total | By rate | Sheath h / rate | Ejecta h / rate |
|---|---|---|---|---|---|
| 1989-03-14 | -589 | sheath | ambiguous | 27.4 / 3.2 | 8.6 / 3.1 |
| 2024-05-11 | -406 | sheath | **agree** | 18.4 / 20.7 | 7.2 / 12.4 |
| 2001-03-31 | -387 | ejecta | sheath | 13.1 / 1.6 | 60.2 / 0.9 |
| 2003-10-30 | -383 | sheath | **agree** | 42.2 / 2.2 | 6.0 / 1.4 |
| 2004-11-08 | -374 | ejecta | sheath | 8.5 / 15.8 | 30.9 / 8.2 |
| 2024-10-11 | -333 | sheath | **agree** | 16.4 / 20.4 | 20.6 / 3.2 |
| 2000-07-16 | -300 | sheath | ambiguous | 18.8 / 2.1 | 6.4 / 2.0 |
| 2000-04-07 | -292 | sheath | **agree** | 13.2 / 14.3 | 24.2 / 1.0 |
| 2001-04-11 | -271 | sheath | ambiguous | 45.5 / 1.5 | 14.6 / 1.2 |
| 1991-10-29 | -254 | sheath | **agree** | 8.3 / 9.2 | 7.7 / 5.9 |
| 2005-05-15 | -247 | ejecta | sheath | 3.2 / 17.8 | 62.4 / 3.3 |
| 1999-10-22 | -237 | ejecta | **agree** | 18.6 / 0.6 | 9.5 / 16.6 |
| 2000-08-12 | -234 | ejecta | ambiguous | 11.2 / 5.3 | 41.6 / 5.0 |
| 2015-03-17 | -234 | ejecta | **agree** | 8.8 / 6.9 | 14.7 / 12.2 |
| 2001-11-24 | -221 | sheath | **agree** | 13.2 / 7.5 | 27.9 / 0.0 |
| 2023-04-24 | -213 | ejecta | ambiguous | 8.2 / 9.3 | 17.5 / 11.1 |
| 1998-09-25 | -207 | ambiguous | sheath | 6.3 / 11.7 | 16.4 / 5.5 |
| 1998-05-04 | -205 | ejecta | **agree** | 6.9 / 0.9 | 44.9 / 5.0 |
| 2000-09-17 | -201 | sheath | **agree** | 12.0 / 4.5 | 40.9 / 0.8 |

Restricted to the 10 storms where both measures agree: **7 sheath, 3 ejecta**. The picture does not change — it is still not a sheath-driven population.

`detect_icme` now reports `south_nT_per_hour` alongside the total and a `driver_by_rate` verdict beside `driver`, so a duration-weighted attribution cannot pass unnoticed again.


## The two storms that started this

| Storm | Driving shock | Sheath | Ejecta | By total | By rate |
|---|---|---|---|---|---|
| 2024-05-11 (−406 nT) | 2024-05-10 17:05 | 18.4 h, 20.62 nT/h | 7.2 h, 12.49 nT/h | **sheath** | **sheath** |
| 2024-10-11 (−333 nT) | 2024-10-10 14:13 | 16.5 h, 20.29 nT/h | 20.6 h, 3.23 nT/h | **sheath** | **sheath** |

**Both hold, on both measures.** The sheath carries roughly 1.7× (May) and 6× (October) the mean southward field of its ejecta, so neither verdict is a duration artefact.

The driving shocks land at 2024-05-10 17:05 and 2024-10-10 14:13 against DONKI's catalogued arrivals of 16:36 and 14:46 — within half an hour, from an independent detector. That agreement is the check that the sheath intervals are real.

So the individual attributions in `../2024-05-gannon-notebook-repro/` and `../2024-10-storms/` stand. **What does not stand is the sentence built on top of them** — that sheath-driving is a pattern intense storms generally follow. It is not, except at the deep end, and that was already known.


## Three defects this study found

Each was invisible on two events and obvious on forty. Each changed the answer.

**1. The sheath was bounded by the first shock in the window.** With a ±4-day window the May 2024 'sheath' ran **105.2 hours with a median Bz of +0.3 nT** — mostly quiet solar wind. Since the verdict compares totals, that interval wins by default. The sheath must be bounded by the shock that drives *its* ejecta, not by the first arrival in view.

**2. The shock test fired on turbulence.** Speed alone rising 60 km s⁻¹ above a 2-hour running minimum gave **23 'shocks'** in the May window. A fast-forward shock compresses plasma and field together, so the test now requires a sustained speed jump *and* a step up in density or |B|. May 2024 goes from 23 detections to 3.

**3. The ejecta's own leading edge was read as its driving shock.** Fixing (1) by taking the *last* shock before the ejecta picked up the discontinuity at the ejecta boundary itself: a **7-minute** sheath for May (11:24 against an 11:31 ejecta) and 43 minutes for October. Both collapsed to nothing and flipped both storms to 'ejecta-driven'. The pairing now takes the earliest shock inside a plausible sheath duration (`min_sheath_hours` 1 h, `max_sheath_hours` 48 h).

A fourth, in the offline tests rather than the tool: the planted 'sheath' fixture had **weaker field than ambient and no density compression** — physically impossible, and precisely why a speed-only shock test passed it. Corrected.

### What each fix did to the answer

| Version | May 2024 sheath | Verdict |
|---|---|---|
| Original (first shock in window) | 105.2 h, median Bz +0.3 nT | sheath — by duration |
| Last shock before ejecta | 0.1 h | ejecta |
| Earliest shock in a plausible sheath | 18.4 h, 20.7 nT/h | **sheath — by field** |

The first and third agree on the label and on nothing else. A verdict that survives three different bugs by coincidence is not evidence, which is the reason for running the check.


## Provenance

142 audited tool invocations, 140 successful. Regenerate with:

```bash
HELIO_AGENT_USER=cayoung uv run python \
  users/cayoung/analyses/sheath-vs-ejecta/study.py
HELIO_AGENT_USER=cayoung uv run python \
  users/cayoung/analyses/sheath-vs-ejecta/render_report.py
```

