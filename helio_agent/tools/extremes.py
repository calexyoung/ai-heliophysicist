"""Extreme-value statistics: peaks-over-threshold with return periods.

Pattern from helio-agent's extreme_value skill: GPD over declustered
threshold exceedances, with closed-form method-of-moments estimation so the
result is exactly reproducible (no stochastic optimizer). The convention
sweep exists because published return periods depend heavily on threshold
and declustering choices — quantify that instead of hiding it.
"""

from __future__ import annotations

from helio_agent.registry import tool


def _decluster(times, values, threshold: float, gap_hours: float, minimize: bool):
    """Runs declustering: exceedances separated by < gap_hours form one
    event; keep each cluster's extreme. Returns (peak_times, peak_values)."""
    import numpy as np
    import pandas as pd

    exceed = values <= threshold if minimize else values >= threshold
    idx = np.flatnonzero(exceed)
    if len(idx) == 0:
        return [], []
    gap = pd.Timedelta(hours=gap_hours)
    peaks_t, peaks_v = [], []
    cluster = [idx[0]]
    for i in idx[1:]:
        if times[i] - times[cluster[-1]] < gap:
            cluster.append(i)
        else:
            vals = values[cluster]
            k = cluster[int(np.argmin(vals) if minimize else np.argmax(vals))]
            peaks_t.append(times[k])
            peaks_v.append(values[k])
            cluster = [i]
    vals = values[cluster]
    k = cluster[int(np.argmin(vals) if minimize else np.argmax(vals))]
    peaks_t.append(times[k])
    peaks_v.append(values[k])
    return peaks_t, peaks_v


def _gpd_mom(excesses):
    """Method-of-moments GPD fit (closed form, deterministic).
    Returns (shape xi, scale sigma)."""
    import numpy as np
    m, v = float(np.mean(excesses)), float(np.var(excesses, ddof=1))
    if v <= 0:
        return 0.0, m
    xi = 0.5 * (1.0 - m * m / v)
    sigma = 0.5 * m * (1.0 + m * m / v)
    return xi, sigma


@tool(family="measure")
def extreme_value(file: str, column: str, threshold: float,
                  direction: str = "min", decluster_gap_hours: float = 48.0,
                  return_periods_years: list[float] | None = None) -> dict:
    """Peaks-over-threshold GPD analysis with runs declustering.

    file/column: workspace time-series CSV (e.g. hourly Dst, daily peak
    flux). threshold: exceedance threshold in the column's units.
    direction: 'min' for negative extremes (Dst), 'max' for positive
    (flux, speed). decluster_gap_hours: exceedances closer than this are
    one event (48 h suits geomagnetic storms; use ~12 h for flares).

    Returns the GPD fit (method of moments — deterministic), the return
    level for each requested return period, and the empirical event rate.
    Run extreme_value_sweep to see how much the answer depends on these
    conventions before quoting any return period.
    """
    import numpy as np
    import pandas as pd

    if direction not in ("min", "max"):
        return {"status": "error", "error": "refusing: direction must be 'min' or 'max'"}
    df = pd.read_csv(file, index_col="time", parse_dates=True)
    if column not in df.columns:
        return {"status": "error",
                "error": f"refusing: column {column!r} not in file; "
                         f"available: {list(df.columns)}"}
    s = df[column].dropna()
    span_years = (s.index[-1] - s.index[0]).total_seconds() / (365.25 * 86400)
    if span_years < 3:
        return {"status": "error",
                "error": f"refusing: only {span_years:.1f} years of data; "
                         "extreme-value fits need years of record (>=10 to "
                         "be taken seriously)"}
    minimize = direction == "min"
    times, vals = s.index, s.values.astype(float)
    pt, pv = _decluster(times, vals, threshold, decluster_gap_hours, minimize)
    n_events = len(pv)
    if n_events < 10:
        return {"status": "error",
                "error": f"refusing: only {n_events} declustered exceedances "
                         "of the threshold; GPD needs >= 10 (relax the "
                         "threshold or extend the record)"}
    excesses = (threshold - np.array(pv)) if minimize else (np.array(pv) - threshold)
    xi, sigma = _gpd_mom(excesses)
    rate = n_events / span_years  # events per year above threshold

    def return_level(T: float) -> float:
        m = rate * T  # expected exceedances in T years
        if m <= 1:
            return float("nan")
        if abs(xi) < 1e-6:
            excess = sigma * np.log(m)
        else:
            excess = sigma / xi * (m ** xi - 1)
        return float(threshold - excess if minimize else threshold + excess)

    periods = return_periods_years or [1, 10, 50, 100]
    levels = {f"{T:g}yr": (None if np.isnan(return_level(T))
                           else round(return_level(T), 1)) for T in periods}
    return {"column": column, "direction": direction,
            "threshold": threshold, "decluster_gap_hours": decluster_gap_hours,
            "record_years": round(span_years, 1),
            "n_events": n_events, "events_per_year": round(rate, 3),
            "gpd": {"shape_xi": round(xi, 4), "scale_sigma": round(sigma, 3),
                    "estimator": "method of moments (deterministic)"},
            "return_levels": levels,
            "strongest_events": sorted(
                [{"time": str(t), "value": float(v)} for t, v in zip(pt, pv)],
                key=lambda e: e["value"], reverse=not minimize)[:5],
            "caveat": "return levels beyond ~3x the record length are "
                      "extrapolation; run extreme_value_sweep before quoting"}


@tool(family="measure")
def extreme_value_sweep(file: str, column: str, thresholds: list[float],
                        direction: str = "min",
                        decluster_gaps_hours: list[float] | None = None,
                        return_period_years: float = 100.0) -> dict:
    """Convention sweep: the same return level across threshold x declustering
    choices. A published return period is a methodological choice — this
    shows the spread you should quote as its uncertainty.
    """
    from helio_agent.registry import get_tool
    gaps = decluster_gaps_hours or [24.0, 48.0, 96.0]
    ev = get_tool("extreme_value").func
    grid = []
    for th in thresholds:
        for gap in gaps:
            r = ev(file=file, column=column, threshold=th,
                   direction=direction, decluster_gap_hours=gap,
                   return_periods_years=[return_period_years])
            level = (r.get("return_levels", {}).get(f"{return_period_years:g}yr")
                     if r.get("status", "ok") == "ok" else None)
            grid.append({"threshold": th, "gap_hours": gap,
                         "n_events": r.get("n_events"),
                         f"level_{return_period_years:g}yr": level,
                         "error": r.get("error")})
    levels = [g[f"level_{return_period_years:g}yr"] for g in grid
              if g[f"level_{return_period_years:g}yr"] is not None]
    return {"return_period_years": return_period_years, "grid": grid,
            "level_spread": {"min": min(levels), "max": max(levels)} if levels else None,
            "n_valid": len(levels),
            "note": "quote the spread, not one cell"}
