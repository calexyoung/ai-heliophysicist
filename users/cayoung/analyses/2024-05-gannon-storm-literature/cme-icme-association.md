# May 2024: which CMEs made which ejecta

From item 8 of [reading-order.md](reading-order.md), read in full:

**L** — Liu, Hu, Zhao, Chen & Wang 2024, *ApJL* 974, L8,
`arxiv_2409.11492.pdf`, "A Pileup of Coronal Mass Ejections Produced the
Largest Geomagnetic Storm in Two Decades".

This is the paper [causal-chain.md](causal-chain.md) flagged as the missing
piece: Hayakawa et al. said the ICME interplay analysis was still underway.
Every value below is L's unless tagged otherwise. Nothing was computed here.

## The source is two regions, not one

L treats the source as a single complex region: NOAA AR 13664, which appeared
on the east limb on 30 April, **merged with AR 13668**, which emerged a few
days later. They cannot be separated. It rotated over the west limb on 13 May.

## The eight full halo CMEs, deprojected

L identifies every full halo from LASCO starting 8 May and reconstructs each
with the graduated cylindrical shell (GCS) technique using **both** SOHO and
STEREO A views, so these velocities have projection effects removed.

| # | Flare | Peak (UT) | Source | CME direction | v (km/s) | Tilt | Half angle |
|---|---|---|---|---|---|---|---|
| 1 | X1.0 | May 8 05:09 | S17W09 | S14W09 | 750 | −63° | 19° |
| 2 | M8.7 | May 8 12:03 | S16W10 | S10W05 | 850 | −55° | 15° |
| 3 | X1.0 | May 8 21:40 | S18W18 | S16W07 | 1240 | −10° | 9° |
| 4 | X2.2 | May 9 09:13 | S18W23 | S12W23 | 1480 | −25° | 8° |
| 5 | X1.1 | May 9 17:44 | S15W28 | S06W26 | 940 | −3° | 10° |
| 6 | X3.9 | May 10 06:54 | S14W34 | S10W17 | 1530 | 52° | 6° |
| 7 | X5.8 | May 11 01:23 | S15W44 | S05W25 | 1660 | 58° | 36° |
| 8 | M6.6 | May 13 09:44 | S23W80 | S36W85 | 1700 | 90° | 25° |

**None of these is a fast CME.** All are below 2000 km/s. L states this
plainly: no individual eruption here was extreme.

## The association

Two ordered speed sequences do the work:

- **CMEs 1-4**: 750 → 850 → 1240 → 1480 km/s. Each is faster than the one
  ahead of it, so they converge in transit.
- **CMEs 5-7**: 940 → 1530 → 1660 km/s. Same pattern, second batch.

L's mapping, confirmed against the in situ record at Wind:

| Complex ejecta | Built from | Shock at Wind | Geoeffective? |
|---|---|---|---|
| **Complex ejecta 1** | CMEs 1-4 (8-9 May) | **16:37 UT, 10 May** | **Yes — this is the superstorm** |
| Complex ejecta 2 | CMEs 5-7 (9-11 May) | 09:09 UT, 12 May | No — only slight Dst dips in recovery |
| (neither) | CME 8 (13 May) | 19:02 UT, 15 May | Too far west, too late |

Time-elongation maps from STEREO A/HI show the tracks of the 8 May CMEs
intersecting and merging into a single bright front in HI2 — direct imaging
evidence of the interaction, not just an inference from speeds.

### Four independent confirmations that ejecta 1 is a merger

1. **Multiple temperature dips** inside the interval, indicating multiple CMEs.
2. **Four major bumps in the speed profile** rather than the monotonic decline
   of a single ICME. L reads the four bumps as CMEs 1-4, and concludes the
   **merging was still in progress at 1 AU**.
3. **Magnetic field of ~72 nT with a peak southward component of ~59 nT** —
   L calls both unusually large at 1 AU, and attributes them to the in-transit
   interaction amplifying and sustaining the field.
4. **Peak speed only ~1000 km/s** inside the ejecta. The field, not the speed,
   is what made this storm.

The second shock (12 May) propagates **into** complex ejecta 1, compressing it
further.

## Why ejecta 2 did almost nothing

Same active region, same pileup mechanism, no superstorm. L gives two reasons:

- **Field orientation.** The flux-rope tilt angle shifts from about −60° to
  about +60° across CMEs 1-7, tracking a change in B_N from predominantly
  southward inside ejecta 1 to predominantly northward inside ejecta 2. L
  cautions the tilt angles carry large uncertainty, since these are full halos
  from both viewpoints.
- **Different polarity inversion lines.** Citing Wang et al. 2024, CMEs 1-4
  and CMEs 5-7 erupted from two different PIL groups in the region; the first
  group's field distribution implies strong southward fields, the second's
  does not.
- CMEs 5-7 were also less tightly clustered in time than 1-4.

**The takeaway for forecasting:** a pileup is necessary but not sufficient.
Two pileups from one region, hours apart, differed by a factor of many in
geoeffectiveness purely on field configuration.

## The 12.6-degree experiment

STEREO A sat 0.96 AU from the Sun and **12.6° west of Earth** — a mesoscale
separation, and a rare chance to ask what the same disturbance would have done
to a differently-placed Earth.

- The first shock reached STEREO A at **14:03 UT on 10 May, 2.6 hr earlier**
  than Wind, with a generally stronger field. Consistent with the more head-on
  geometry the coronagraph reconstruction predicted (CMEs 1-4 average direction
  points nearer STEREO A than Earth).
- L models Dst from the solar wind with Burton et al. 1975 and O'Brien &
  McPherron 2000 averaged. At Earth this yields **−378 nT against the measured
  −412 nT**, 8% shallow. L treats that agreement as a calibration.
- Feeding the same model with STEREO A's field gives **−494 nT**.

**A 12.6° shift in Earth's position would have deepened the storm by roughly
120 nT.** L flags this as a lower limit and states the caveat: STEREO A's
plasma data are gappy, so they used time-shifted Wind speeds as input.

## Reconciling this with the other papers

- **Speed of the key 8 May eruption.** Hayakawa et al. report the 22:24 UT
  halo at **952 km/s** (LASCO projected). L's CME 3, the same X1.0 at 21:40 UT,
  is **1240 km/s** after GCS deprojection. Not a disagreement — a projected
  plane-of-sky speed versus a deprojected one. Cite L's when you need a
  physical speed.
- **Shock timing.** L: shock passes Wind 16:37 UT, 10 May. Hajra et al.: fast
  forward shock 16:37 UT at WIND, 17:03 UT at the bow shock nose. Hayakawa:
  arrival 17:05 UT. All consistent once you note which location is meant.
- **What L adds.** Hayakawa inferred a pileup from arrival timing and IPS.
  L supplies the actual mapping: which numbered CME went into which ejecta,
  from GCS reconstruction plus HI track merging plus in situ structure.
- **Refinement, not contradiction.** Hayakawa emphasized one CME stacking onto
  earlier ones. L's version is a four-CME merger still completing at 1 AU.

## L's framing

The event supports the "perfect storm" hypothesis (Liu et al. 2019): a
long-lived eruptive active region, successive eruptions from it, and in-transit
interaction producing exceptionally strong ejecta fields at 1 AU. L's closing
point is uncomfortable for risk estimates — **extreme events are not as rare
as we imagine**, because they do not require an extreme CME, only an ordered
sequence of ordinary ones.
