# Reproduction: the 2012 July 23 extreme CME at STEREO-A

**Date:** 2026-09-02 · **Method:** skills/methods/paper_reproduction.md ·
**Report:** [repro_20120723.pdf](repro_20120723.pdf)

## Papers
- Baker et al. 2013, Space Weather 11, 585 (2013SpWea..11..585B)
- Russell et al. 2013, ApJ 770, 38 (2013ApJ...770...38R)
- Cash et al. 2015, Space Weather 13, 611 (2015SpWea..13..611C)
- Temmer et al. 2015, Solar Physics 290, 919 (2015SoPh..290..919T)

## Verdicts
| Claim | Source | Computed | Verdict |
|---|---|---|---|
| STEREO-A at ~0.96 AU | Cash 2015 | 0.9641 AU | match (0.4%) |
| Arrival ~19 h after eruption | Baker 2013 | 18.3 h (02:36 launch → 20:55 shock) | match (3.6%) |
| Transit < 21 h | Cash 2015 | 18.3 h | satisfied |
| Peak B 109 nT | Russell 2013 (body, not re-read — flagged) | 109.086 nT | match (0.08%) |
| Impact speed 2246 km/s | Cash 2015 | — | **blocked at L2**: PLASTIC Vp is fill 2012-07-23 09:05 → 07-25 23:53; published speeds come from special reprocessing |

Key audit ids: fetch f1710fdc0d6c; peak-B e2987b4f79e9; Vp extremum
72f676a00e01 (post-gap value, not impact speed).

## Notes
- Data: STA_L2_MAGPLASMA_1M, 2012-07-22 → 07-27 (7200 records).
- DBM cross-check: v0=2500 km/s (DONKI), gamma=0.05e-7 → 17.7 h transit
  (0.6 h early); default drag is far too slow — the preconditioned-heliosphere
  effect (Temmer 2015) is required, and the model shows it.
- Promoted to core: nothing (all capabilities already existed); the event's
  immutable anchors became core validation case `repro20120723`, including a
  guard on the L2 plasma gap itself.
