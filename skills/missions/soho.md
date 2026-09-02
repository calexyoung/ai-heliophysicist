# SOHO (Solar and Heliospheric Observatory)
> One-line: ESA/NASA workhorse at L1 since 1996; today primarily valued for LASCO coronagraph CME imaging.

## Overview
- Launched 1995-12-02; science operations from ~1996-01 to present. Joint ESA/NASA; operated from GSFC.
- Halo orbit around Sun-Earth L1 — uninterrupted solar viewing, upstream solar wind vantage.
- Many instruments are retired or degraded; LASCO is the reason you still use SOHO daily. It remains the canonical CME catalog source spanning 2+ solar cycles.

## Instruments that matter
- **LASCO** C2 (2.2-6 Rs) and C3 (3.7-30 Rs) white-light coronagraphs: CME detection, halo CME identification, CME speed/width measurement. C1 was lost in the 1998 mission interruption.
- **EIT**: EUV imager (171/195/284/304 Å); superseded by SDO/AIA after 2010, now low cadence (synoptic only). Use for pre-2010 events.
- **MDI**: LOS magnetograms and Dopplergrams 1996-2011; superseded by HMI. Use for pre-2010 magnetic context.
- **CELIAS/SEM, ERNE, COSTEP**: solar EUV flux and energetic particles; niche use.

## Key datasets and where to get them
- **CDAW CME catalog** (cdaw.gsfc.nasa.gov/CME_list): manually curated LASCO CME list, 1996-present, with linear/quadratic speeds, position angles, widths, movies. The standard reference catalog; also CACTus (automated) at sidc.be for an independent take.
- LASCO level-0.5/1 FITS via the VSO (`Fido`, `a.Instrument("LASCO")`, detector C2/C3) or the NRL LASCO archive. C2 cadence ~12-20 min, C3 ~12-30 min (varies by era).
- EIT and MDI via VSO. MDI magnetograms: 96-min cadence full-disk.
- SOHO data also mirrored at the ESA SOHO Science Archive.
- CELIAS proton monitor and other in-situ products exist on CDAWeb — verify with a cdaweb dataset search before use; prefer ACE/Wind/DSCOVR for L1 solar wind.

## Analysis recipes
- **CME identification for an event**: query the CDAW catalog for CMEs within +-6 h of the eruption seen in AIA/EIT; check the position angle against the source region location; a "halo" (width 360) with a front-side source region is the Earth-directed candidate. Pull C2/C3 running-difference images to confirm.
- **CME speed for arrival estimates**: use the CDAW linear speed as the plane-of-sky speed; for halo CMEs this underestimates the radial speed of Earth-directed events — expect true speed higher, and don't feed plane-of-sky speed directly into a 1D arrival model without saying so.
- **Pre-2010 event context**: EIT 195 for the flare/dimming, MDI for the magnetogram, LASCO for the CME — the classic pre-SDO triad.

## Gotchas and judgment calls
- **Data gaps**: SOHO is not continuously in contact; expect regular gaps of a few hours in LASCO coverage (downlink scheduling), plus the big 1998 mission interruption (1998-06-25 to ~1998-10) and 1999 gyroscope-era gaps. A "missing CME" may just be a gap — check the catalog's data-gap listings.
- LASCO C3 has the pylon (occulter arm) blocking a sector; bright planets and stars cross the field and saturate with bleed streaks — do not mistake Venus for a CME front.
- CDAW catalog speeds are plane-of-sky, from manual point-and-click tracking; uncertainties of 10-20 percent are typical, worse for faint/halo events. Poor/fair quality flags matter.
- Halo CME detection is biased: faint Earth-directed CMEs can be missed against the bright corona; backside halos look identical to frontside ones — always confirm the source region with disk imagery.
- EIT after ~2010 runs at very low cadence; do not assume EIT coverage for late-mission events.
- SOHO roll: SOHO has performed 180-degree rolls in some eras; check CROTA-type FITS keywords rather than assuming solar north is up.

## Validation anchors
- **2003-10-28 Halloween CME**: LASCO C3 halo CME with CDAW linear speed ~2459 km/s, associated with the X17 flare (~11:10 UT); one of the fastest CMEs on record and heavily proton-snowed images.
- **2012-07-23 backside superfast CME** (STEREO-A event): appears in LASCO as a backside halo — good test that your source-region disambiguation logic works.
