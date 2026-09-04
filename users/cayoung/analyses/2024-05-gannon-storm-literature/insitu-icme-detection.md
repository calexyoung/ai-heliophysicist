# May 2024 (Gannon) storm: what the in-situ data say

Computed 2026-09-03/04 from 1-min OMNI. Unlike
[causal-chain.md](causal-chain.md), which quotes three papers and computes
nothing, **every number in sections 1-4 below came out of a tool in this
session** and carries its audit id. Section 5 is the comparison against the
published record; the paper keys are the same ones causal-chain.md uses:

- **H** — Hayakawa et al. 2024, *ApJ*, `arxiv_2407.07665.pdf`
- **J** — Hajra, Tsurutani, Lakhina, Lu & Du 2024, *ApJ*, `arxiv_2408.14799.pdf`

## 0. Data

`fetch_omni` 1-min (`OMNI_HRO_1MIN`), 2024-05-09 to 2024-05-15, variables
F, BY_GSM, BZ_GSM, flow_speed, proton_density, T, SYM_H, Pressure —
8641 samples, audit `44d0053ebf6c`.

`solar_wind_analysis.md` says to use 1-min OMNI rather than hourly for ICME
boundaries, because hourly proton temperature inside clouds is too patchy for
the 6 h low-Tp gate. That was the right call here, but note the cost:

| Field | Valid samples | Missing |
|---|---|---|
| SYM_H | 8641 | 0 |
| F, BY_GSM, BZ_GSM | 7557 | 12.5% |
| flow_speed, proton_density, T, Pressure | 5824 | **32.6%** |

**A third of the plasma record in this window is absent.** `detect_icme`
keys on speed and temperature, so every interval boundary below is drawn
through a gappy series. Fill values are properly masked (NaN, not 9999-style
sentinels) — checked directly — so the gaps degrade resolution rather than
corrupting values, but boundary times deserve wider error bars than the
1-minute cadence suggests.

## 1. Shock, sheath, ejecta

`detect_icme` on speed + temperature, with BY/BZ for the flux-rope check and
density for the figure — audit `604e862f9a8f` (figure
`workspace/outputs/gannon_icme.png`), re-run without the plot for the
interval listing as `1daf79c2ec2f`.

**Shock: 2024-05-10 17:05 UT.**

| Structure | Start | End | Hours | Bz min | Bz median | Hours below -10 nT | Southward budget |
|---|---|---|---|---|---|---|---|
| Sheath | 05-10 17:05 | 05-11 11:31 | 18.4 | **-47.9 nT** | -24.0 nT | 13.0 | **380.1 nT·h** |
| Ejecta | 05-11 11:31 | 05-11 18:40 | 7.2 | -24.5 nT | -12.2 nT | 4.4 | 89.3 nT·h |

**Verdict: SHEATH-DRIVEN, by a factor of 4.3 in southward field budget.**
The tool's own note flags the consequence: the storm minimum may fall outside
every ICME interval, and it does — SYM-H bottoms out at 02:14 UT on 11 May,
9.3 hours *before* the first low-Tp interval begins.

## 2. The ICME train

Four qualifying low-Tp intervals, not one. Same audit `1daf79c2ec2f`.

| # | Start | End | Hours | Tp/Texp min | Mean V | Rotation | r² | Flux rope? |
|---|---|---|---|---|---|---|---|---|
| 1 | 05-11 11:31 | 05-11 18:40 | 7.2 | 0.164 | 803 km/s | 301° | 0.64 | no |
| 2 | 05-12 00:58 | 05-12 10:36 | 9.6 | 0.084 | 907 km/s | 608° | 0.63 | no |
| 3 | 05-12 20:53 | 05-14 10:16 | 37.4 | 0.104 | 657 km/s | 266° | 0.36 | no |
| 4 | 05-14 15:54 | 05-14 23:59 | 8.1 | 0.265 | 516 km/s | 165° | 0.00 | no |

Interval 2 has the coldest plasma of the event (Tp/Texp = 0.084, i.e. proton
temperature at 8% of the Lopez 1987 expectation for its speed) and the
fastest mean flow. Interval 3 is the long one, spanning a day and a half of
the recovery phase.

**No interval passes the magnetic-cloud gate.** See section 6 — this is a
limitation of the proxy, not evidence that no cloud passed.

## 3. Storm and solar-wind extremes

`storm_metrics` on SYM_H, audit `c0cea9efb47c`:

| | |
|---|---|
| SYM-H minimum | **-518.0 nT at 2024-05-11 02:14 UT** |
| Classification | extreme (G4-G5-like) |
| Main phase start | 2024-05-10 18:03 UT |
| Main phase duration | 8.2 h |
| Recovery to half-minimum | 7.5 h |

`find_extrema`, one audit each:

| Quantity | Value | Time | Audit |
|---|---|---|---|
| Speed, max | 1025.9 km/s | 05-12 01:17 | `630e5428a8a8` |
| \|B\|, max | 69.99 nT | 05-11 00:06 | `a618bedba481` |
| Bz GSM, min | -47.85 nT | 05-11 00:36 | `7455d3fbb308` |
| Density, max | 70.07 cm⁻³ | 05-11 09:42 | `2ca0895f9d58` |
| Dynamic pressure, max | 70.01 nPa | 05-11 09:42 | `c936a46532ea` |

**Read the last two differently from the rest.** The |B| maximum sits on a
smooth shoulder — the eight largest samples run 69.85 to 69.99 nT across
several minutes, which is a real plateau. The density and pressure maxima are
a *single minute* at 09:42 standing against neighbours of 20-46; both are
plausible for a compression this extreme, but quote them as a spike, and
prefer the ~60 cm⁻³ / ~60 nPa level for anything that needs a sustained value.

One curiosity worth recording: BY_GSM peaks at 69.90 nT against an |B| of
69.99 nT, so at that moment the field was almost entirely in +Y.

## 4. The radiation storm, and why its peak is suspicious

`fetch_goes_protons` (GOES-16 SGPS, 5-min, **derived** — see
`skills/datasources/goes_ncei.md`) audit `d8307d089e41`, into
`characterize_sep` audit `32205dd18a2f`:

| | |
|---|---|
| S-scale | **S2** |
| Onset | 2024-05-10 13:15 UT |
| Peak >10 MeV | 516.06 pfu at **2024-05-10 17:45 UT** |
| End | 2024-05-12 12:50 UT |
| Duration | 47.6 h |
| Hardness (>30/>10 peak) | 0.063 — soft, gradual |
| >10 MeV fluence | 8.08e6 cm⁻² sr⁻¹ |

**The peak arrives 40 minutes after the shock.** Onset is 13:15, nearly four
hours *before* the shock at 17:05, so the event begins as a normal prompt
injection — but the maximum does not land until the shock is already at the
bow shock nose. `sep_analysis.md` warns about exactly this: an energetic
storm particle (ESP) peak at shock arrival can exceed the prompt peak, and
then the ">10 MeV peak time" is the shock, not the flare.

The timing is consistent with an ESP peak, and the very soft spectrum
(hardness 0.063) fits a gradual shock-associated event rather than a
flare-rich one. **This is a hypothesis from timing alone.** Confirming it
needs the local spectral evolution and anisotropy across shock passage,
which was not computed here.

Two other caveats on this section. The fluxes are **derived**, not measured:
the GOES-R archive has no >10 MeV integral channel, so these are a piecewise
power law through the SGPS differential spectrum, agreeing with SWPC's
operational product to ~10% at >10 MeV. And `characterize_sep` reports
`n_events = 2` for this window — only the first is tabulated above.

## 5. Against the published record

The in-situ reduction lands on the papers, in some places exactly:

| Quantity | This session | Published | Agreement |
|---|---|---|---|
| SYM-H minimum | -518.0 nT at 05-11 02:14 | -518 nT at 02:14 UT (J) | exact |
| Peak southward Bz | -47.85 nT at 05-11 00:36 | Bs 47.9 nT at 00:36 UT (J) | exact |
| Shock arrival | 05-10 17:05 UT | 17:05 UT (H) | exact |
| \|B\| maximum | 69.99 nT at 05-11 00:06 | ~71 nT, wave-compressed sheath (J) | ~1.5% |
| Main phase | 8.2 h | ~9 h (J) | within an hour |
| Storm driver | sheath, 380 vs 89 nT·h | "the southward field lives in the sheaths … not in a single magnetic cloud" (J) | agrees |
| Structure | 4-interval train, no single cloud | "not one fast ICME but a complex accumulation of multiple ICMEs" (H) | agrees |

Two notes on the shock time. J lists the fast forward shock at **16:37 UT at
Wind**; H gives **17:05 UT**, and OMNI is time-shifted to the bow-shock nose,
so a ~28-minute lag from L1 is exactly what it should be. The tool reproduces
the nose time, not the Wind time — as designed, and worth stating whenever an
OMNI-derived shock time is compared against a spacecraft-frame catalog.

J also lists three further structures after the initial shock (a fast forward
*wave* at 21:40 on 10 May with M_ms 0.55, then shocks at 18:02 on 11 May and
09:08 on 12 May). `detect_icme` gates on the **first** shock in the window
only and does not attempt to find the later ones, so the correspondence
between J's structure list and the four low-Tp intervals here is suggestive,
not established. Interval 2 beginning 00:58 on 12 May sits between J's last
two entries; nothing here pins it to either.

## 6. Where the tool is wrong

**It misses the magnetic clouds.** J reports three magnetic clouds in the
recovery phase with Bs of 25-40 nT. `detect_icme` flags `magnetic_cloud:
false` on all four intervals.

The rotations are present and large — 301°, 608°, 266°, 165° — but the
smoothness test fails: r² of 0.64, 0.63, 0.36 and 0.00 against a 0.80 gate.
`solar_wind_analysis.md` already records the proxy as conservative (the
2015-03-17 St Patrick's Day cloud scores r² 0.76 on 1-min OMNI while the
literature calls it a magnetic cloud). A compound structure built from merged
ejecta is precisely the case where a single coherent clock-angle rotation
should not be expected, so the failure here is unsurprising and, arguably,
correct behaviour from a proxy that has no beta and no |B| test.

**Do not read `magnetic_cloud: false` as "no flux rope passed."** Read it as
"the rotation in this interval is not smooth enough for a proxy to call it."

## Summary

The May 2024 storm at L1, measured rather than cited: a shock at 17:05 UT on
10 May, an 18.4-hour sheath carrying Bz to -47.9 nT and 380 nT·h of southward
field, driving SYM-H to -518 nT at 02:14 on 11 May, followed by a train of
four cold-plasma intervals over the next three days, none of which is a
clean flux rope and none of which contains the storm minimum. The energy that
made this the largest storm in two decades was in the sheath, not the ejecta.

Every headline number above reproduces the published record, which is the
point of running it: the tool chain, on public data, gets the same answer as
the papers.

## Input pin

Every number above comes from one CDAWeb fetch of 1-min OMNI, and that fetch
does not pass through this repo's HTTP cache — CDAWeb data arrives via
`cdasws`, a library-managed transfer. So a reprocessing upstream would move
these values silently. `validation/run_validation.py omnipin` pins the window:
8641 records, the valid-sample counts including the 32.6% plasma gap noted
above, and the SYM-H / Bz / |B| / speed extrema with their timestamps. It
fails loudly and names this file if the reanalysis changes.
