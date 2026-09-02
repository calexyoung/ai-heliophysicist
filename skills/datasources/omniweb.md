# OMNI / OMNIWeb
> Multi-source solar wind and geomagnetic-index dataset, time-shifted to Earth's bow-shock nose — the default for solar wind context at Earth.

## What it is / When to use it
OMNI (SPDF; browse at https://omniweb.gsfc.nasa.gov) merges near-Earth solar wind magnetic field and plasma data from L1 monitors (ACE, Wind, DSCOVR; historically IMP-8 and others) into a single continuous record, TIME-SHIFTED to the bow-shock nose, and bundles geomagnetic indices (Kp, Dst/SYM-H, AE) and sunspot number. Use it whenever you need "solar wind conditions at Earth" without caring which monitor provided them — storm studies, coupling functions, statistical work.

## How to use it
- Two families:
  - Low-resolution OMNI2: hourly, 1963-present. CDAWeb ID: `OMNI2_H0_MRG1HR`.
  - High-resolution OMNI (HRO): 1-min and 5-min, 1995-present. CDAWeb IDs: `OMNI_HRO_1MIN`, `OMNI_HRO_5MIN` (2nd-generation `OMNI_HRO2_*` variants also exist).
- Key variables: flow speed, proton density, proton temperature, |B|, B components in GSE and GSM (Bz_GSM is the geoeffective one), flow pressure, electric field (-V x Bz), plasma beta, Alfven Mach number, Kp, Dst or SYM-H, AE, and the spacecraft-ID flag saying which monitor supplied each record.
- Access: CDAWeb/cdasws with the IDs above, CDAWeb HAPI, pyspedas (`pyspedas.projects.omni.data(...)` — verify exact call signature for your version), or OMNIWeb's own form/FTP for ASCII.

## Gotchas and judgment calls
- Already time-shifted: OMNI timestamps are at the bow-shock nose, not L1. Do NOT add another ~45-min propagation delay; conversely, comparing OMNI to L1-native data requires shifting one of them.
- ASCII fill values are per-column sentinels (999.9, 9999.9, 9999999., etc.) — column-specific; the CDF versions use standard FILLVAL. Misread sentinels are the classic OMNI bug.
- The shift algorithm assumes phase-front propagation; during highly variable wind, 1-min OMNI has timing errors of minutes and occasional out-of-order source switching artifacts.
- Hourly OMNI2 smooths over shocks — shock parameters from hourly data are meaningless; use HRO or L1-native data.
- Source spacecraft changes mid-stream (ACE <-> Wind); small calibration offsets between sources appear as steps. The spacecraft-ID variable tells you who's talking.
- Density/temperature gaps during strong SEP events (ACE SWEPAM degradation) propagate into OMNI.
- Indices in OMNI: check whether Dst is quicklook or definitive for recent intervals.

## Cross-checks
- Compare OMNI against the underlying L1 dataset (e.g., `WI_H0_MFI`, `AC_H0_SWE`) with an explicit ballistic shift — agreement within minutes and instrument calibration is expected.
- Kp/Dst in OMNI vs GFZ/Kyoto official values for recent data.
- For a shock/ICME arrival time, verify against SYM-H sudden commencement.

## Related index sources (added 2026-09-02)
For Dst and Kp beyond OMNI's copies: `fetch_kyoto_dst` (hourly Dst by
revision - final/provisional/realtime; always cite the revision) and
`fetch_gfz_index` (GFZ, the Kp producer: Kp/ap/Ap plus 30- and 60-min
Hp30/Hp60, which are open-ended above 9 and resolve storm structure Kp
saturates on - e.g. Hp30 hit 11.3 during the 2024 Gannon storm).
