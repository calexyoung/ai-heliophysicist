"""Solar energetic particle (SEP) event characterization (measure family).

Ported from helio-agent's ``analysis.characterize_sep`` (v1.2.0) onto this
repo's CSV-in / dict-out contract. See skills/methods/sep_analysis.md for
the craft.

Following the NOAA definition, an SEP event (radiation storm) is in
progress while the >10 MeV integral proton flux sits at or above
``threshold_pfu`` (default 10 pfu = 10 protons cm⁻² s⁻¹ sr⁻¹); severity is
the NOAA S scale on the peak flux (S1 at 10 pfu up to S5 at 10⁵).

Per qualifying event (above-threshold samples grouped across gaps of at
most ``gap_hours``, kept when ``min_hours``+ long):

- onset, end, duration, and the peak flux + time per channel;
- fluence per channel (flux integrated over the event, cm⁻² sr⁻¹) via the
  median sample cadence;
- a spectral hardness ratio (peak >30 MeV / peak >10 MeV);
- the primary event is the FIRST (the prompt injection arrives first),
  the same convention as ``detect_icme``.

With flare context (peak time; optionally GOES class and source longitude)
the tool adds onset physics for the primary event:

- observed onset delay after the flare peak against the expected delay for
  10 / 30 MeV protons free-streaming along the Parker spiral (path length
  from the solar-wind speed; 1 AU light-travel time subtracted because
  flare timestamps are Earth-observed);
- velocity dispersion: the >30 MeV channel should cross its threshold
  before the >10 MeV channel does;
- magnetic connection: angular distance between the flare longitude and
  the Parker-spiral footpoint of the Earth-connected field line; well
  connected when ≤ 40°.
"""

from __future__ import annotations

import math

from helio_agent.registry import tool
from helio_agent.workspace import output_path

# NOAA radiation-storm scale on the >10 MeV peak flux (pfu)
S_SCALE = [(1e5, "S5"), (1e4, "S4"), (1e3, "S3"), (1e2, "S2"), (1e1, "S1")]

# Onset-physics constants
PROTON_REST_MEV = 938.272
C_KM_S = 299_792.458
AU_KM = 1.496e8
OMEGA_SUN_RAD_S = 2.865e-6  # sidereal solar rotation (25.38 d)
CONNECTION_LIMIT_DEG = 40.0  # |flare − footpoint| for "well connected"


def proton_speed_km_s(energy_mev: float) -> float:
    """Relativistic proton speed for a given kinetic energy."""
    gamma = 1.0 + energy_mev / PROTON_REST_MEV
    return C_KM_S * math.sqrt(1.0 - 1.0 / (gamma * gamma))


def parker_spiral_length_km(vsw_km_s: float) -> float:
    """Arc length of the Parker spiral from the Sun to 1 AU.

    Archimedean spiral with dφ/dr = Ω/v_sw: L = ∫₀ᴿ √(1 + k²r²) dr,
    k = Ω/v_sw, in closed form. About 1.14 AU at 450 km/s.
    """
    k = OMEGA_SUN_RAD_S / vsw_km_s
    kr = k * AU_KM
    return (AU_KM * math.sqrt(1.0 + kr * kr) + math.asinh(kr) / k) / 2.0


def parker_footpoint_lon_deg(vsw_km_s: float) -> float:
    """Heliographic (west) longitude of the field line connected to Earth."""
    return math.degrees(OMEGA_SUN_RAD_S * AU_KM / vsw_km_s)


def s_scale(peak_pfu: float) -> str | None:
    """NOAA S-scale label for a >10 MeV peak flux, or None below S1."""
    for threshold, label in S_SCALE:
        if peak_pfu >= threshold:
            return label
    return None


def _load_csv(file: str):
    import pandas as pd
    return pd.read_csv(file, index_col="time", parse_dates=True)


def _parse_flare_time(text: str):
    """Naive-UTC pandas Timestamp for a flare peak, or None if unparseable."""
    import pandas as pd
    try:
        t = pd.Timestamp(text)
    except (ValueError, TypeError):
        return None
    if t is pd.NaT:
        return None
    if t.tzinfo is not None:
        t = t.tz_convert("UTC").tz_localize(None)
    return t


def _physics(sep: dict, flux30, flare_peak, flare_class: str | None,
             flare_lon_deg: float | None, vsw_km_s: float,
             threshold_30mev_pfu: float) -> dict:
    import pandas as pd
    onset = pd.Timestamp(sep["onset"])
    delay_h = (onset - flare_peak).total_seconds() / 3600.0
    spiral_km = parker_spiral_length_km(vsw_km_s)
    light_h = AU_KM / C_KM_S / 3600.0
    expected10 = spiral_km / proton_speed_km_s(10.0) / 3600.0 - light_h
    expected30 = spiral_km / proton_speed_km_s(30.0) / 3600.0 - light_h
    has30 = flux30 is not None and len(flux30)
    footpoint = parker_footpoint_lon_deg(vsw_km_s)
    ph = {
        "flare_peak": str(flare_peak),
        "flare_class": flare_class,
        "onset_delay_hours": round(delay_h, 2),
        "expected_delay_hours_10mev": round(expected10, 2),
        "expected_delay_hours_30mev": round(expected30, 2) if has30 else None,
        "spiral_length_au": round(spiral_km / AU_KM, 3),
        "onset_30mev": None,
        "dispersion_minutes": None,
        "parker_footpoint_lon_deg": round(footpoint, 1),
        "connection_angle_deg": None,
        "well_connected": None,
        "note": "",
    }
    if has30:
        after = flux30.loc[flare_peak:]
        crossing = after[after >= threshold_30mev_pfu]
        if len(crossing):
            onset30 = crossing.index[0]
            ph["onset_30mev"] = str(onset30)
            ph["dispersion_minutes"] = round((onset - onset30).total_seconds() / 60.0, 1)
    if flare_lon_deg is not None:
        angle = abs(flare_lon_deg - ph["parker_footpoint_lon_deg"])
        ph["connection_angle_deg"] = round(angle, 1)
        ph["well_connected"] = bool(angle <= CONNECTION_LIMIT_DEG)

    flare_label = f"{flare_class} flare" if flare_class else "flare"
    parts = [
        f"onset {ph['onset_delay_hours']:g} h after the {flare_label} peak "
        f"(free-streaming 10 MeV expectation {ph['expected_delay_hours_10mev']:g} h "
        f"along a {ph['spiral_length_au']:g} AU spiral)"
    ]
    if ph["dispersion_minutes"] is not None:
        direction = "before" if ph["dispersion_minutes"] >= 0 else "AFTER"
        parts.append(f">30 MeV crossed {threshold_30mev_pfu:g} pfu "
                     f"{abs(ph['dispersion_minutes']):g} min {direction} the >10 MeV onset")
    if ph["connection_angle_deg"] is not None:
        verdict = "well connected" if ph["well_connected"] else "poorly connected"
        parts.append(f"source {ph['connection_angle_deg']:g}° from the "
                     f"W{ph['parker_footpoint_lon_deg']:g} Parker footpoint ({verdict})")
    ph["note"] = "; ".join(parts)
    return ph


@tool(family="measure")
def characterize_sep(file: str, flux_10mev_column: str,
                     flux_30mev_column: str | None = None,
                     threshold_pfu: float = 10.0, gap_hours: float = 12.0,
                     min_hours: float = 2.0, flare_peak_time: str | None = None,
                     flare_class: str | None = None,
                     flare_lon_deg: float | None = None, vsw_km_s: float = 450.0,
                     threshold_30mev_pfu: float = 1.0, plot: bool = True,
                     out_name: str = "sep.png") -> dict:
    """Characterize solar energetic particle (radiation storm) events in a
    proton-flux CSV: NOAA S-scale from the >10 MeV peak, onset / end /
    duration, per-channel peak and fluence, spectral hardness ratio, and —
    with flare context — onset physics (delay vs the Parker-spiral
    free-streaming expectation, >30 / >10 MeV velocity dispersion, magnetic
    connection of the flare site).

    file: workspace CSV with a 'time' index. Fluxes are integral proton
    fluxes in pfu (protons cm^-2 s^-1 sr^-1): OMNI hourly PR-FLX_101800 /
    PR-FLX_301800 (available through 2020-03 only), or GOES SEISS/EPEAD
    integral channels.

    An event is >10 MeV flux >= threshold_pfu (NOAA S1 = 10), samples
    merged across gaps <= gap_hours (decay dips do not split an event), kept
    when >= min_hours long. The primary event `sep` is the FIRST qualifying
    one (prompt injection); `events` lists all in time order.

    flare_peak_time (ISO UTC) enables `physics` for the primary event;
    flare_class labels the note; flare_lon_deg (heliographic, west positive)
    adds the connection angle to the Parker footpoint for vsw_km_s.
    threshold_30mev_pfu marks the >30 MeV onset for the dispersion check.

    Returns sep, events, n_events, physics, method, note, and the figure
    path when plot (log flux, both channels, threshold, events shaded).
    """
    import pandas as pd

    df = _load_csv(file)
    for col in (flux_10mev_column, flux_30mev_column):
        if col is not None and col not in df.columns:
            return {"status": "error",
                    "error": f"column {col!r} not in {file}; available: {list(df.columns)}"}
    flux10 = df[flux_10mev_column].astype(float)
    if flux10.notna().sum() == 0:
        return {"status": "error",
                "error": f"no valid {flux_10mev_column} samples in the window (all fill) — "
                         "this dataset may not cover the event's era (OMNI proton "
                         "fluxes end 2020-03; use GOES integral channels after that)"}
    flare_peak = None
    if flare_peak_time:
        flare_peak = _parse_flare_time(flare_peak_time)
        if flare_peak is None:
            return {"status": "error",
                    "error": f"flare_peak_time {flare_peak_time!r} is not a timestamp; "
                             "give ISO UTC, e.g. 2017-09-10T16:06:00Z"}
    flux30 = None
    if flux_30mev_column is not None:
        flux30 = df[flux_30mev_column].astype(float).dropna()
        if flux30.empty:
            flux30 = None

    valid10 = flux10.dropna()
    above = valid10[valid10 >= threshold_pfu].index
    groups: list[list] = []
    gap = pd.Timedelta(hours=gap_hours)
    for t in above:
        if groups and t - groups[-1][1] <= gap:
            groups[-1][1] = t
        else:
            groups.append([t, t])

    # median cadence (s) for the fluence integral
    idx = valid10.index
    if len(idx) >= 2:
        cadence_s = float(pd.Series(idx[1:51]).sub(pd.Series(idx[:50])).dt
                          .total_seconds().median())
    else:
        cadence_s = 3600.0

    events = []
    for a, b in groups:
        duration = (b - a).total_seconds() / 3600
        if duration < min_hours:
            continue
        seg = valid10.loc[a:b]
        peak_t = seg.idxmax()
        peak = float(seg.max())
        ev = {"onset": str(a), "end": str(b), "duration_hours": round(duration, 1),
              "peak_10mev": {"value": round(peak, 2), "time": str(peak_t)},
              "s_scale": s_scale(peak) or "S1",
              "fluence_10mev": round(float(seg.sum()) * cadence_s, 1),
              "peak_30mev": None, "fluence_30mev": None, "hardness_ratio": None}
        if flux30 is not None:
            seg30 = flux30.loc[a:b]
            if len(seg30):
                p30 = float(seg30.max())
                ev["peak_30mev"] = {"value": round(p30, 2), "time": str(seg30.idxmax())}
                ev["fluence_30mev"] = round(float(seg30.sum()) * cadence_s, 1)
                if peak > 0:
                    ev["hardness_ratio"] = round(p30 / peak, 3)
        events.append(ev)

    sep = events[0] if events else None
    if sep is None:
        peak_seen = float(valid10.max())
        note = (f">10 MeV flux never reached {threshold_pfu:g} pfu for {min_hours:g}+ h "
                f"(window maximum {peak_seen:g} pfu) — no SEP event in this window")
    else:
        hard = (f", hardness {sep['hardness_ratio']:g}"
                if sep["hardness_ratio"] is not None else "")
        note = (f"{sep['s_scale']} radiation storm: peak {sep['peak_10mev']['value']:g} pfu "
                f"at {sep['peak_10mev']['time']}, {sep['duration_hours']:g} h above "
                f"threshold{hard}")
        if len(events) > 1:
            note += f"; first of {len(events)} qualifying events"

    physics = None
    if sep is not None and flare_peak is not None:
        physics = _physics(sep, flux30, flare_peak, flare_class, flare_lon_deg,
                           vsw_km_s, threshold_30mev_pfu)
        note += f"; {physics['note']}"

    out = {"sep": sep, "events": events, "n_events": len(events), "physics": physics,
           "cadence_s": cadence_s,
           "method": "NOAA S-scale on >10 MeV integral flux >= threshold; fluence by "
                     "cadence-weighted sum; onset physics via Parker-spiral "
                     "free-streaming (Archimedean arc length) and footpoint longitude",
           "note": note}
    if plot:
        out["file"] = _plot(valid10, flux30, threshold_pfu, events, flare_peak, out_name)
        out["artifacts"] = [out["file"]]
    return out


def _plot(flux10, flux30, threshold_pfu, events, flare_peak, out_name) -> str:
    import pandas as pd
    from helio_agent.style import EVENT_COLOR, NEUTRAL, PALETTE, apply_style, figsize
    apply_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize("page", 0.45))
    ax.plot(flux10.index, flux10.clip(lower=1e-3), lw=1.0, color=PALETTE[0], label=">10 MeV")
    if flux30 is not None:
        ax.plot(flux30.index, flux30.clip(lower=1e-3), lw=1.0, color=PALETTE[1],
                label=">30 MeV")
    ax.axhline(threshold_pfu, color=NEUTRAL, ls="--", lw=0.8)
    ax.annotate(f"{threshold_pfu:g} pfu", xy=(0.005, threshold_pfu),
                xycoords=("axes fraction", "data"), va="bottom", fontsize=7, color=NEUTRAL)
    for k, ev in enumerate(events):
        ax.axvspan(pd.Timestamp(ev["onset"]), pd.Timestamp(ev["end"]), color=PALETTE[0],
                   alpha=0.15 if k == 0 else 0.07, lw=0)
    if flare_peak is not None:
        ax.axvline(flare_peak, color=EVENT_COLOR, ls="--", lw=0.9, alpha=0.85)
        ax.annotate("flare", xy=(flare_peak, 1.0), xycoords=("data", "axes fraction"),
                    rotation=90, va="top", ha="right", fontsize=7, color=EVENT_COLOR)
    ax.set_yscale("log")
    ax.set_ylabel("Proton flux (cm$^{-2}$ s$^{-1}$ sr$^{-1}$)")
    ax.set_xlabel("Time (UTC)")
    ax.set_title("SEP event detection" + (f" — {events[0]['s_scale']} radiation storm"
                                          if events else " — none found"))
    ax.legend(loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)
