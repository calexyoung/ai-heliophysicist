# Wind
> One-line: NASA solar wind spacecraft, at L1 since 2004 (complex orbits before that), with arguably the best-calibrated long-baseline plasma and field measurements at 1 AU.

## Overview
- Launched 1994-11-01; early years included petal orbits, lunar flybys, and magnetotail passes; permanently stationed at L1 since mid-2004. NASA/GSFC.
- 30+ years of high-quality data; alongside ACE, the primary input to OMNI. When ACE SWEPAM chokes on a big event, Wind SWE usually still delivers.

## Instruments that matter
- **MFI**: magnetic field, 3 s (and higher) resolution — very well calibrated.
- **SWE**: solar wind protons/alphas (Faraday cups — robust during SEP events) and electrons.
- **3DP**: full 3D plasma and suprathermal electrons/ions (PESA/EESA/SST) — pitch-angle distributions for strahl/bidirectional-electron ICME work.
- **WAVES**: radio and plasma waves; type II/III interplanetary radio bursts; also gives electron density from quasi-thermal noise/plasma line.
- **SMS (SWICS/MASS/STICS)**: composition (partly degraded early).
- **EPACT**: energetic particles.

## Key datasets and where to get them
- CDAWeb:
  - `WI_H0_MFI` — MFI 3-sec/1-min/1-hr magnetic field (GSE/GSM).
  - `WI_H1_SWE` — SWE 92-sec proton/alpha nonlinear fit parameters; `WI_K0_SWE` for quicklook moments.
  - `WI_H5_SWE` — electron moments (verify with a cdaweb dataset search).
  - `WI_PM_3DP` — 3DP onboard proton moments (~3 s); `WI_ELPD_3DP` — electron pitch-angle distributions.
  - `WI_H1_WAV` / WAVES products for radio spectra (RAD1/RAD2/TNR).
- All coverage 1994-present (SWE electron mode changes in 2001; check variable notes).

## Analysis recipes
- **Event solar wind timeline**: `WI_H0_MFI` (1-min) + `WI_H1_SWE` protons; SWE Faraday cups keep working through intense SEP storms, so prefer Wind over ACE for extreme-event plasma moments.
- **ICME/magnetic-cloud analysis**: MFI 1-min for flux-rope rotation + `WI_ELPD_3DP` for bidirectional suprathermal electrons; minimum-variance analysis on the cloud interval for axis orientation.
- **Type II shock tracking**: WAVES RAD2/RAD1 dynamic spectrum — drift of the type II from ~MHz downward tracks the shock outward; combine with the in-situ shock arrival for average transit speed.
- **Cross-calibration anchor**: when any other L1 dataset looks weird, difference it against Wind at matched cadence.

## Gotchas and judgment calls
- Pre-2004 orbits are NOT at L1: Wind was sometimes in the magnetosphere, magnetotail, or near the Moon. Always check the spacecraft position (available in the CDFs or SSCWeb) before treating pre-2004 Wind data as pristine solar wind.
- `WI_H1_SWE` provides fit parameters (anisotropic temperatures etc.); the "K0" quicklook moments are less accurate — do not mix them in one series.
- SWE electron products changed configuration in 2001; treat electron time series across that boundary carefully.
- 3DP onboard moments (`WI_PM_3DP`) can drift in absolute calibration versus SWE; SWE is the reference for density/velocity.
- WAVES TNR-derived electron density is excellent but requires the plasma-line product, not raw spectra.
- Fill values: mask via FILLVAL attribute; SWE fits can also return unphysical values with quality flags set — filter on the quality/DQF variables.

## Validation anchors
- **1995-2020s OMNI cross-check**: pick any quiet month, load `WI_H0_MFI` + `WI_H1_SWE`, shift by the OMNI time-lag variables, and confirm agreement with OMNI values (OMNI is largely built from Wind in recent years) — validates your fill-handling and time alignment.
- **2015-03-17 St. Patrick's Day storm**: clean sheath + magnetic cloud with southward Bz ~ -25 nT in WI_H0_MFI; storm onset at Earth follows the L1 signatures by the expected convection delay.
