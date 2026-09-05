"""ICME / magnetic-cloud interval detection at 1 AU (measure family).

Ported from helio-agent's ``analysis.detect_icme`` (v1.3.0) onto this
repo's CSV-in / dict-out contract. Method (Richardson & Cane 2010;
Burlaga et al. 1981; Lopez 1987) — see skills/methods/solar_wind_analysis.md
for the craft:

- **Low proton temperature** is the primary ICME discriminator: Tp below
  ``temp_ratio_max`` (default 0.5) of the expected temperature of normal
  wind at the same speed, Texp(V) = (0.031·V − 5.1)²·10³ K for V < 500 km/s
  and (0.51·V − 142)·10³ K above (Lopez 1987). Low-Tp samples are grouped
  into intervals (runs separated by at most ``gap_hours``, kept when at
  least ``min_hours`` long). Every qualifying interval is reported; the
  primary ICME is the FIRST, because the storm driver is whatever arrives
  first, not whatever lingers longest.
- **Shock gate**: cold *slow* wind false-positives the Tp criterion (Lopez
  overestimates Texp below ~400 km/s). When the window contains a shock
  (speed rising ``shock_jump_kms`` above the running minimum of the
  preceding ``shock_window_hours``), only intervals starting at or after
  it count and the shock time is reported.
- **Magnetic-cloud check** when BY/BZ (GSM) columns are given: enhanced
  transverse field (max √(BY²+BZ²) ≥ ``min_b_perp_nt``) and a smooth, large
  clock-angle rotation (smoothed, unwrapped angle spanning
  ≥ ``min_rotation_deg`` with a linear time fit at r² ≥ ``min_rotation_r2``).
  A flux-rope proxy, not the full Burlaga criteria (no |B|, no beta).
- **Sheath**: shock → leading ejecta, with the southward-Bz content of the
  sheath and the ejecta compared, because a sheath routinely drives a
  bigger storm than the ejecta behind it and the Dst minimum then falls
  OUTSIDE every ICME interval.
"""

from __future__ import annotations

import math

from helio_agent.registry import tool
from helio_agent.workspace import output_path

# Sheath vs ejecta southward-field ratio below which neither is called the driver.
DRIVER_MARGIN = 1.5


def expected_temperature_k(speed_kms: float) -> float:
    """Lopez (1987) expected proton temperature (K) of normal solar wind."""
    if speed_kms < 500.0:
        return (0.031 * speed_kms - 5.1) ** 2 * 1e3
    return (0.51 * speed_kms - 142.0) * 1e3


def _load_csv(file: str):
    import pandas as pd
    return pd.read_csv(file, index_col="time", parse_dates=True)


def _south_stats(field, start, end, south_bz_nt: float) -> dict | None:
    """Southward-Bz content of [start, end]; None without a field series."""
    if field is None:
        return None
    seg = field.loc[start:end].dropna()
    if len(seg) < 2:
        return None
    span_s = (seg.index[-1] - seg.index[0]).total_seconds()
    cadence_h = max(span_s / max(1, len(seg) - 1), 1.0) / 3600
    bz = seg["bz"]
    return {
        "hours": round(span_s / 3600, 1),
        "bz_min_nT": round(float(bz.min()), 1),
        "bz_median_nT": round(float(bz.median()), 1),
        "hours_below_threshold": round(int((bz < -south_bz_nt).sum()) * cadence_h, 1),
        "south_nT_hours": round(float((-bz[bz < 0]).sum()) * cadence_h, 1),
        # Mean southward Bz over the interval. The driver verdict compares
        # TOTALS, because ring-current injection integrates VBs over time —
        # but a total rewards duration, so the rate is reported beside it.
        # Where the two disagree, say so rather than quoting the label alone.
        "south_nT_per_hour": round(
            float((-bz[bz < 0]).sum()) * cadence_h / max(span_s / 3600, 1e-9), 2),
    }


def _driver(sheath: dict, ejecta: dict) -> str:
    a, b = sheath["south_nT_hours"], ejecta["south_nT_hours"]
    if max(a, b) <= 0:
        return "ambiguous"
    if a >= b * DRIVER_MARGIN:
        return "sheath"
    if b >= a * DRIVER_MARGIN:
        return "ejecta"
    return "ambiguous"


def _driver_rate(sheath: dict, ejecta: dict) -> str:
    """The same verdict on mean southward Bz instead of the integral.

    Reported beside `driver` so a duration-weighted attribution cannot pass
    unnoticed. When the two disagree the storm's sheath was long but weak
    (or short but intense), and neither label alone is the answer.
    """
    a = sheath.get("south_nT_per_hour")
    b = ejecta.get("south_nT_per_hour")
    if a is None or b is None or max(a, b) <= 0:
        return "ambiguous"
    if a >= b * DRIVER_MARGIN:
        return "sheath"
    if b >= a * DRIVER_MARGIN:
        return "ejecta"
    return "ambiguous"


def _cloud_check(interval: dict, field, min_rotation_deg: float,
                 min_rotation_r2: float, min_b_perp_nt: float,
                 smooth_minutes: float) -> None:
    import numpy as np
    seg = field.loc[interval["start"]:interval["end"]].dropna()
    if len(seg) < 5:
        return
    y, z = seg["by"].to_numpy(float), seg["bz"].to_numpy(float)
    b_perp = np.hypot(y, z)
    cadence_s = max((seg.index[-1] - seg.index[0]).total_seconds() / max(1, len(seg) - 1), 1.0)
    # boxcar-smooth the components before the angle so high-cadence noise
    # cannot fake (or unwrap into) extra rotation
    width = max(1, int(round(smooth_minutes * 60 / cadence_s)))
    kernel = np.ones(width) / width
    y_s = np.convolve(y, kernel, mode="valid")
    z_s = np.convolve(z, kernel, mode="valid")
    theta = np.degrees(np.unwrap(np.arctan2(y_s, z_s)))
    seconds = np.arange(len(theta)) * cadence_s
    rotation = float(theta.max() - theta.min())
    r2 = 0.0
    if len(theta) >= 2 and theta.std() > 0:
        slope, intercept = np.polyfit(seconds, theta, 1)
        pred = slope * seconds + intercept
        r2 = float(1.0 - ((theta - pred) ** 2).sum() / ((theta - theta.mean()) ** 2).sum())
    interval["rotation_deg"] = round(rotation, 1)
    interval["rotation_r2"] = round(r2, 3)
    interval["max_b_perp_nT"] = round(float(b_perp.max()), 2)
    interval["magnetic_cloud"] = bool(
        rotation >= min_rotation_deg and r2 >= min_rotation_r2
        and interval["max_b_perp_nT"] >= min_b_perp_nt)


@tool(family="measure")
def detect_icme(file: str, speed_column: str, temperature_column: str,
                by_column: str | None = None, bz_column: str | None = None,
                density_column: str | None = None,
                temp_ratio_max: float = 0.5, min_hours: float = 6.0,
                gap_hours: float = 2.0, min_rotation_deg: float = 90.0,
                min_rotation_r2: float = 0.8, min_b_perp_nt: float = 8.0,
                smooth_minutes: float = 30.0, shock_jump_kms: float = 60.0,
                shock_window_hours: float = 2.0, south_bz_nt: float = 10.0,
                min_sheath_hours: float = 1.0, max_sheath_hours: float = 48.0,
                plot: bool = True, out_name: str = "icme.png") -> dict:
    """Detect ICME intervals in a solar-wind CSV via the low-proton-temperature
    signature (Tp < temp_ratio_max · Texp(V), Lopez 1987), gated by the first
    shock in the window, with a magnetic-cloud check when BY/BZ (GSM, nT) are
    given and a sheath / driver attribution.

    file: workspace CSV with a 'time' index (e.g. from fetch_omni). Speed in
    km/s, temperature in K (OMNI: V1800/T1800 hourly, flow_speed/T 1-min).

    Returns icme (the FIRST qualifying interval — the storm driver, or null),
    intervals (all, in time order), shock_time, sheath, ejecta_field, driver
    ("sheath" | "ejecta" | "ambiguous" | null), closest (near-miss diagnostics
    when nothing qualified), note, and the diagnostic figure path when plot.

    Hourly OMNI temperature is patchy inside clouds; prefer 1-min OMNI or
    Wind/ACE data for interval boundaries, and treat hourly results with
    min_hours relaxed as indicative only.
    """
    import numpy as np
    import pandas as pd

    df = _load_csv(file)
    for col in (speed_column, temperature_column, by_column, bz_column, density_column):
        if col is not None and col not in df.columns:
            return {"status": "error",
                    "error": f"column {col!r} not in {file}; available: {list(df.columns)}"}
    if (by_column is None) != (bz_column is None):
        return {"status": "error",
                "error": "give both by_column and bz_column (GSM, nT) or neither"}
    speed = df[speed_column].astype(float)
    temp = df[temperature_column].astype(float)
    valid = speed.notna() & temp.notna() & (temp > 0)
    if not valid.any():
        return {"status": "error",
                "error": f"no rows with both {speed_column} and {temperature_column} valid"}
    texp = speed.map(lambda v: expected_temperature_k(v) if not math.isnan(v) else math.nan)
    ratio = (temp / texp).where(valid)

    # Shocks: every sample rising shock_jump_kms above the running minimum of
    # the preceding window, with a refractory period so one steep front is
    # not counted many times.
    #
    # ALL of them, not just the first. Taking the first shock and calling
    # everything up to the ejecta "the sheath" is wrong whenever the window
    # holds an earlier, unrelated arrival: on a +/-4 day window around the
    # May 2024 superstorm that produced a 105-hour "sheath" with a median Bz
    # of +0.3 nT — mostly quiet solar wind, and long enough to win any
    # duration-weighted comparison by default. The sheath is bounded by the
    # LAST shock before the ejecta, which is the one that drives it.
    # A fast-forward shock jumps speed, density AND field together, and the
    # jump is SUSTAINED. Testing speed alone against a running minimum fires
    # on ordinary turbulence: on the May 2024 window that gave 23 "shocks",
    # so "the last shock before the ejecta" landed 0.8 h before it, inside
    # the sheath rather than at its leading edge. Compare medians either
    # side of a candidate and require all three to step up.
    shocks: list = []
    s = speed.dropna()
    win = pd.Timedelta(hours=shock_window_hours)
    dens = (df[density_column].astype(float)
            if density_column and density_column in df.columns else None)
    bmag = None
    if by_column in df.columns and bz_column in df.columns:
        bmag = (df[by_column].astype(float) ** 2
                + df[bz_column].astype(float) ** 2) ** 0.5
    for i in range(1, len(s)):
        t = s.index[i]
        if shocks and (t - shocks[-1]) < pd.Timedelta(hours=6):
            continue
        before = s.loc[t - win:t].iloc[:-1]
        after = s.loc[t:t + win]
        if len(before) < 2 or len(after) < 2:
            continue
        # The sample AT t must itself already be elevated, or the median
        # window flags the point one cadence step BEFORE the jump.
        base = float(before.median())
        if float(s.iloc[i]) - base < shock_jump_kms:
            continue
        if float(after.median()) - base < shock_jump_kms:
            continue
        # A fast-forward shock compresses the plasma AND the field. Requiring
        # at least one of density or |B| to step up with the speed is what
        # separates a shock from ordinary turbulence: on May 2024 the speed
        # test alone fired 23 times, the combined test 3 (and its leading one
        # lands 19 min from the DONKI-catalogued arrival).
        compressed = False
        for extra in (dens, bmag):
            if extra is None:
                continue
            b = extra.loc[t - win:t].iloc[:-1].dropna()
            a = extra.loc[t:t + win].dropna()
            if len(b) < 2 or len(a) < 2 or float(b.median()) <= 0:
                continue
            if float(a.median()) > float(b.median()) * 1.2:
                compressed = True
                break
        ok_extra = compressed or (dens is None and bmag is None)
        if ok_extra:
            shocks.append(t)
    shock_time = shocks[0] if shocks else None

    # group low-Tp samples into intervals, merging across gaps
    low = ratio[ratio < temp_ratio_max].index
    raw: list[list] = []
    gap = pd.Timedelta(hours=gap_hours)
    for t in low:
        if raw and t - raw[-1][1] <= gap:
            raw[-1][1] = t
        else:
            raw.append([t, t])
    min_len = pd.Timedelta(hours=min_hours)
    qualifying = [(a, b) for a, b in raw if b - a >= min_len]
    pre_shock = 0
    if shock_time is not None:
        pre_shock = sum(1 for a, _ in qualifying if a < shock_time)
        qualifying = [(a, b) for a, b in qualifying if a >= shock_time]

    closest = None
    if not qualifying:
        cands = [(a, b) for a, b in raw if shock_time is None or a >= shock_time]
        after = ratio.dropna()
        if shock_time is not None:
            after = after.loc[shock_time:]
        lowest = round(float(after.min()), 3) if len(after) else None
        if cands:
            a, b = max(cands, key=lambda ab: ab[1] - ab[0])
            hours = (b - a).total_seconds() / 3600
            closest = {"start": str(a), "end": str(b), "duration_hours": round(hours, 1),
                       "hours_short": round(min_hours - hours, 1),
                       "min_temp_ratio": lowest, "ratio_short": None}
        else:
            closest = {"start": None, "end": None, "duration_hours": 0.0,
                       "hours_short": min_hours, "min_temp_ratio": lowest,
                       "ratio_short": round(lowest - temp_ratio_max, 3)
                       if lowest is not None else None}

    field = None
    if by_column is not None:
        field = pd.DataFrame({"by": df[by_column].astype(float),
                              "bz": df[bz_column].astype(float)}).dropna()
        if field.empty:
            field = None

    intervals = []
    for a, b in qualifying:
        r = ratio.loc[a:b].dropna()
        iv = {"start": str(a), "end": str(b),
              "duration_hours": round((b - a).total_seconds() / 3600, 1),
              "min_temp_ratio": round(float(r.min()), 3),
              "mean_speed_kms": round(float(speed.loc[r.index].mean()), 1),
              "magnetic_cloud": None, "rotation_deg": None,
              "rotation_r2": None, "max_b_perp_nT": None}
        if field is not None:
            _cloud_check(iv, field, min_rotation_deg, min_rotation_r2,
                         min_b_perp_nt, smooth_minutes)
        intervals.append(iv)
    icme = intervals[0] if intervals else None

    sheath = ejecta_field = driver = None
    # Pair the ejecta with the shock that actually drives it: the EARLIEST
    # shock inside a physically plausible sheath duration before it.
    #
    # Not the last one. An ejecta has its own leading-edge discontinuity that
    # trips the shock test minutes ahead of the interval start — on May 2024
    # that put the "sheath" at 7 minutes (11:24 against an 11:31 ejecta),
    # and October at 43 minutes, collapsing both sheaths to nothing and
    # flipping the attribution. min_sheath_hours discards those; the earliest
    # qualifying shock is the leading edge of the disturbed region.
    driving_shock = None
    if icme is not None and shocks:
        t0 = pd.Timestamp(icme["start"])
        window = [t for t in shocks
                  if pd.Timedelta(hours=min_sheath_hours)
                  <= (t0 - t) <= pd.Timedelta(hours=max_sheath_hours)]
        if window:
            driving_shock = window[0]
    if driving_shock is None:
        driving_shock = shock_time

    if driving_shock is not None and icme is not None:
        sheath_end = pd.Timestamp(icme["start"])
        sheath = {"start": str(driving_shock), "end": str(sheath_end),
                  "duration_hours": round((sheath_end - driving_shock).total_seconds() / 3600, 1),
                  "field": _south_stats(field, driving_shock, sheath_end, south_bz_nt)}
        ejecta_field = _south_stats(field, pd.Timestamp(icme["start"]),
                                    pd.Timestamp(icme["end"]), south_bz_nt)
        if sheath["field"] is not None and ejecta_field is not None:
            driver = _driver(sheath["field"], ejecta_field)

    # note
    if icme is None:
        gate = f"Tp < {temp_ratio_max:g}·Texp lasting {min_hours:g}+ h"
        if closest and closest["start"] is not None:
            how = (f"; closest: {closest['duration_hours']:g} h below the ratio from "
                   f"{closest['start']} ({closest['hours_short']:g} h short; lowest "
                   f"Tp/Texp {closest['min_temp_ratio']})")
        elif closest and closest["min_temp_ratio"] is not None:
            how = (f"; no sample fell below the ratio — the lowest Tp/Texp after the "
                   f"shock was {closest['min_temp_ratio']} ({closest['ratio_short']:+g} above it)")
        else:
            how = ""
        note = f"no interval with {gate}{how} — no ICME signature in this window"
    else:
        if icme["magnetic_cloud"] is None:
            cloud = "no BY/BZ given — magnetic-cloud check skipped"
        elif icme["magnetic_cloud"]:
            cloud = (f"magnetic cloud: {icme['rotation_deg']:g}° smooth rotation "
                     f"(r²={icme['rotation_r2']:g}), max B⊥ {icme['max_b_perp_nT']:g} nT")
        else:
            cloud = (f"no flux-rope signature (rotation {icme['rotation_deg']:g}° at "
                     f"r²={icme['rotation_r2']:g}, max B⊥ {icme['max_b_perp_nT']:g} nT)")
        extra = (f"; first of {len(intervals)} qualifying intervals — an ICME train follows"
                 if len(intervals) > 1 else "")
        note = f"low-Tp interval of {icme['duration_hours']:g} h; {cloud}{extra}"
    if shock_time is not None:
        note = f"shock {shock_time}; {note}"
    if sheath is not None:
        text = f"sheath {sheath['duration_hours']:g} h"
        f = sheath["field"]
        if f is not None:
            text += (f" carrying Bz to {f['bz_min_nT']:g} nT "
                     f"({f['hours_below_threshold']:g} h below -{south_bz_nt:g})")
            if driver == "sheath":
                text += (f" — SHEATH-DRIVEN: {f['south_nT_hours']:g} vs "
                         f"{ejecta_field['south_nT_hours']:g} nT·h southward, so the storm "
                         "minimum may fall outside every ICME interval")
            elif driver == "ejecta":
                text += (f" — ejecta-driven: {ejecta_field['south_nT_hours']:g} vs "
                         f"{f['south_nT_hours']:g} nT·h southward")
            elif driver == "ambiguous":
                text += (f" — driver ambiguous: {f['south_nT_hours']:g} (sheath) vs "
                         f"{ejecta_field['south_nT_hours']:g} (ejecta) nT·h southward")
        note += f"; {text}"
    if pre_shock:
        note += f"; {pre_shock} pre-shock cold-slow-wind interval(s) ignored"

    out = {"icme": icme, "closest": closest, "intervals": intervals,
           "n_intervals": len(intervals),
           "shock_time": str(shock_time) if shock_time is not None else None,
           "sheath": sheath, "ejecta_field": ejecta_field, "driver": driver,
           "driver_by_rate": (_driver_rate(sheath["field"], ejecta_field)
                              if sheath and sheath.get("field") and ejecta_field
                              else None),
           "shock_times": [str(t) for t in shocks],
           "method": "Tp/Texp(V) (Lopez 1987) intervals, shock-gated; clock-angle "
                     "flux-rope proxy (Burlaga et al. 1981); Richardson & Cane 2010",
           "note": note}
    if plot:
        out["file"] = _plot(df, speed_column, temperature_column, texp, ratio,
                            density_column, field, intervals, shock_time, out_name)
        out["artifacts"] = [out["file"]]
    return out


def _plot(df, speed_column, temperature_column, texp, ratio, density_column,
          field, intervals, shock_time, out_name) -> str:
    import numpy as np
    from helio_agent.style import EVENT_COLOR, PALETTE, NEUTRAL, apply_style, figsize
    apply_style()
    import matplotlib.pyplot as plt

    n = 3 + (field is not None)
    w, _ = figsize("page")
    fig, axes = plt.subplots(n, 1, figsize=(w, 1.5 * n + 0.6), sharex=True)
    axes[0].plot(df.index, df[speed_column], lw=1.0, color=PALETTE[0])
    axes[0].set_ylabel("V (km s$^{-1}$)")
    if density_column:
        tw = axes[0].twinx()
        tw.plot(df.index, df[density_column], lw=0.7, color=PALETTE[3], alpha=0.8)
        tw.set_ylabel("n (cm$^{-3}$)", color=PALETTE[3])
    axes[1].plot(df.index, df[temperature_column], lw=1.0, color=PALETTE[1], label="$T_p$")
    axes[1].plot(df.index, texp, lw=0.9, ls="--", color=NEUTRAL, label="$T_{exp}(V)$")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("T (K)")
    axes[1].legend(loc="upper right")
    axes[2].plot(df.index, ratio, lw=0.9, color=PALETTE[2])
    axes[2].axhline(1.0, color=NEUTRAL, lw=0.6)
    axes[2].set_yscale("log")
    axes[2].set_ylabel("$T_p/T_{exp}$")
    if field is not None:
        ax = axes[3]
        ax.plot(field.index, np.hypot(field["by"], field["bz"]), lw=0.9,
                color=PALETTE[4], label="$B_\\perp$")
        ax.set_ylabel("$B_\\perp$ (nT)")
        tw = ax.twinx()
        tw.plot(field.index, np.degrees(np.arctan2(field["by"], field["bz"])),
                lw=0.5, alpha=0.7, color=PALETTE[5])
        tw.set_ylabel("clock angle (°)", color=PALETTE[5])
    for ax in axes:
        if shock_time is not None:
            ax.axvline(shock_time, color=EVENT_COLOR, ls="--", lw=0.9, alpha=0.85)
        for k, iv in enumerate(intervals):
            import pandas as pd
            ax.axvspan(pd.Timestamp(iv["start"]), pd.Timestamp(iv["end"]),
                       color=PALETTE[0], alpha=0.15 if k == 0 else 0.07, lw=0)
    title = "ICME detection" + (f" — {len(intervals)} low-$T_p$ interval(s)"
                                if intervals else " — none found")
    if shock_time is not None:
        axes[0].annotate("shock", xy=(shock_time, 1.0), xycoords=("data", "axes fraction"),
                         rotation=90, va="top", ha="right", fontsize=7, color=EVENT_COLOR)
    axes[0].set_title(title)
    axes[-1].set_xlabel("Time (UTC)")
    fig.autofmt_xdate()
    fig.align_ylabels(axes)
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)
