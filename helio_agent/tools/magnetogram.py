"""Quantitative field metrics from an HMI line-of-sight magnetogram (measure).

Ported from helio-agent's ``analysis.magnetogram`` (v1.0.0) onto this repo's
FITS-in / dict-out contract. See skills/missions/sdo.md for the craft.

The Mount Wilson class is a categorical label written by an observer. This
tool measures the same physics from the data: given an HMI LOS magnetogram
FITS (``fetch_vso`` with physobs LOS_magnetic_field, or a JSOC export), it
computes

- **total unsigned flux** Φ = Σ|B_los|·A_pixel over the disk and over an
  active-region box — the standard size / energy proxy (Maxwell);
- the **polarity-inversion-line (PIL) proxy**: pixels where strong
  positive and strong negative field sit side by side (each polarity's
  strong mask dilated by one pixel, then intersected). δ-class regions —
  opposite-polarity umbrae sharing a penumbra — light up exactly here.
  Reported as a length (pixel count × pixel size) and as the unsigned flux
  threaded through the PIL neighborhood (an R-value-like proxy);
- max |B| and the signed flux balance in the box.

The region box is given in heliographic Stonyhurst coordinates (the frame
DONKI flare locations use, west positive) and projected to pixels through
the map's own WCS, so foreshortening is handled by the projection. Honest
limits: fluxes are line-of-sight with no μ (foreshortening) correction — a
lower bound away from disk center — and the PIL length is a pixel-chain
measure, not a smoothed curve length.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import output_path


def _dilate(mask):
    """8-neighborhood dilation by one pixel (no scipy dependency)."""
    import numpy as np
    out = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def strong_pil(sub, strong_g: float):
    """Boolean mask of strong-PIL pixels in a magnetogram cutout."""
    import numpy as np
    valid = np.isfinite(sub)
    pos = valid & (sub >= strong_g)
    neg = valid & (sub <= -strong_g)
    return _dilate(pos) & _dilate(neg)


@tool(family="measure")
def magnetogram_metrics(fits_file: str, lat_deg: float | None = None,
                        lon_deg: float | None = None, half_deg: float = 8.0,
                        noise_g: float = 20.0, strong_g: float = 100.0,
                        plot: bool = True, out_name: str = "magnetogram.png") -> dict:
    """Quantitative metrics from an HMI LOS magnetogram FITS: total unsigned
    flux (disk + active-region box), signed balance, max |B|, and a
    polarity-inversion-line proxy (strong-PIL length and threaded flux) — the
    measured counterpart of the Mount Wilson delta class. Annotated plot.

    fits_file: a full-disk HMI LOS magnetogram (hmi.M_45s / hmi.M_720s, from
    fetch_vso physobs 'LOS_magnetic_field' or a JSOC export). Refuses files
    whose instrument is not HMI or whose units are not Gauss.

    lat_deg/lon_deg (heliographic Stonyhurst, west positive, the DONKI
    convention) with half_deg define the region box; omit them for the full
    disk only. |B| below noise_g is ignored in flux sums; strong_g sets the
    strong-field masks whose one-pixel dilations intersect on the PIL.

    Returns date_obs, pixel_km, disk_unsigned_flux_mx, region (unsigned /
    signed flux, max |B|, pil_length_mm, pil_flux_mx, n_pixels) or null,
    note, and the figure path when plot. Fluxes are line-of-sight without a
    mu correction: a lower bound away from disk center.
    """
    import astropy.units as u
    import numpy as np
    import sunpy.map
    from astropy.coordinates import SkyCoord
    from sunpy.coordinates import HeliographicStonyhurst

    from pathlib import Path
    if not Path(fits_file).is_file():
        return {"status": "error", "error": f"FITS not found: {fits_file}"}
    smap = sunpy.map.Map(fits_file)
    instr = (smap.instrument or "").upper()
    if "HMI" not in instr and "MDI" not in instr:
        return {"status": "error",
                "error": f"refusing: {fits_file} is {smap.instrument!r}, not an HMI/MDI "
                         "magnetogram (fetch_vso instrument='HMI', "
                         "physobs='LOS_magnetic_field')"}
    unit = str(smap.meta.get("bunit", "")).strip().lower()
    if unit and unit not in ("gauss", "g", "mx/cm^2", "mx/cm2"):
        return {"status": "error",
                "error": f"refusing: BUNIT={smap.meta.get('bunit')!r} is not Gauss — this "
                         "looks like an intensity or Doppler product, not a magnetogram"}
    if (lat_deg is None) != (lon_deg is None):
        return {"status": "error", "error": "give both lat_deg and lon_deg or neither"}

    b = np.asarray(smap.data, dtype=float)
    scale_arcsec = float(smap.scale[0].to_value(u.arcsec / u.pix))
    m_per_arcsec = float((smap.rsun_meters / smap.rsun_obs).to_value(u.m / u.arcsec))
    pixel_km = scale_arcsec * m_per_arcsec / 1e3
    pixel_area_cm2 = (pixel_km * 1e5) ** 2

    valid = np.isfinite(b)
    above_noise = valid & (np.abs(b) >= noise_g)
    disk_flux = float(np.sum(np.abs(b[above_noise])) * pixel_area_cm2)

    region = None
    box = None
    if lat_deg is not None:
        if abs(lat_deg) > 90 or abs(lon_deg) > 90 or not 0 < half_deg <= 30:
            return {"status": "error",
                    "error": "lat/lon must be within +/-90 deg and 0 < half_deg <= 30"}
        xs, ys = [], []
        for lon in (lon_deg - half_deg, lon_deg + half_deg):
            for lat in (lat_deg - half_deg, lat_deg + half_deg):
                coord = SkyCoord(lon * u.deg, lat * u.deg, frame=HeliographicStonyhurst,
                                 obstime=smap.date).transform_to(smap.coordinate_frame)
                px = smap.world_to_pixel(coord)
                xs.append(float(px.x.to_value(u.pix)))
                ys.append(float(px.y.to_value(u.pix)))
        if any(np.isnan(xs)) or any(np.isnan(ys)):
            return {"status": "error",
                    "error": f"region box ({lat_deg}, {lon_deg}) +/- {half_deg} deg is "
                             "behind the limb for this map"}
        x0, x1 = max(int(min(xs)), 0), min(int(max(xs)) + 1, b.shape[1])
        y0, y1 = max(int(min(ys)), 0), min(int(max(ys)) + 1, b.shape[0])
        if x1 <= x0 or y1 <= y0:
            return {"status": "error",
                    "error": f"region box ({lat_deg}, {lon_deg}) +/- {half_deg} deg projects "
                             "outside the map"}
        box = (x0, x1, y0, y1)
        sub = b[y0:y1, x0:x1]
        sub_valid = np.isfinite(sub)
        sub_noise = sub_valid & (np.abs(sub) >= noise_g)
        pil = strong_pil(sub, strong_g)
        region = {
            "unsigned_flux_mx": float(np.sum(np.abs(sub[sub_noise])) * pixel_area_cm2),
            "signed_flux_mx": float(np.sum(sub[sub_noise]) * pixel_area_cm2),
            "max_abs_b_g": float(np.nanmax(np.abs(sub))) if sub_valid.any() else 0.0,
            "pil_length_mm": round(float(pil.sum()) * pixel_km / 1e3, 1),
            "pil_flux_mx": float(np.sum(np.abs(np.where(pil, sub, 0.0))) * pixel_area_cm2),
            "n_pixels": int(sub_noise.sum()),
            "box_pixels": [x0, x1, y0, y1],
        }

    note = f"disk unsigned flux {disk_flux:.2e} Mx"
    if region is not None:
        note += (f"; region ({lat_deg:g}, {lon_deg:g}) +/- {half_deg:g} deg: "
                 f"{region['unsigned_flux_mx']:.2e} Mx unsigned, max |B| "
                 f"{region['max_abs_b_g']:.0f} G, strong PIL {region['pil_length_mm']:g} Mm "
                 f"({region['pil_flux_mx']:.2e} Mx threaded)")
    out = {"file_in": fits_file, "instrument": smap.instrument,
           "date_obs": str(smap.date.isot), "pixel_km": round(pixel_km, 1),
           "disk_unsigned_flux_mx": disk_flux, "region": region,
           "method": "sum |B_los| A_pix above noise_g (no mu correction); strong-PIL = "
                     "intersection of one-pixel dilations of the +/- strong_g masks",
           "note": note}
    if plot:
        # HMI arrays are stored camera-up (CROTA2 ~ 180 deg): flip for display
        # so solar north is up, and map the box into the flipped frame
        flip = abs(float(smap.meta.get("crota2", 0.0))) > 90.0
        out["file"] = _plot(b, box, strong_g, out_name, flip)
        out["artifacts"] = [out["file"]]
    return out


def _plot(b, box, strong_g, out_name, flip: bool = False) -> str:
    import numpy as np
    from matplotlib.patches import Rectangle
    from helio_agent.style import EVENT_COLOR, apply_style, figsize
    apply_style()
    import matplotlib.pyplot as plt

    w, _ = figsize("column")
    fig, ax = plt.subplots(figsize=(w * 1.5, w * 1.5))
    ny, nx = b.shape
    shown = b[::-1, ::-1] if flip else b
    ax.imshow(np.clip(shown, -500, 500), cmap="gray", origin="lower", vmin=-500, vmax=500)
    title = "HMI LOS magnetogram (+/-500 G, solar north up)"
    if box is not None:
        x0, x1, y0, y1 = box
        ys, xs = np.nonzero(strong_pil(b[y0:y1, x0:x1], strong_g))
        xs, ys = xs + x0, ys + y0
        if flip:
            x0, x1 = nx - x1, nx - x0
            y0, y1 = ny - y1, ny - y0
            xs, ys = nx - 1 - xs, ny - 1 - ys
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor=EVENT_COLOR,
                               lw=0.8))
        ax.scatter(xs, ys, s=0.6, color=EVENT_COLOR, alpha=0.9, linewidths=0)
        title += " — box + strong-PIL pixels"
    ax.set_title(title, fontsize=8)
    ax.set_xlabel("x (pixel)")
    ax.set_ylabel("y (pixel)")
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight", dpi=150)
    plt.close(fig)
    return str(fpath)
