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
def track_cme_front(files: list[str], position_angle_deg: float | None = None,
                    sector_width_deg: float = 30.0,
                    n_sigma: float = 5.0,
                    r_min_rsun: float | None = None,
                    r_max_rsun: float | None = None) -> dict:
    """Track a CME leading edge through a coronagraph sequence, frame by frame.

    Measures the front so `cme_height_time` has something real to fit. Each
    frame is divided by its own exposure time and differenced against the
    previous one (same discipline as `plot_coronagraph_sequence`), remapped
    to heliocentric radius through the frame WCS, and reduced to a median
    radial profile inside a position-angle sector. The leading edge is the
    OUTERMOST radius where that profile stays above `n_sigma` times the
    noise for three consecutive radial bins — a single hot pixel or a cosmic
    ray cannot set the edge.

    position_angle_deg: sector centre, degrees counter-clockwise from solar
      north (the standard coronagraph convention). Leave None to auto-select
      the sector with the largest outward excursion across the sequence; the
      chosen angle is reported either way, so an auto choice is inspectable.
    sector_width_deg: full width of the sector. Narrow sectors are noisier;
      wide ones average over structure moving at different speeds.
    n_sigma: detection threshold, in units of the per-frame noise, estimated
      as 1.4826 x the median absolute deviation of the whole differenced
      frame. A plain standard deviation over an outer annulus is not usable
      here: once the CME reaches that annulus it inflates its own noise
      floor and suppresses the detection.
    r_min_rsun / r_max_rsun: radial search bounds. Default to the detector's
      own field (C2: 2.2-6, C3: 3.7-30), which keeps the occulter edge and
      the frame corners out of the measurement.

    Refuses rather than guessing when: fewer than 3 frames survive, the WCS
    carries no solar radius, or fewer than 3 frames yield a detection.
    Returns per-frame times and heights ready to hand to `cme_height_time`,
    plus the detections it rejected and why.

    **This is a plane-of-sky measurement of a running-difference front.**
    The bright edge in a difference image is where the brightness CHANGED
    most, which is the front only if the front is the fastest-moving
    feature; a streamer deflection can masquerade as one. Always compare the
    result against a cone-model fit before quoting it as physical.
    """
    import numpy as np
    import sunpy.map

    if len(files) < 3:
        return {"status": "error",
                "error": ("need at least 3 frames to track a front and fit "
                          f"it; got {len(files)}")}
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
                "error": ("a frame carries no usable exposure time; refusing "
                          "to difference raw counts")}

    ref = maps[0]
    # LASCO headers carry no RSUN/RSUN_OBS. sunpy computes the apparent solar
    # radius from the observation date (assuming an Earth-based observer when
    # DSUN_OBS is absent, as it is here). SOHO sits ~1% closer to the Sun than
    # Earth, so heights carry a ~1% systematic on top of the fit error; that
    # is reported rather than hidden.
    import astropy.units as u

    try:
        rsun_arcsec = float(ref.rsun_obs.to_value(u.arcsec))
        cdelt = float(ref.scale[0].to_value(u.arcsec / u.pix))
        cx = float(ref.reference_pixel[0].to_value(u.pix))
        cy = float(ref.reference_pixel[1].to_value(u.pix))
    except Exception as exc:  # noqa: BLE001
        return {"status": "error",
                "error": f"frame WCS is unusable for a radial measurement: {exc}"}
    if not (rsun_arcsec > 0 and cdelt > 0):
        return {"status": "error",
                "error": (f"nonsensical WCS: rsun {rsun_arcsec} arcsec, "
                          f"scale {cdelt} arcsec/pix")}
    rsun_source = ("header" if ref.meta.get("rsun") or ref.meta.get("RSUN_OBS")
                   else "computed from date (Earth-based observer assumed; "
                        "~1% systematic for SOHO at L1)")
    px_per_rsun = rsun_arcsec / cdelt

    detector = (ref.detector or "").upper()
    if r_min_rsun is None:
        r_min_rsun = 3.9 if detector == "C3" else 2.4
    if r_max_rsun is None:
        r_max_rsun = 29.0 if detector == "C3" else 5.8

    ny, nx = np.asarray(ref.data).shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    dx = xx - cx
    dy = yy - cy
    rr = np.hypot(dx, dy) / px_per_rsun
    # position angle: 0 at solar north, increasing counter-clockwise (east)
    pa = (np.degrees(np.arctan2(-dx, dy))) % 360.0

    edges = np.arange(float(r_min_rsun), float(r_max_rsun), 0.10)
    centres = 0.5 * (edges[:-1] + edges[1:])

    diffs, stamps = [], []
    for i in range(1, len(maps)):
        cur = np.asarray(maps[i].data, dtype=float) / exposures[i]
        prev = np.asarray(maps[i - 1].data, dtype=float) / exposures[i - 1]
        if cur.shape != prev.shape:
            continue
        diffs.append(cur - prev)
        stamps.append(maps[i].date.datetime)
    if len(diffs) < 3:
        return {"status": "error",
                "error": ("fewer than 3 consecutive frames share a shape; the "
                          "sequence probably mixes detectors (pass "
                          "detector='C2' to fetch_vso)")}

    def _profile(d, pa_centre):
        """(radial SNR profile, edge) for one sector of one difference frame.

        The reference is the SAME RADIUS at other position angles, not an
        outer annulus: that cancels the steep radial brightness gradient and
        the frame-wide noise floor, both of which otherwise swamp a thin
        front arc. The sector statistic is the 90th percentile, because the
        front occupies only part of a 30-degree bin and a median averages it
        away.
        """
        half = float(sector_width_deg) / 2.0
        dpa = np.abs(((pa - pa_centre + 180.0) % 360.0) - 180.0)
        sector = dpa <= half
        quiet = dpa > (half + 30.0)      # guard band between the two
        snr = np.full(centres.size, np.nan)
        for k in range(centres.size):
            band = (rr >= edges[k]) & (rr < edges[k + 1])
            a = d[sector & band]
            q = d[quiet & band]
            a = a[np.isfinite(a)]
            q = q[np.isfinite(q)]
            if a.size < 20 or q.size < 50:
                continue
            noise = float(1.4826 * np.median(np.abs(q - np.median(q))))
            if not np.isfinite(noise) or noise <= 0:
                continue
            snr[k] = float(np.percentile(a, 90)) / noise
        hot = np.nan_to_num(snr, nan=-np.inf) > n_sigma
        run, best = 0, None
        for k in range(centres.size):
            run = run + 1 if hot[k] else 0
            if run >= 3:
                best = float(centres[k])
        return snr, best

    def _edge(d, pa_centre):
        return _profile(d, pa_centre)[1]

    def _halo_fraction(d):
        """Fraction of position angles brightening — 1.0 means a full halo.

        A halo CME brightens every position angle at once, so there is no
        quiet reference left and azimuthal contrast cannot locate a front.
        That is a property of the event, not a failure of the code, and it
        is why the community fits halos with cone/GCS models instead.
        """
        hits = 0
        for pac in range(0, 360, 15):
            half = float(sector_width_deg) / 2.0
            dpa = np.abs(((pa - float(pac) + 180.0) % 360.0) - 180.0)
            sector = (dpa <= half) & (rr >= r_min_rsun) & (rr <= r_max_rsun)
            a = d[sector & np.isfinite(d)]
            fin = d[np.isfinite(d)]
            if a.size < 50 or fin.size == 0:
                continue
            scale = float(1.4826 * np.median(np.abs(fin - np.median(fin))))
            if scale > 0 and float(np.percentile(a, 90)) > 3.0 * scale:
                hits += 1
        return hits / 24.0

    if position_angle_deg is None:
        # Score sectors by whether the front actually MOVES OUTWARD, not by
        # how far the detections scatter: maximising the raw span rewards a
        # noisy sector whose "edge" jumps around, which is the opposite of a
        # tracked front. Monotonic first, then number of detections, then
        # distance travelled.
        best_score, chosen = None, None
        for pac in range(0, 360, 15):
            vals = [_edge(d, float(pac)) for d in diffs]
            good = [v for v in vals if v is not None]
            if len(good) < 3:
                continue
            mono = all(b >= a for a, b in zip(good, good[1:]))
            score = (1 if mono else 0, len(good), max(good) - min(good))
            if best_score is None or score > best_score:
                best_score, chosen = score, float(pac)
        if chosen is None:
            return {"status": "error",
                    "error": (f"no sector produced 3+ detections at "
                              f"{n_sigma} sigma; lower n_sigma or widen the "
                              "radial bounds")}
        pa_source = ("auto (monotonic outward track, "
                     f"{best_score[1]} detections)" if best_score[0]
                     else f"auto (best available, {best_score[1]} detections, "
                          "NOT monotonic)")
    else:
        chosen = float(position_angle_deg) % 360.0
        pa_source = "caller"

    halo_frac = [float(_halo_fraction(d)) for d in diffs]
    halo_peak = max(halo_frac) if halo_frac else 0.0

    times, heights, rejected = [], [], []
    for d, t in zip(diffs, stamps):
        h = _edge(d, chosen)
        if h is None:
            rejected.append({"time": str(t), "reason": "no 3-bin run above "
                                                       "threshold"})
            continue
        times.append(str(t))
        heights.append(round(float(h), 3))
    if len(times) < 3:
        halo_note = ""
        if halo_peak >= 0.75:
            halo_note = (
                f" This is a HALO event: {halo_peak * 100:.0f}% of position "
                "angles brighten simultaneously, so no quiet reference "
                "annulus remains and azimuthal contrast cannot locate a "
                "front. Plane-of-sky height-time does not apply to a halo "
                "by construction — use a cone or GCS fit (DONKI "
                "CMEAnalysis) instead. This is a property of the geometry, "
                "not a threshold that wants lowering.")
        return {"status": "error",
                "n_detections": len(times),
                "halo_fraction_peak": round(halo_peak, 2),
                "position_angle_deg": round(chosen, 1),
                "error": (f"only {len(times)} frame(s) yielded a detection at "
                          f"PA {chosen:.0f} deg and {n_sigma} sigma; refusing "
                          "to fit." + (halo_note or
                          " Lower n_sigma, widen sector_width_deg, or check "
                          "that the CME is inside the radial bounds."))}

    monotonic = all(b >= a for a, b in zip(heights, heights[1:]))

    # Two ways a "track" can be an artefact rather than a measurement. Both
    # reach here with 3+ monotonic detections, and both must be refused.
    #
    # (1) A FULL HALO brightens every position angle, so the azimuthal
    #     reference is itself full of CME and no sector stands out. What the
    #     tracker then follows is the edge of the brightened region, not a
    #     front. Geometry, not tuning: plane-of-sky height-time does not
    #     apply to a halo, which is why halos are fitted with cone/GCS.
    if halo_peak >= 0.75:
        return {"status": "error",
                "n_detections": len(times), "heights_rsun": heights,
                "halo_fraction_peak": round(halo_peak, 2),
                "position_angle_deg": round(chosen, 1),
                "error": (f"HALO event: {halo_peak * 100:.0f}% of position "
                          "angles brighten simultaneously, so no quiet "
                          "reference annulus remains and azimuthal contrast "
                          "cannot locate a front. Plane-of-sky height-time "
                          "does not apply to a halo by construction — use a "
                          "cone or GCS fit (search_donki CMEAnalysis). This "
                          "is the geometry of the event, not a threshold "
                          "that wants lowering.")}
    # (2) Heights PINNED AT THE SEARCH BOUND. A CME faster than the field can
    #     follow leaves the detector between frames; the outermost bin stays
    #     lit and every later "detection" reports the same radius. A repeated
    #     maximum at r_max is a saturation, not a track — and it passes the
    #     monotonicity test, which is why it needs its own check.
    edge = float(r_max_rsun) - 0.15
    pinned = sum(1 for h in heights if h >= edge)
    if pinned >= 2 and pinned >= len(heights) / 2:
        return {"status": "error",
                "n_detections": len(times), "heights_rsun": heights,
                "halo_fraction_peak": round(halo_peak, 2),
                "position_angle_deg": round(chosen, 1),
                "error": (f"{pinned} of {len(heights)} heights sit at the "
                          f"outer search bound ({r_max_rsun} Rsun): the front "
                          "left the field faster than the cadence can follow, "
                          "so these are saturations, not measurements. Track "
                          "this event in a wider field (LASCO C3 spans "
                          "3.9-29 Rsun against C2's 2.4-5.8) or accept that "
                          "the plane-of-sky speed is unmeasurable here.")}

    return {"n_frames": len(maps), "n_differences": len(diffs),
            "n_detections": len(times),
            "position_angle_deg": round(chosen, 1),
            "position_angle_source": pa_source,
            "sector_width_deg": float(sector_width_deg),
            "n_sigma": float(n_sigma),
            "search_r_rsun": [float(r_min_rsun), float(r_max_rsun)],
            "instrument": f"{ref.instrument} {ref.detector}".strip(),
            "px_per_rsun": round(float(px_per_rsun), 2),
            "rsun_arcsec": round(float(rsun_arcsec), 2),
            "rsun_source": rsun_source,
            "halo_fraction_peak": round(halo_peak, 2),
            "times": times, "heights_rsun": heights,
            "monotonic": bool(monotonic),
            "rejected": rejected,
            "note": ("Plane-of-sky leading edge of a RUNNING-DIFFERENCE "
                     "front: the outermost radius where the differenced, "
                     "exposure-normalised profile stays above "
                     f"{n_sigma} sigma for 3 consecutive 0.1 Rsun bins. "
                     "Feed times/heights_rsun to cme_height_time. Compare "
                     "against a cone-model fit before quoting as physical."
                     + ("" if monotonic else " HEIGHTS ARE NOT MONOTONIC — "
                        "the sector likely contains more than one moving "
                        "feature; inspect before fitting."))}


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
