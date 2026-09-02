"""Geospace tools: coordinate transforms and magnetospheric field-line tracing.

Transforms use pySPEDAS's cotrans (GEI/GSE/GSM/SM/GEO/MAG/J2000, dipole
orientation recomputed per sample). Tracing uses geopack (Tsyganenko T89 +
IGRF). Read skills/methods/coordinate_systems.md before choosing frames.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import data_path

_FRAMES = ("gei", "gse", "gsm", "sm", "geo", "mag", "j2000")


@tool(family="reduce")
def transform_coordinates(file: str, columns: list[str], from_coords: str,
                          to_coords: str, out_name: str | None = None) -> dict:
    """Rotate a 3-component vector time series between geocentric frames.

    file: workspace CSV; columns: exactly three column names [x, y, z] in
    from_coords. Frames: gei, gse, gsm, sm, geo, mag, j2000 (pySPEDAS
    cotrans; dipole recomputed per sample). Output adds columns suffixed
    _<to_coords>. Works for any vector (position km, field nT) — magnitude
    is preserved by construction.
    """
    import numpy as np
    import pandas as pd

    from_c, to_c = from_coords.lower(), to_coords.lower()
    if from_c not in _FRAMES or to_c not in _FRAMES:
        return {"status": "error",
                "error": f"refusing: frames must be one of {_FRAMES}"}
    if len(columns) != 3:
        return {"status": "error", "error": "refusing: need exactly 3 columns [x, y, z]"}

    import pyspedas
    from pyspedas import cotrans, get_data, store_data

    df = pd.read_csv(file, index_col="time", parse_dates=True)
    missing = [c for c in columns if c not in df.columns]
    if missing:
        return {"status": "error",
                "error": f"refusing: columns {missing} not in file; "
                         f"available: {list(df.columns)}"}
    sub = df[columns].dropna()
    # resolution-proof unix seconds (index may be datetime64[us] or [ns]);
    # explicit copies: pandas CoW arrays are read-only and cotrans mutates
    times = np.array((sub.index - pd.Timestamp(0)) / pd.Timedelta(seconds=1),
                     dtype=float)
    store_data("_helio_cotrans_in",
               data={"x": times, "y": np.array(sub.values, dtype=float)})
    ok = cotrans(name_in="_helio_cotrans_in", name_out="_helio_cotrans_out",
                 coord_in=from_c, coord_out=to_c)
    if not ok:
        return {"status": "error", "error": "cotrans failed; see log output"}
    d = get_data("_helio_cotrans_out")
    out_vals = np.asarray(d.y)
    axes = ("x", "y", "z")
    for i, ax in enumerate(axes):
        df.loc[sub.index, f"{ax}_{to_c}"] = out_vals[:, i]
    fname = out_name or file.rsplit("/", 1)[-1].replace(".csv", f"_{to_c}.csv")
    fpath = data_path(fname)
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": int(len(sub)),
            "new_columns": [f"{ax}_{to_c}" for ax in axes],
            "from": from_c, "to": to_c, "artifacts": [str(fpath)]}


@tool(family="measure")
def trace_field_line(x_gsm_re: float, y_gsm_re: float, z_gsm_re: float,
                     time: str, kp: int = 2) -> dict:
    """Trace the magnetic field line through a GSM point (Tsyganenko T89 + IGRF).

    Position in Earth radii (GSM); time ISO UTC (sets dipole orientation);
    kp 0-6 selects the T89 activity level. Returns both footpoints (GEO
    latitude/longitude at r=1 Re) and whether the line is closed (both ends
    reach Earth), open (one end), or not traced (neither within 30 Re).

    T89 is a quiet-to-moderate empirical model — do not trust footpoints
    during storm main phases; see skills/methods/coordinate_systems.md.
    """
    import numpy as np
    import pandas as pd
    from geopack import geopack

    if not 0 <= kp <= 6:
        return {"status": "error", "error": "refusing: T89 accepts Kp 0-6 (iopt=kp+1)"}
    ts = pd.Timestamp(time)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC").tz_localize(None)
    ut = (ts - pd.Timestamp(0)) / pd.Timedelta(seconds=1)  # naive = UTC here
    ps = geopack.recalc(ut)

    def foot(direction: int):
        x, y, z, *_ = geopack.trace(x_gsm_re, y_gsm_re, z_gsm_re, dir=direction,
                                    rlim=30.0, r0=1.0, parmod=kp + 1,
                                    exname="t89", inname="igrf")
        r = float(np.sqrt(x * x + y * y + z * z))
        if abs(r - 1.0) > 0.05:
            return None
        # GSM -> GEO for footpoint lat/lon
        xgeo, ygeo, zgeo = geopack.geogsm(x, y, z, -1)
        lat = float(np.degrees(np.arcsin(zgeo / r)))
        lon = float(np.degrees(np.arctan2(ygeo, xgeo))) % 360
        return {"geo_lat_deg": round(lat, 2), "geo_lon_deg": round(lon, 2)}

    north = foot(-1)   # antiparallel to B -> northern hemisphere
    south = foot(1)
    topology = ("closed" if north and south
                else "open" if north or south else "not reached (r>30 Re)")
    return {"time": str(pd.Timestamp(time)), "kp": kp,
            "dipole_tilt_deg": round(float(np.degrees(ps)), 2),
            "north_footpoint": north, "south_footpoint": south,
            "topology": topology,
            "model": "T89 (external) + IGRF (internal)"}
