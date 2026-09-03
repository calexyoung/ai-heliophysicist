# May 2024 (Gannon) storm: the causal chain

Synthesized 2026-09-03 from the first three papers in
[reading-order.md](reading-order.md), read in full:

- **H** — Hayakawa et al. 2024, *ApJ*, `arxiv_2407.07665.pdf`
- **J** — Hajra, Tsurutani, Lakhina, Lu & Du 2024, *ApJ*, `arxiv_2408.14799.pdf`
- **R** — Jarolim, Veronig, Purkhart, Zhang & Rempel 2024, *ApJ*, `arxiv_2409.08124.pdf`

Every value below is quoted from one of these three, tagged with its source.
Nothing here was computed in this session.

## 1. Flux emergence builds a super active region

AR 13664 crossed the south-eastern limb on 1 May and the central meridian on
7 May (H). It grew from 113 to 2761 millionths of the solar hemisphere between
4 and 14 May (H); R gives 110 to 2700 microhemispheres over 4-7 May and a
magnetic class of βγδ from 6 May. Major flux emergence starts 7 May (R).

R's NLFFF extrapolations (physics-informed neural network, SHARP vector
magnetograms at 12-min cadence) show magnetic energy and free magnetic energy
rising continuously with that emergence, with several high-free-energy regions
where the nonpotential field intensity exceeds 1000 G (H). The continuous
build-up dominates the global energy evolution, so free energy keeps climbing
even across the flares (R).

**Why it mattered:** H notes the peak unsigned flux and free magnetic energy
were as large as AR 12192, the largest-area region of cycle 24.

## 2. The region flares, and the flares are not the storm driver

12 X-class flares from 1-15 May, plus 52 M-class (R); soft X-ray flux stayed
continuously above M1 from 8 to 12 May (H). Largest was X8.7 on 14 May at
16:51 UT, already partly behind the west limb (H).

R quantifies each X flare as a distinct depletion of free magnetic energy
co-located with the EUV emission: most X-class flares release >10^32 erg, and
the X5.8 on 11 May reaches an upper estimate of 2.1x10^32 erg depleted. For
the X4.0 on 10 May (06:27 start, 06:54 peak) the eruption is tied to a
filament channel with a fan-spine structure at its western anchor.

**The flares are a symptom.** The geomagnetic storm is driven by the CMEs
those eruptions launched, not by the X-ray flux.

## 3. Multiple CMEs, launched into each other

LASCO recorded at least 19 major CMEs (width >= 60 deg) from 5-15 May,
including 10 halo CMEs, all from AR 13664 (H).

The critical one, H's "CME2": the halo observed at 22:24 UT on 8 May,
projected speed 952 km/s, associated with an X1.0 at 21:40 UT and an M9.8 at
22:27 UT whose eruptive features merged before reaching LASCO C2. Propagated
at constant speed it would arrive 17:33 UT on 10 May; the actual shock arrived
17:05 UT (H) — agreement far better than the usual +/-8 to +/-12 hr error bar
on CME arrival prediction.

H's interpretation of that closeness: **the preceding CMEs cleared the path.**
CME2 stacked onto CME1 and onto the two earlier halos, so later ICMEs
propagated without much deceleration. Interplanetary scintillation data from
ISEE showed large-amplitude responses spreading across the sky 8-10 May,
consistent with ICMEs accumulating and compressing the background solar wind.

H is explicit: the 10/11 May storm **is not one fast ICME** but a complex
accumulation of multiple ICMEs and southward interplanetary fields.

## 4. At L1: a shock, a sheath, and a wave that squeezes it

J resolves what actually hit, from WIND upstream:

| Time (UT) | Structure | M_ms | V_sh (km/s) | SI+ (nT) |
|---|---|---|---|---|
| 10 May 16:37 | fast forward shock | 7.15 | 386 | 88 |
| 10 May 21:40 | fast forward **wave** | 0.55 | 147 | 136 |
| 11 May 18:02 | fast forward shock | 1.46 | 106 | 39 |
| 12 May 09:08 | fast forward shock | 1.83 | 150 | 36 |

The southward field lives in the **sheaths** behind these, not in a single
magnetic cloud. J measures three intense southward intervals with peak Bs of
40.4 nT (18:06 UT, 1.6 hr), 43.4 nT (22:12 UT, 3.4 hr) and 47.9 nT (00:36 UT,
4.7 hr), with motional electric fields VBs of 28.7, 31.4 and 35.0 mV/m.

The 22:12 UT structure is the mechanism J highlights: a magnetosonic **wave**
(M_ms ~0.6, so not a shock) that compressed the sheath ahead of it to a field
magnitude of ~71 nT, deepening Bs to ~43.4 nT. Shock-sheath and wave-sheath
interaction is J's stated interplanetary cause of the main phase.

## 5. Ring current: three steps, not one

Dayside reconnection injects that energy (J). Akasofu epsilon peaks at
2.5x10^13, 3.7x10^13 and 5.1x10^13 W, matching the three Bs intervals.

SYM-H accordingly falls in three steps (J): -183 nT at 19:21 UT on 10 May,
-354 nT at 23:12 UT on 10 May, and **-518 nT at 02:14 UT on 11 May**. Main
phase ~9 hr; recovery ~2.8 days, lengthened by three magnetic clouds in the
recovery phase (Bs 25-40 nT) that added ring-current energy without deepening
the peak.

**Index caution:** H reports the storm as **Dst -412 nT** at 02 UT on 11 May,
sixth-largest since 1957. J reports **SYM-H -518 nT**. Both are right — SYM-H
is the 1-min index, Dst the hourly one, and the 1-min minimum is deeper. Quote
whichever the audience expects and say which.

The shock at 17:05 UT compressed the magnetopause to ~5.04 Earth radii (H).

## 6. Consequences, in the order they appear

- **Radiation belts (J):** after the 17:03 UT shock, 76-534 keV electrons at
  geosynchronous orbit dropped ~3 orders of magnitude, 0.9 MeV ~2 orders,
  1.5 MeV ~1 order. No significant effect on 2.0-2.9 MeV electrons.
- **Cosmic rays (H, J):** a deep Forbush decrease. J measures ~17% at Dome C
  bare and ~11% at Oulu; the decrease phase of 7-12 hr is far faster than the
  weeks-long recovery.
- **Energetic protons (H):** GLE74, ground-level enhancement from 02 to 10 UT
  on 11 May, confirmed by GOES and high-latitude neutron monitors.
- **Substorms (J):** the fast forward wave drove a supersubstorm with IL
  peaking at -2632 nT at 22:35 UT on 10 May.
- **Ionosphere (J):** afternoon TEC crest-to-trough ratio 120/40 against a
  quiet-time 60/40, with anomaly crests displaced to +/-15-45 deg latitude.
  Then in recovery, an "ionospheric hole": TEC below 20 TECU for ~8.8 hr
  against quiet values of 40-50 TECU.
- **Aurora (H):** equatorward boundary of the visual oval reconstructed to
  29.8 deg invariant latitude.
- **Ground (J):** GICs of ~30-40 A in the sub-auroral region, following the
  substorm westward electrojet rather than the storm main phase alone.

## The chain in one line

Rapid flux emergence built a βγδ region with free energy comparable to the
largest of cycle 24 → 12 X-class flares released it as at least 19 CMEs
including 10 halos → the earlier CMEs cleared the path so later ones arrived
undecelerated and piled up → the resulting compound sheaths, squeezed further
by a magnetosonic wave, held ~40-48 nT of southward field for hours → three
reconnection episodes drove SYM-H to -518 nT in three steps → belts emptied,
cosmic rays dropped, aurora reached 29.8 deg, and the grid saw 30-40 A.

**The pileup is the story.** No single CME in this sequence was extraordinary;
the ordering was.

## What these three do not cover

- Quantitative CME-ICME association. H says in-depth analyses of the ICME
  interplay were still underway at publication. **Now covered:
  [cme-icme-association.md](cme-icme-association.md)**, from Liu et al. 2024
  (`arxiv_2409.11492.pdf`), which maps each numbered halo CME onto the two
  complex ejecta observed at Wind.
- Thermosphere and satellite drag: items 15-19.
- SEP spectra: item 12 (GLE74).
