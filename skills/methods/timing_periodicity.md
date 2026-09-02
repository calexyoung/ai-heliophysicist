# Timing and Periodicity Analysis
> Find and validate periodic signals in solar and solar-wind time series, including gappy data.

## What it is / When to use it
Use when searching for or verifying periodicities: rotation modulation, cycle variations, oscillations, quasi-periodic pulsations in flares. Known periods to expect (and to treat as unsurprising when found):
- ~27 days: solar rotation as seen from Earth (synodic; sidereal ~25.4 d at equator; differential rotation spreads this).
- ~11 years: sunspot/activity cycle (~22 y magnetic Hale cycle).
- ~5 minutes (~3.3 mHz): photospheric p-modes; also common in flare QPPs.
- 1 day / 1 year and harmonics: usually artifacts of sampling, calibration, or orbit — be suspicious.

## How to use it
1. FFT prerequisites: uniform sampling, no gaps (or honestly interpolated short gaps), detrended, and windowed (Hann or similar) to control leakage. If any prerequisite fails, use Lomb-Scargle instead of force-interpolating.
2. Lomb-Scargle for gappy/uneven data: `astropy.timeseries.LombScargle(t, y).autopower()`. It handles irregular sampling natively. Use the floating-mean (default `fit_mean=True`) variant.
3. Detrending first: remove secular trends (polynomial or running-mean subtraction) before spectral analysis; a trend leaks power into all low frequencies. For flare QPP work, detrending choice can create or destroy the result — test several detrend timescales.
4. Significance: quote a false-alarm probability. astropy's `false_alarm_probability` assumes white noise; solar time series are red (power ~ 1/f^a), which makes white-noise FAPs wildly optimistic. Better: fit a red-noise (AR(1) or power-law) background and test peaks against it, or use randomization — shuffle/phase-randomize the data many times and build the null peak-height distribution.
5. Aliasing: with sampling interval dt, nothing above the Nyquist frequency 1/(2 dt) is trustworthy; regular gaps (day/night, orbit) create alias peaks at f_true ± k*f_sampling. Compute the window function spectrum to identify aliases.
6. For time-localized periodicity, use wavelet analysis (Torrence & Compo conventions) with the cone of influence marked.

## Gotchas and judgment calls
- The 27-day peak and its harmonics (13.5 d — two-sector structure, 9 d — four-sector) appear in almost every heliospheric quantity; finding them is confirmation the pipeline works, not a discovery.
- A single tall Lomb-Scargle peak in red noise is the classic false positive in this field (much QPP literature has been relitigated over exactly this). Always state the noise model behind your significance claim.
- Long-period claims need multiple cycles of data: claiming an 11-y period needs several decades; one-and-a-bit cycles is a trend, not a period.
- Leap seconds and mixed time scales (TAI vs UTC) don't matter for daily periods but do for sub-second timing; mixed timezone/UTC errors create spurious 1-day artifacts (see troubleshooting).

## Cross-checks
- Split the series and confirm the peak persists in both halves with consistent phase.
- Rerun on an independent instrument/dataset measuring the same quantity.
- Inject a synthetic sinusoid of known period/amplitude into the real noise and confirm the pipeline recovers it; inject nothing and confirm it finds nothing at your claimed significance.
