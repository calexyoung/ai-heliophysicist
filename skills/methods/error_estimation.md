# Error Estimation
> Decide what the real uncertainty is, propagate it honestly, and admit when error bars are fiction.

## What it is / When to use it
Read before quoting any uncertainty, fitting anything, or comparing two numbers and calling them "different". Heliophysics data mixes counting statistics, calibration systematics, and irreducible definitional ambiguity — the dominant term is usually NOT the one the file gives you.

## How to use it
1. Identify the error type:
   - Counting statistics: particle detectors, photon counters. Poisson: sigma = sqrt(N) on counts. Valid only on raw counts, not on rates/fluxes already multiplied by geometry factors — convert back or scale properly.
   - Instrument/calibration uncertainty: systematic, quoted in instrument papers (often 5-20% absolute flux for particle instruments, ~0.1 nT class for magnetometers). Does not shrink with averaging.
   - Definitional/measurement-choice uncertainty: where you put the ICME boundary, which points enter the CME height-time fit. Often the biggest term; estimate by redoing the analysis with plausible alternative choices.
2. Propagation: for f(x, y) with independent errors, sigma_f^2 = (df/dx)^2 sigma_x^2 + (df/dy)^2 sigma_y^2. For ratios/products, fractional errors add in quadrature. For anything nonlinear or correlated, prefer Monte Carlo: perturb inputs by their errors, recompute, take the spread — 10 lines of numpy and hard to get wrong.
3. Bootstrap when there's no error model: resample your data points (or events) with replacement, recompute the statistic ~1000x, quote percentile intervals. Right tool for medians, correlation coefficients, fit parameters, superposed-epoch traces. Bootstrap over the independent units (events, not the autocorrelated time samples within one event).
4. Fits: report parameter uncertainties from the covariance matrix ONLY if residuals are consistent with the assumed errors (check chi^2/dof ~ 1); otherwise scale or bootstrap. `scipy.optimize.curve_fit` with `absolute_sigma=False` silently rescales — know which behavior you invoked.

## Gotchas and judgment calls
- When error bars are fiction: sqrt(N) bars on heavily processed level-2 fluxes; formal fit errors on a CME linear speed when the true uncertainty is which frames/feature you tracked (tens of percent); uncertainties on OMNI values (merged, shifted, interpolated — no per-point error exists); any error bar on a quantity with an ambiguous definition (flare end time, ICME boundary). In these cases report a spread from alternative analysis choices, or refuse to quote a number.
- Averaging N correlated samples does not reduce error by sqrt(N); use the number of independent samples (decorrelation time).
- Systematics don't average down and don't appear in scatter — two instruments agreeing to 1% can both be 15% off absolutely.
- Beware "significant" differences smaller than the calibration uncertainty between the two instruments being compared.
- Asymmetric distributions (fluxes, densities are lognormal-ish): quote median with percentile ranges, not mean ± sigma.

## Cross-checks
- Monte Carlo vs analytic propagation should agree for near-linear cases — if not, trust the Monte Carlo and find your algebra error.
- Compare your uncertainty to instrument-team published values and to the scatter between independent instruments measuring the same thing (e.g., ACE vs Wind speed: typically a few km/s to ~5%).
- Chi^2/dof far from 1 means your error model is wrong, not that the fit is great/terrible.
