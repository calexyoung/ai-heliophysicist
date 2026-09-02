# Heliophysics Plotting Conventions
> Make plots the field recognizes: UTC time axes, labeled datasets and units, event markers, stacked panels, standard colormaps.

## What it is / When to use it
Read before producing any figure. Heliophysics has strong plotting idioms; following them makes results checkable at a glance and prevents the classic self-deceptions (timezone offsets, unlabeled units, hidden gaps).

## How to use it
- Time axis: ALWAYS UTC, labeled as such ("2024-05-10 UTC" or axis label "Time (UT)"). Force tz-aware UTC datetimes end to end; matplotlib's default local-time rendering of naive timestamps is a silent lie. Use `matplotlib.dates` locators/formatters; for multi-day plots show date at day boundaries and HH:MM between.
- Label with provenance: each panel's y-label carries quantity + units + source, e.g. "Bz GSM [nT] (OMNI_HRO_1MIN)" or "1-8 Å flux [W m^-2] (GOES-16 XRS)". Take units from the dataset metadata (CDF UNITS attribute), don't guess.
- Standard scales: X-ray flux log-scaled with horizontal A/B/C/M/X guide lines; particle fluxes log; solar wind n, T often log; B components linear and symmetric about 0 with a zero line.
- Event markers: vertical dashed lines at event times (shock arrival, flare peak, storm onset) spanning all panels of a stack, with a small annotation. Shade intervals (ICME passage, storm main phase) with translucent spans.
- Multi-panel stack plots are the field's standard product: shared x-axis, e.g. panels top-to-bottom |B|, B components, V, n, T, beta, Dst/SYM-H. Use `plt.subplots(n, 1, sharex=True)` with `hspace` near 0; only the bottom panel gets time tick labels. PyTplot `tplot()` produces these natively.
- Gaps: never line-connect across data gaps — break the line (insert NaNs at gap boundaries) or use markers, so gaps read as gaps.
- Solar imagery colormaps: use the community tables shipped in sunpy — `sdoaia171`, `sdoaia193`, `sdoaia304`, `sdoaia131`, etc. (auto-applied by `Map.plot()`); `hmimag` gray for magnetograms with symmetric limits (±~1000 G class); coronagraphs typically grayscale, running-difference images gray with symmetric stretch. These channel colors are how the field identifies wavelengths — don't substitute viridis for AIA images.
- For quantitative colormaps (spectrograms), use perceptually uniform maps (viridis/plasma), log color scale for particle flux, and ALWAYS a labeled colorbar.

## Gotchas and judgment calls
- A constant hours-offset between your plot and a published one = timezone bug, not physics (see troubleshooting).
- Autoscaling over unmasked fill values flattens everything — mask first, then plot.
- Don't smooth for display without saying so; annotate "1-hr running mean" on the panel.
- Aspect/stretch for images: AIA displays use log or asinh stretch; linear stretch hides the corona.
- Legends listing spacecraft go in consistent colors across a paper/report; note the convention you adopt.

## Cross-checks
- Compare your stack plot to CDAWeb's GUI plot or SWPC dashboards for the same interval — shapes must match.
- Recreate one published figure for a famous event as a pipeline check.
- Have the time axis print its timezone; if you can't tell from the figure alone that it's UTC, fix the figure.
