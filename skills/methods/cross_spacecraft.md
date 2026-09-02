# Cross-Spacecraft Analysis
> Relate observations of the same plasma or structure at two spacecraft: lag correlation, ballistic mapping, and their limits.

## What it is / When to use it
Use when comparing time series from spacecraft at different locations — L1 monitors vs magnetospheric craft, PSP/Solar Orbiter vs 1 AU, STEREO vs Earth — to establish that they saw the same structure and to measure propagation.

## How to use it
1. Time-lagged cross-correlation: interpolate both series to a common uniform cadence (mask fill values FIRST), detrend/high-pass if a shared trend would dominate, then compute Pearson correlation as a function of lag and take the lag of the peak. Report peak correlation value and lag; a peak below ~0.5-0.6 on the fluctuation timescale of interest is weak evidence of correspondence.
2. Expected ballistic lag: for radially separated spacecraft, dt ≈ dr / Vsw using the measured solar wind speed (assume constant speed — "ballistic propagation"). L1 to Earth: ~1.5e6 km / 400 km/s ≈ 60 min; ~45 min at 550 km/s. For large radial separations (PSP at 0.2 AU to 1 AU), constant-speed ballistic mapping accumulates errors of many hours to a day.
3. Non-radial separation: solar wind structure is organized by the Parker spiral. Map each spacecraft's footpoint: source longitude ≈ observed longitude + omega * r / Vsw (omega = 14.7 deg/day sidereal, ~13.2 deg/day synodic — state which). Two spacecraft are "connected"/comparable when their ballistically back-mapped source longitudes match, not when their positions align in space.
4. Radial alignment events (spacecraft near the same Parker spiral line) are gold for studying evolution with distance; find them with SSCWeb ephemeris queries (see sscweb skill).
5. Plane-wave timing with >= 4 spacecraft (Cluster/MMS style) gives boundary normal and speed from arrival-time differences — different technique, same family; only valid when separation << structure scale.

## Gotchas and judgment calls
- Correlation lag != propagation time when the structure evolves, or when both series respond to a common driver with different response times.
- Lag ambiguity: quasi-periodic signals produce multiple correlation peaks one period apart; pick the peak consistent with the ballistic estimate, and say you did.
- Ballistic mapping ignores stream interactions: fast wind catching slow wind reshapes structures between 0.3 and 1 AU; mapped features can arrive early/late by 10+ hours and compressed.
- Latitudinal separation matters: two craft at the same longitude but different heliolatitudes can sit in different streams entirely (slow belt vs fast coronal-hole wind).
- L1 monitors are ~0.01 AU off the Sun-Earth line in Y; small-scale (< ~100 Re transverse) structures at ACE can miss Earth. This causes real forecast misses.
- Autocorrelation inflates apparent significance of correlations; if quoting significance, use an effective-N correction or bootstrap on blocks.

## Cross-checks
- Compare measured lag to the ballistic dr/Vsw prediction — agreement within ~10-20% supports the correspondence.
- Check a second variable pair (e.g., correlate density if you matched on speed) — the same lag should emerge.
- Verify geometry with SSCWeb positions before claiming alignment; verify magnetic connectivity by comparing IMF polarity (Br sign) at both craft.
