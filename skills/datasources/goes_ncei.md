# NOAA NCEI GOES Particle Archives
> The science-quality GOES proton record, in two incompatible halves: measured integral channels through 2020-03-04, and a differential-only GOES-R archive after it.

## What it is / When to use it
NCEI holds the archival GOES space-environment record. For solar energetic particles there are two eras and they are not interchangeable:

- **GOES 8-15, 1986 - 2020-03-04** — `.../goes-space-environment-monitor/access/avg/YYYY/MM/goesNN/netcdf/gNN_epead_cpflux_5m_*.nc`. Carries **measured** contamination-corrected integral channels `ZPGT1/5/10/30/50/60/100`, in East (`E`) and West (`W`) detector variants, each with a `*_QUAL_FLAG`. This is the product SWPC's historical >10 MeV numbers come from.
- **GOES 16-19, 2020 - present** — `.../goes/goesNN/l2/data/sgps-l2-avg{1m,5m}/YYYY/MM/sci_sgps-l2-avg*_gNN_dYYYYMMDD_v*.nc`. SEISS/SGPS L2 archives **13 differential channels (1.02-404 MeV) plus one >500 MeV integral channel — and nothing at >10 MeV.** SWPC computes the operational >10 MeV integral itself and publishes only a rolling 7 days of it.

So there is no archived >10 MeV integral flux anywhere for the GOES-R era. `fetch_goes_protons` reconstructs it; see `methods/sep_analysis.md`.

## How to use it
- Both trees are plain Apache directory listings — scrape `href`s to find filenames, because the GOES-R version suffix (`v3-0-2`, `v3-0-3`, …) changes and legacy monthly files are named by their actual first/last day.
- Legacy files are **netCDF-3 classic**: xarray needs `engine="scipy"`. GOES-R files are **netCDF-4/HDF5**: `engine="h5netcdf"`. Using the wrong one fails with `OSError: file signature not found`, which reads like a corrupt download but is not.
- Legacy time is `time_tag` in **milliseconds since 1970**, not a CF-decoded axis; open with `decode_times=False` and convert.
- Legacy cadence for `cpflux` is **5-minute only** — there is no 1-minute variant, whatever the sibling EPEAD products offer.
- NCEI lags real time by roughly **1 day**; SWPC's operational feed keeps 7. The overlap is where you can check a reconstruction against the operational product.

## Gotchas and judgment calls
- **The SGPS differential bands overlap and leave gaps.** Bands 3/4 overlap at 5.8-6.5 MeV and bands 8/9/10 overlap around 96-118 MeV, while 138-153, 229-267 and 390-500 MeV are unsampled. A `sum(flux_i * dE_i)` integral therefore double-counts at low energy and drops flux at high energy: measured against SWPC it runs ~1.25x high at >10 MeV and ~0.36x low at >100 MeV. Integrate a piecewise power law through the channel *effective* energies instead.
- **Do not fold the >500 MeV channel into lower thresholds.** At quiet background it is ~0.19 pfu against a total >10 MeV of ~0.25 pfu, so adding it roughly doubles the background and stops matching how SWPC defines its channels. Carry it as its own column.
- **Quiet-time >30 MeV and above are lower bounds** in any SGPS-derived integral: at background those channels are dominated by galactic cosmic rays above ~390 MeV that the differential channels do not sample, so a reconstruction runs 2-3x low. During an SEP event the solar spectrum dominates and the deficit collapses.
- **Two telescopes, and they disagree during anisotropic events.** Both eras carry oppositely-looking sensors (legacy East/West; GOES-R the -X/+X units, see the `sgps_mx_instrument_id` / `sgps_px_instrument_id` attributes — the file gives no explicit index-to-direction mapping, so do not assume one). SWPC alerts on the larger reading. During the prompt phase of a beamed event the choice matters: on 2024-05-10 GOES-16 peaked at 516 pfu and GOES-18 at 269 pfu for the same hour, while the rest of the event agreed to a few percent.
- Legacy `QUAL_FLAG` is non-zero on bad samples; drop them rather than averaging them in.
- GOES-17 has archive holes (no 2019 SGPS directory at all); GOES-19 only starts 2024. Ask for a satellite explicitly when reproducibility matters.

## Cross-checks
- Legacy >10 MeV peaks against the NOAA SWPC solar proton event list (2017-09-11: archive gives 1493 pfu at 11:45 UT, SWPC published 1490 at 11:45).
- Any GOES-R reconstruction against SWPC's operational 7-day feed on the overlapping days — and against the *other* GOES spacecraft, which is genuinely independent hardware.
- The `p_gt500` passthrough is a free plumbing check: it should match SWPC's `>=500 MeV` feed exactly, because both are the same archived channel.
