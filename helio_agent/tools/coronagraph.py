"""Coronagraph sequences: running difference, and CME height-time (report+measure).

A CME is invisible in a raw coronagraph frame — the static K-corona and
stray-light pattern dominate it by orders of magnitude. What makes an
eruption visible is the **running difference**: each frame minus the one
before, after normalising both by exposure time. That normalisation is not
optional. LASCO C2 alternates exposure lengths through a sequence (2.1 MB
and 1.1 MB files in the same hour are different exposures), so differencing
raw counts produces a bright/dark flicker that looks like an outward
disturbance and is nothing but the shutter.

`plot_coronagraph_sequence` builds those frames. `cme_height_time` fits a
front's measured heights against time for a plane-of-sky speed — the same
linear fit CDAW's catalogue uses, so a result here is comparable with a
catalogue entry rather than a private convention.

Gotchas
-------
* **Plane-of-sky speeds are lower bounds.** A halo CME aimed at Earth is
  seen edge-on, so its measured speed underestimates the radial speed;
  cone-model or GCS fits (DONKI CMEAnalysis) correct for that geometry.
  `cme_height_time` says so in its result rather than letting the number
  pass as the physical speed.
* **Heights must be measured, not invented.** This tool takes heights the
  caller obtained from the frames; it does not track a front for you. A
  tracking algorithm that silently guesses would be worse than no tool.
* LASCO frames occasionally arrive out of time order from the archive, and
  a missing frame makes a difference span two cadences. Frames are sorted
  by DATE-OBS and each panel is labelled with its own timestamp and the
  gap it covers.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import output_path

RSUN_KM = 695700.0


@tool(family="report")
def plot_coronagraph_sequence(files: list[str], n_panels: int = 6,
                              clip_percent: float = 99.0,
                              title: str = "",
                              out_name: str = "coronagraph.png") -> dict:
    """Running-difference panels from a coronagraph FITS sequence (LASCO, SECCHI).

    Each frame is divided by its own exposure time before differencing, so a
    sequence with alternating exposures does not produce spurious brightness
    steps. Frames are sorted by observation time; `n_panels` evenly spaced
    differences are drawn, each labelled with its time and the interval it
    spans.

    files: coronagraph FITS paths (e.g. from fetch_vso with detector='C2').
    clip_percent: symmetric intensity clip for the difference scale.

    Returns the figure path, the frame times used, the median cadence, and
    `exposure_times_s` — inspect it: more than one distinct value is exactly
    the case where raw differencing would have produced artefacts.
    """
    import numpy as np
    import sunpy.map

    from helio_agent.tools.report import _setup_mpl

    if len(files) < 2:
        return {"status": "error",
                "error": "need at least 2 frames for a running difference; "
                         f"got {len(files)}"}
    maps = []
    for f in files:
        try:
            maps.append(sunpy.map.Map(f))
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": f"could not read {f}: {exc}"}
    maps.sort(key=lambda m: m.date.datetime)

    exposures = []
    for m in maps:
        e = m.meta.get("exptime") or m.meta.get("XPOSURE")
        try:
            e = float(e)
        except (TypeError, ValueError):
            e = None
        exposures.append(e if (e and e > 0) else None)
    if any(e is None for e in exposures):
        return {"status": "error",
                "error": "a frame carries no usable exposure time; refusing to "
                         "difference raw counts, which would turn the shutter "
                         "pattern into a fake outward disturbance"}

    diffs, stamps, spans = [], [], []
    for i in range(1, len(maps)):
        cur = np.asarray(maps[i].data, dtype=float) / exposures[i]
        prev = np.asarray(maps[i - 1].data, dtype=float) / exposures[i - 1]
        if cur.shape != prev.shape:
            continue
        diffs.append(cur - prev)
        stamps.append(str(maps[i].date.datetime))
        spans.append((maps[i].date.datetime
                      - maps[i - 1].date.datetime).total_seconds() / 60.0)
    if not diffs:
        return {"status": "error",
                "error": "no consecutive frames share a shape; the sequence "
                         "probably mixes detectors (pass detector='C2')"}

    n = min(n_panels, len(diffs))
    idx = np.linspace(0, len(diffs) - 1, n, dtype=int)
    rows = 2 if n > 3 else 1
    cols = int(np.ceil(n / rows))
    plt = _setup_mpl()
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 4.4 * rows))
    axes = np.atleast_1d(axes).ravel()
    for k, j in enumerate(idx):
        d = diffs[j]
        lim = float(np.nanpercentile(np.abs(d[np.isfinite(d)]), clip_percent))
        axes[k].imshow(d, origin="lower", cmap="Greys_r", vmin=-lim, vmax=lim)
        axes[k].set_title(f"{stamps[j][:19]}  (+{spans[j]:.0f} min)",
                          fontsize=9)
        axes[k].set_xticks([])
        axes[k].set_yticks([])
    for k in range(len(idx), len(axes)):
        axes[k].axis("off")
    inst = f"{maps[0].instrument} {maps[0].detector}".strip()
    fig.suptitle(title or f"{inst} running difference", fontsize=13)
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight", dpi=130)
    plt.close(fig)

    uniq = sorted({round(e, 3) for e in exposures})
    cadence = float(np.median(spans)) if spans else None
    return {"file": str(fpath), "n_frames": len(maps), "n_differences": len(diffs),
            "n_panels": int(n), "instrument": inst,
            "start": str(maps[0].date.datetime), "end": str(maps[-1].date.datetime),
            "median_cadence_min": cadence,
            "exposure_times_s": uniq,
            "note": ("Each frame divided by its own exposure time before "
                     f"differencing ({len(uniq)} distinct exposure(s) present"
                     + ("; raw differencing would have produced brightness "
                        "artefacts here)." if len(uniq) > 1 else ").")),
            "artifacts": [str(fpath)]}


@tool(family="measure")
def cme_height_time(times: list[str], heights_rsun: list[float],
                    plane_of_sky: bool = True) -> dict:
    """Linear height-time fit for a CME front: plane-of-sky speed and its error.

    times: ISO timestamps of the measured front positions.
    heights_rsun: leading-edge heliocentric distance in solar radii, measured
      from the frames (this tool does not track the front for you).

    Returns speed_km_s with its standard error, the fitted launch time where
    the fit crosses 1 Rsun (an extrapolation, flagged as such), r_squared,
    and an acceleration from an optional quadratic term.

    **Plane-of-sky speeds are lower bounds for an Earth-directed CME**: a
    halo is seen edge-on, so the measured speed understates the radial one.
    Compare against a cone-model or GCS fit (DONKI CMEAnalysis) before
    quoting a speed as physical.
    """
    import numpy as np
    import pandas as pd

    if len(times) != len(heights_rsun):
        return {"status": "error",
                "error": f"{len(times)} times but {len(heights_rsun)} heights"}
    if len(times) < 3:
        return {"status": "error",
                "error": "need at least 3 points for a fit with an error bar; "
                         f"got {len(times)}"}
    t = pd.to_datetime(pd.Series(times), utc=True, format="mixed")
    order = np.argsort(t.values)
    t = t.iloc[order].reset_index(drop=True)
    h = np.asarray(heights_rsun, dtype=float)[order]
    if not np.all(np.diff(h) >= 0):
        return {"status": "error",
                "error": "heights are not monotonically increasing with time; "
                         "check the measurements or the frame ordering"}
    secs = (t - t.iloc[0]).dt.total_seconds().to_numpy()

    coef, cov = np.polyfit(secs, h, 1, cov=True)
    slope, intercept = coef
    slope_err = float(np.sqrt(cov[0, 0]))
    pred = np.polyval(coef, secs)
    ss_res = float(np.sum((h - pred) ** 2))
    ss_tot = float(np.sum((h - h.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    accel = None
    if len(secs) >= 4:
        q = np.polyfit(secs, h, 2)
        accel = float(q[0] * 2 * RSUN_KM * 1e3)  # Rsun/s^2 -> m/s^2

    speed = float(slope * RSUN_KM)
    t_launch = (t.iloc[0] + pd.Timedelta(seconds=float((1.0 - intercept) / slope))
                if slope > 0 else None)
    return {"speed_km_s": round(speed, 1),
            "speed_error_km_s": round(float(slope_err * RSUN_KM), 1),
            "r_squared": round(float(r2), 4),
            "acceleration_m_s2": None if accel is None else round(accel, 2),
            "n_points": int(len(h)),
            "height_range_rsun": [float(h[0]), float(h[-1])],
            "extrapolated_launch_1rsun": (None if t_launch is None
                                          else str(t_launch)),
            "plane_of_sky": bool(plane_of_sky),
            "note": ("Plane-of-sky linear fit (the CDAW catalogue convention). "
                     "For an Earth-directed halo this is a LOWER BOUND on the "
                     "radial speed — compare with a cone/GCS fit such as DONKI "
                     "CMEAnalysis. The launch time is an extrapolation of the "
                     "linear fit back to 1 Rsun, not an observation.")}
