"""Type II / type III solar radio burst detection in dynamic spectra (measure).

Ported from helio-agent's ``analysis.radio_bursts`` (v1.0.0) onto this repo's
CSV-in / dict-out contract. See skills/methods/radio_burst_analysis.md.

Solar radio bursts are the earliest remote signature of an eruption's
particles and shocks: **type III** bursts are electron beams racing out
along open field lines (seconds to minutes, drifting fast from high to low
frequency); **type II** bursts are CME-driven shocks plowing through the
corona (drifting slowly, over tens of minutes to hours). Both appear in a
dynamic spectrum as emission drifting toward lower frequency as the source
moves out through falling plasma density.

Method, over a spectrogram CSV from ``fetch_cdaweb_spectrogram`` (WIND/WAVES
``WI_K0_WAV`` / ``E_Average``: dB above background at 76 log-spaced
frequencies, ~3-min cadence):

1. Times where at least ``min_channels`` channels above ``min_freq_hz`` (the
   TNR thermal-noise / plasma-line range is excluded) exceed ``min_db`` are
   *active*; active times merge across gaps of at most ``gap_minutes``.
2. Each burst's log-frequency centroid drift (first active sample to last)
   converts to a radial source speed by inverting the Leblanc, Dulk &
   Bougeret (1998) density model, assuming fundamental plasma emission:
   f_pe[kHz] = 8.98 sqrt(n_e), n_e(r) = 3.3e5 r^-2 + 4.1e6 r^-4 + 8e7 r^-6.
3. The inferred speed classifies the burst: electron beams are far faster
   than any shock, so speed > ``typeiii_min_speed_km_s`` is type III,
   200 km/s to that bound is a type II candidate, no downward drift is
   unclassified (storm-time auroral kilometric radiation lands here).
"""

from __future__ import annotations

import math
import re

from helio_agent.registry import tool
from helio_agent.workspace import output_path

RSUN_KM = 695_700.0
FILL_CUTOFF = 1e30  # CDF fill is -1e31; anything |v| >= cutoff is no-data
_CHANNEL = re.compile(r"^[a-zA-Z_]*([0-9.eE+-]+)(?:hz)?$", re.IGNORECASE)


def leblanc_density(r_rsun: float) -> float:
    """Electron density (cm^-3) at r solar radii — Leblanc et al. 1998."""
    return 3.3e5 * r_rsun**-2 + 4.1e6 * r_rsun**-4 + 8.0e7 * r_rsun**-6


def radius_for_frequency(f_hz: float) -> float:
    """Invert the Leblanc model: fundamental plasma frequency -> R_sun (bisection)."""
    n_target = (f_hz / 1e3 / 8.98) ** 2
    lo, hi = 1.2, 400.0
    if leblanc_density(lo) < n_target:
        return lo
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if leblanc_density(mid) > n_target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def channel_frequency(column: str) -> float | None:
    """Frequency in Hz encoded in a spectrogram column name ('c268', '10090000')."""
    m = _CHANNEL.match(column.strip())
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _characterize(group, times, centers, min_speed_kms: float) -> dict:
    """group: list of (time_index, [(channel_index, dB), ...]) in time order."""
    first_idx, last_idx = group[0][0], group[-1][0]
    span_s = (times[last_idx] - times[first_idx]).total_seconds()
    duration_min = span_s / 60.0
    points = [(t_idx, i, v) for t_idx, enhanced in group for i, v in enhanced]
    peak_t, peak_i, peak_v = max(points, key=lambda p: p[2])
    freqs = [centers[i] for _, i, _ in points]

    speed = None
    if span_s > 0:
        c0 = sum(math.log10(centers[i]) for i, _ in group[0][1]) / len(group[0][1])
        c1 = sum(math.log10(centers[i]) for i, _ in group[-1][1]) / len(group[-1][1])
        if c1 < c0:  # drifting down in frequency = moving out
            r0, r1 = radius_for_frequency(10**c0), radius_for_frequency(10**c1)
            speed = round((r1 - r0) * RSUN_KM / span_s, 0)

    span_decades = math.log10(max(freqs) / min(freqs)) if freqs else 0.0
    if span_s == 0:
        classification = "type III (impulsive)" if span_decades >= 1.0 else "unclassified"
    elif speed is not None and speed > min_speed_kms:
        classification = "type III"
    elif speed is not None and 200.0 <= speed <= min_speed_kms:
        classification = "type II candidate"
    else:
        classification = "unclassified"

    return {"start": str(times[first_idx]), "end": str(times[last_idx]),
            "duration_minutes": round(duration_min, 1), "n_samples": len(group),
            "peak_db": round(float(peak_v), 1), "peak_time": str(times[peak_t]),
            "peak_freq_hz": centers[peak_i], "freq_min_hz": min(freqs),
            "freq_max_hz": max(freqs), "inferred_speed_km_s": speed,
            "classification": classification}


@tool(family="measure")
def radio_bursts(file: str, min_db: float = 10.0, min_channels: int = 8,
                 min_freq_hz: float = 20_000.0, gap_minutes: float = 15.0,
                 typeiii_min_speed_km_s: float = 5000.0, plot: bool = True,
                 out_name: str = "radio_bursts.png") -> dict:
    """Detect and classify solar radio bursts (type III electron beams vs type
    II shock candidates) in a dynamic-spectrum CSV, via frequency-drift speeds
    through the Leblanc et al. (1998) density model. Labeled spectrogram plot.

    file: spectrogram CSV from fetch_cdaweb_spectrogram — 'time' index, one
    column per frequency channel named c<Hz> (WIND/WAVES WI_K0_WAV E_Average:
    dB above background, 76 channels, ~3-min cadence).

    A time is active when >= min_channels channels above min_freq_hz (default
    20 kHz, excluding the TNR plasma-line range) exceed min_db; active times
    within gap_minutes merge into one burst. The log-frequency centroid drift
    from first to last active sample, inverted through Leblanc's n_e(r) for
    fundamental emission, gives inferred_speed_km_s: > typeiii_min_speed_km_s
    is "type III", 200 km/s to that bound "type II candidate", no downward
    drift "unclassified"; single-sample broadband (>= 1 decade) enhancements
    are "type III (impulsive)".

    Returns bursts (time order), n_bursts, counts by classification, note, and
    the figure path when plot. The speed is a fundamental-emission, radial,
    model-density estimate: harmonic emission halves the radius, and the
    3-min cadence undersamples type III drifts, so quote it as indicative.
    """
    import pandas as pd

    df = pd.read_csv(file, index_col="time", parse_dates=True)
    chan = [(c, channel_frequency(c)) for c in df.columns]
    centers_all = [(c, f) for c, f in chan if f is not None]
    if not centers_all:
        return {"status": "error",
                "error": f"no frequency-channel columns (c<Hz>) in {file}; columns: "
                         f"{list(df.columns)[:6]}... — fetch with fetch_cdaweb_spectrogram"}
    if df.empty:
        return {"status": "error", "error": f"no spectra rows in {file}"}
    cols = [c for c, _ in centers_all]
    centers = [f for _, f in centers_all]
    usable = [i for i, f in enumerate(centers) if f >= min_freq_hz]
    if not usable:
        return {"status": "error",
                "error": f"min_freq_hz={min_freq_hz:g} excludes every channel "
                         f"(max {max(centers):g} Hz)"}
    matrix = df[cols].to_numpy(float)
    times = list(df.index)

    # 1. active times: broad simultaneous enhancement above background
    active = []
    for t_idx in range(len(times)):
        row = matrix[t_idx]
        enhanced = [(i, float(row[i])) for i in usable
                    if not math.isnan(row[i]) and min_db <= row[i] < FILL_CUTOFF]
        if len(enhanced) >= min_channels:
            active.append((t_idx, enhanced))

    # 2. merge across gaps into bursts
    groups: list[list] = []
    gap = pd.Timedelta(minutes=gap_minutes)
    for entry in active:
        if groups and times[entry[0]] - times[groups[-1][-1][0]] <= gap:
            groups[-1].append(entry)
        else:
            groups.append([entry])

    bursts = [_characterize(g, times, centers, typeiii_min_speed_km_s) for g in groups]
    counts: dict[str, int] = {}
    for b in bursts:
        counts[b["classification"]] = counts.get(b["classification"], 0) + 1
    if bursts:
        parts = ", ".join(f"{v}x {k}" for k, v in sorted(counts.items()))
        note = f"{len(bursts)} radio bursts: {parts}"
    else:
        note = (f"no radio bursts: never >= {min_channels} channels above {min_db:g} dB "
                f"(> {min_freq_hz:g} Hz) in this window")

    out = {"bursts": bursts, "n_bursts": len(bursts), "counts": counts,
           "n_samples": len(times), "n_channels": len(usable),
           "method": "simultaneous-channel enhancement, gap-merged; log-frequency "
                     "centroid drift inverted through Leblanc et al. 1998 n_e(r) "
                     "(fundamental emission) for radial speed; speed-class thresholds",
           "note": note}
    if plot:
        out["file"] = _plot(times, matrix, centers, usable, bursts, out_name)
        out["artifacts"] = [out["file"]]
    return out


def _plot(times, matrix, centers, usable, bursts, out_name) -> str:
    import numpy as np
    import pandas as pd
    from helio_agent.style import EVENT_COLOR, SEQUENTIAL_CMAP, apply_style, figsize
    apply_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize("page", 0.45))
    freqs = np.array([centers[i] for i in usable])
    grid = matrix[:, usable].T.astype(float)
    grid = np.where(np.isnan(grid) | (grid < 0) | (grid >= FILL_CUTOFF), 0.0, grid)
    mesh = ax.pcolormesh(pd.DatetimeIndex(times), freqs, grid, cmap=SEQUENTIAL_CMAP,
                         vmin=0.0, vmax=30.0, shading="nearest")
    fig.colorbar(mesh, ax=ax, pad=0.01, label="dB above background")
    short = {"type III": "III", "type III (impulsive)": "III",
             "type II candidate": "II?", "unclassified": "?"}
    for b in bursts:
        t0, t1 = pd.Timestamp(b["start"]), pd.Timestamp(b["end"])
        ax.axvspan(t0, t1, color=EVENT_COLOR, alpha=0.12, lw=0)
        ax.annotate(short[b["classification"]], xy=(t0 + (t1 - t0) / 2, freqs.max() * 0.72),
                    color=EVENT_COLOR, fontweight="bold", ha="center", fontsize=8)
    ax.set_yscale("log")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_xlabel("Time (UTC)")
    ax.set_title("WIND/WAVES dynamic spectrum — detected radio bursts")
    fig.autofmt_xdate()
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)
