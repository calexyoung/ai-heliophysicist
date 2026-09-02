"""Measure: fit, correlate, and quantify. These produce the science numbers.

Deterministic algorithms only; thresholds and definitions follow the method
skills in skills/methods/ (read those before choosing parameters).
"""

from __future__ import annotations

from helio_agent.registry import tool


def _load_csv(file: str):
    import pandas as pd
    return pd.read_csv(file, index_col="time", parse_dates=True)


def goes_class(flux_wm2: float) -> str:
    """GOES 1-8 A peak flux (W/m^2) -> flare class string (A/B/C/M/X)."""
    import math
    if flux_wm2 <= 0 or math.isnan(flux_wm2):
        return "unknown"
    for letter, base in (("X", 1e-4), ("M", 1e-5), ("C", 1e-6), ("B", 1e-7)):
        if flux_wm2 >= base:
            return f"{letter}{flux_wm2 / base:.1f}"
    return f"A{flux_wm2 / 1e-8:.1f}"


@tool(family="measure")
def find_flares(file: str, column: str = "xrsb", min_class: str = "C1.0",
                swpc_scale: bool = True) -> dict:
    """Detect flares in a GOES XRS long-channel series (SWPC-style logic).

    The series is first averaged to 1-minute cadence (the operational
    standard). A flare starts after 3 consecutive rising minutes with flux
    above min_class (SWPC uses a similar 4-minute rise test), peaks at the
    local maximum, and ends when flux decays to halfway (linear) between
    peak and pre-flare level. Returns start/peak/end and GOES class.

    swpc_scale: science-quality GOES-8..15 netcdf files carry TRUE irradiance;
    the historical/operational flare classes (and all pre-2020 literature) use
    fluxes with the SWPC scaling factor applied (XRS-B x0.7). Leave True to
    get classes comparable to the operational record; set False for GOES-R
    (16+) products already in operational scale or for true-irradiance work.
    See skills/missions/goes.md.
    """
    import numpy as np
    df = _load_csv(file)
    s = df[column].dropna().resample("1min").mean().dropna()
    if swpc_scale:
        s = s * 0.7
    if s.empty:
        return {"status": "error", "error": f"no data in column {column}"}
    base = {"A": 1e-8, "B": 1e-7, "C": 1e-6, "M": 1e-5, "X": 1e-4}
    thresh = base[min_class[0].upper()] * float(min_class[1:])
    vals, times = s.values, s.index
    flares, in_flare = [], False
    start_i = peak_i = None
    for i in range(3, len(vals)):
        rising = vals[i] > vals[i - 1] > vals[i - 2] > vals[i - 3]
        if not in_flare and rising and vals[i] >= thresh:
            in_flare = True
            j = i - 3
            while j > 0 and vals[j - 1] < vals[j]:
                j -= 1
            start_i, peak_i = j, i
        elif in_flare:
            if vals[i] > vals[peak_i]:
                peak_i = i
            else:
                half = vals[start_i] + (vals[peak_i] - vals[start_i]) / 2.0
                if vals[i] <= half:
                    flares.append((start_i, peak_i, i))
                    in_flare = False
    if in_flare:
        flares.append((start_i, peak_i, len(vals) - 1))
    out = []
    for s_i, p_i, e_i in flares:
        out.append({"start": str(times[s_i]), "peak": str(times[p_i]),
                    "end": str(times[e_i]),
                    "duration_min": round((times[e_i] - times[s_i]).total_seconds() / 60, 1),
                    "peak_flux_wm2": float(vals[p_i]),
                    "class": goes_class(float(vals[p_i]))})
    return {"n_results": len(out), "flares": out,
            "note": "cross-check against HEK (search_hek_events FL) and DONKI FLR"}


@tool(family="measure")
def find_extrema(file: str, column: str, mode: str = "min") -> dict:
    """Find the extremum of a column and when it occurred (e.g. Dst minimum)."""
    df = _load_csv(file)
    s = df[column].dropna()
    if s.empty:
        return {"status": "error", "error": f"no valid data in {column}"}
    idx = s.idxmin() if mode == "min" else s.idxmax()
    return {"column": column, "mode": mode, "value": float(s.loc[idx]),
            "time": str(idx)}


@tool(family="measure")
def storm_metrics(file: str, dst_column: str = "DST") -> dict:
    """Characterize a geomagnetic storm from a Dst/SYM-H series.

    Returns minimum Dst, its time, storm classification (NOAA-style bands:
    <-30 weak-ish threshold, -50 moderate, -100 intense, -250 extreme),
    main-phase duration (last zero-crossing before minimum -> minimum) and
    recovery estimate (time to reach half the minimum after it).
    """
    df = _load_csv(file)
    s = df[dst_column].dropna()
    if s.empty:
        return {"status": "error", "error": f"no valid data in {dst_column}"}
    tmin = s.idxmin()
    dst_min = float(s.min())
    if dst_min <= -250:
        cls = "extreme (G4-G5-like)"
    elif dst_min <= -100:
        cls = "intense"
    elif dst_min <= -50:
        cls = "moderate"
    elif dst_min <= -30:
        cls = "weak"
    else:
        cls = "no storm (Dst never below -30 nT)"
    before = s.loc[:tmin]
    onset_candidates = before[before >= 0]
    onset = onset_candidates.index[-1] if len(onset_candidates) else s.index[0]
    after = s.loc[tmin:]
    half = after[after >= dst_min / 2]
    recovery_half = half.index[0] if len(half) else None
    return {"dst_min_nT": dst_min, "time_of_min": str(tmin),
            "classification": cls,
            "main_phase_start": str(onset),
            "main_phase_hours": round((tmin - onset).total_seconds() / 3600, 1),
            "recovery_to_half_hours":
                round((recovery_half - tmin).total_seconds() / 3600, 1)
                if recovery_half is not None else None}


@tool(family="measure")
def lomb_scargle(file: str, column: str, min_period: str = "1h",
                 max_period: str = "100D", n_freq: int = 2000) -> dict:
    """Lomb-Scargle periodogram for (possibly gappy) time series.

    Returns the top 5 peaks with periods and false-alarm probabilities.
    Read skills/methods/timing_periodicity.md before interpreting.
    """
    import numpy as np
    import pandas as pd
    from astropy.timeseries import LombScargle

    df = _load_csv(file)
    s = df[column].dropna()
    t = (s.index - s.index[0]).total_seconds().values / 86400.0  # days
    y = s.values.astype(float)
    fmin = 1.0 / (pd.Timedelta(max_period).total_seconds() / 86400)
    fmax = 1.0 / (pd.Timedelta(min_period).total_seconds() / 86400)
    freq = np.linspace(fmin, fmax, n_freq)
    ls = LombScargle(t, y)
    power = ls.power(freq)
    order = np.argsort(power)[::-1]
    peaks, used = [], []
    for i in order:
        if len(peaks) >= 5:
            break
        if any(abs(freq[i] - u) < (fmax - fmin) / 100 for u in used):
            continue
        used.append(freq[i])
        peaks.append({"period_days": round(1.0 / freq[i], 4),
                      "power": round(float(power[i]), 4),
                      "false_alarm_prob": float(ls.false_alarm_probability(power[i]))})
    return {"peaks": peaks, "n_points": len(y)}


@tool(family="measure")
def cross_correlate(file: str, column_a: str, column_b: str,
                    max_lag: str = "6h") -> dict:
    """Time-lagged cross-correlation between two columns of one merged CSV.

    Positive best_lag means column_b lags column_a. Series are aligned on the
    file's cadence; NaNs pairwise-dropped per lag.
    """
    import numpy as np
    import pandas as pd
    df = _load_csv(file)
    a, b = df[column_a], df[column_b]
    cadence = (df.index[1] - df.index[0])
    nlag = int(pd.Timedelta(max_lag) / cadence)
    lags, corrs = [], []
    for k in range(-nlag, nlag + 1):
        shifted = b.shift(-k)
        mask = a.notna() & shifted.notna()
        if mask.sum() < 10:
            continue
        c = np.corrcoef(a[mask], shifted[mask])[0, 1]
        lags.append(k)
        corrs.append(c)
    if not corrs:
        return {"status": "error", "error": "not enough overlapping data"}
    best = int(np.nanargmax(np.abs(corrs)))
    return {"best_lag": str(lags[best] * cadence), "best_corr": round(float(corrs[best]), 4),
            "cadence": str(cadence), "n_lags_tested": len(lags)}


@tool(family="measure")
def superposed_epoch(file: str, column: str, epochs: list[str],
                     before: str = "2D", after: str = "5D",
                     cadence: str = "1h") -> dict:
    """Superposed epoch analysis: stack column around a list of epoch times.

    Returns median, mean, and quartiles vs epoch-relative hours. Read
    skills/methods/superposed_epoch.md for epoch selection guidance.
    """
    import numpy as np
    import pandas as pd
    df = _load_csv(file)
    s = df[column]
    rel = pd.timedelta_range(-pd.Timedelta(before), pd.Timedelta(after), freq=cadence)
    stack = []
    for ep in epochs:
        t0 = pd.Timestamp(ep)
        vals = [s.asof(t0 + dt) if (t0 + dt) >= s.index[0] else np.nan for dt in rel]
        stack.append(vals)
    arr = np.array(stack, dtype=float)
    hours = [round(dt.total_seconds() / 3600, 2) for dt in rel]
    return {"n_epochs": len(epochs),
            "epoch_hours": hours,
            "median": [None if np.isnan(v) else round(float(v), 4) for v in np.nanmedian(arr, 0)],
            "mean": [None if np.isnan(v) else round(float(v), 4) for v in np.nanmean(arr, 0)],
            "q25": [None if np.isnan(v) else round(float(v), 4) for v in np.nanpercentile(arr, 25, 0)],
            "q75": [None if np.isnan(v) else round(float(v), 4) for v in np.nanpercentile(arr, 75, 0)]}


@tool(family="measure")
def propagation_delay(solar_wind_speed_kms: float, from_x_km: float = 1.5e6,
                      to_x_km: float = 0.0) -> dict:
    """Ballistic solar-wind propagation delay between two GSE-X positions.

    Defaults: L1 (~1.5e6 km upstream) to Earth. Crude — assumes radial,
    constant speed; good to ~±10 min for steady wind. See skills/methods/cross_spacecraft.md.
    """
    if solar_wind_speed_kms <= 0:
        return {"status": "error", "error": "speed must be positive"}
    seconds = (from_x_km - to_x_km) / solar_wind_speed_kms
    return {"delay_minutes": round(seconds / 60, 1),
            "assumptions": "radial ballistic propagation at constant speed"}


@tool(family="measure")
def plasma_parameters(density_cm3: float, b_nT: float,
                      temperature_K: float | None = None,
                      ion: str = "p+") -> dict:
    """Derived plasma parameters via PlasmaPy (PyHC core package).

    Inputs: number density (cm^-3), magnetic field magnitude (nT), and
    optionally temperature (K). Returns Alfven speed, ion gyrofrequency and
    gyroradius (needs T), plasma beta (needs T), thermal speed (needs T),
    and ion inertial length. Typical slow solar wind at 1 AU:
    n~5 cm^-3, B~5 nT, T~1e5 K -> v_A ~ 49 km/s, beta ~ 0.7.
    """
    import astropy.units as u
    from plasmapy.formulary import (Alfven_speed, beta, gyrofrequency,
                                    gyroradius, inertial_length, thermal_speed)

    n = density_cm3 * u.cm ** -3
    B = b_nT * u.nT
    out: dict = {
        "alfven_speed_km_s": float(Alfven_speed(B, n, ion=ion).to_value(u.km / u.s)),
        "ion_gyrofrequency_Hz": float(gyrofrequency(B, ion, to_hz=True).to_value(u.Hz)),
        "ion_inertial_length_km": float(inertial_length(n, ion).to_value(u.km)),
    }
    if temperature_K is not None:
        T = temperature_K * u.K
        out["plasma_beta"] = float(beta(T, n, B))
        out["thermal_speed_km_s"] = float(
            thermal_speed(T, ion).to_value(u.km / u.s))
        out["ion_gyroradius_km"] = float(
            gyroradius(B, ion, T=T).to_value(u.km))
    return out


@tool(family="measure")
def linear_fit(file: str, x_column: str, y_column: str, order: int = 1) -> dict:
    """Least-squares polynomial fit y(x) with parameter uncertainties.

    Typical use: CME height-time -> linear speed (order=1) or acceleration
    (order=2). x may be 'time' to fit against seconds since series start.
    """
    import numpy as np
    df = _load_csv(file)
    if x_column == "time":
        x = (df.index - df.index[0]).total_seconds().values
    else:
        x = df[x_column].values.astype(float)
    y = df[y_column].values.astype(float)
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < order + 2:
        return {"status": "error", "error": "not enough points for fit"}
    coeffs, cov = np.polyfit(x[mask], y[mask], order, cov=True)
    errs = np.sqrt(np.diag(cov))
    resid = y[mask] - np.polyval(coeffs, x[mask])
    return {"order": order,
            "coefficients_high_to_low": [float(c) for c in coeffs],
            "uncertainties": [float(e) for e in errs],
            "rms_residual": float(np.sqrt(np.mean(resid ** 2))),
            "n_points": int(mask.sum()),
            "x_units": "seconds since start" if x_column == "time" else x_column}
