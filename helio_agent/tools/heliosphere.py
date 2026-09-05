"""Heliospheric spacecraft configuration and magnetic connection (report).

Where an eruption goes depends on where the observers are. This renders the
constellation the way multi-spacecraft studies do: each body at its
Carrington longitude and heliocentric distance, with the Parker spiral that
magnetically connects it back to the solar surface.

The spiral matters more than the positions. A spacecraft at 45 degrees from
Earth in longitude is NOT 45 degrees away in magnetic connection: the field
line winds back to a footpoint that depends on the solar wind speed, and at
storm-time speeds (~1000 km/s) the spiral unwinds substantially compared
with the nominal 400 km/s case. Two observers close in longitude can be
connected to opposite sides of the Sun, and vice versa.

Wraps `solarmach` (Gieseler et al. 2023, Front. Astron. Space Sci. 9,
1058810), an optional dependency: install with `uv sync --extra extra`.

Gotchas
-------
* **Solar wind speed is an input, not a detail.** The footpoint longitude
  scales with it. Passing one speed for every body assumes a uniform
  heliosphere; during a storm that is wrong in a known direction, and the
  result records the speeds used so a figure cannot be read without them.
* Carrington longitude rotates with the Sun, so a configuration is only
  meaningful at one instant. The date is stamped on the figure.
* Body names are solarmach's ('STEREO-A', 'Solar Orbiter', 'PSP', 'BepiColombo').
  An unknown name is refused with the list rather than silently dropped.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import output_path


@tool(family="report")
def plot_heliospheric_config(date: str, bodies: list[str] | None = None,
                             solar_wind_kms: float = 400.0,
                             body_speeds_kms: list[float] | None = None,
                             reference_longitude: float | None = None,
                             out_name: str = "heliospheric_config.png") -> dict:
    """Spacecraft constellation with Parker spirals at one instant.

    date: ISO instant; Carrington longitudes are only meaningful at one time.
    bodies: solarmach names, e.g. ['Earth', 'STEREO-A', 'Solar Orbiter',
      'PSP', 'BepiColombo', 'Mars']. Defaults to the inner-heliosphere set.
    solar_wind_kms: one speed for every body (the usual simplification).
    body_speeds_kms: per-body speeds instead, same order as `bodies` — use
      real measurements when you have them; the spiral footpoint depends on
      this directly.
    reference_longitude: draw a reference spiral from this Carrington
      longitude, e.g. a flare's source longitude, to see which spacecraft
      the eruption was magnetically connected to.

    Returns the figure path plus a `positions` table: Carrington longitude
    and latitude, heliocentric distance, the magnetic footpoint longitude
    each spiral traces back to, and the longitudinal separation from the
    first body listed.
    """
    import pandas as pd

    try:
        from solarmach import SolarMACH
    except ImportError:
        return {"status": "error",
                "error": "solarmach is not installed (it is an optional "
                         "dependency): run `uv sync --extra extra`"}

    bodies = bodies or ["Earth", "STEREO-A", "Solar Orbiter", "PSP",
                        "BepiColombo"]
    if body_speeds_kms is not None and len(body_speeds_kms) != len(bodies):
        return {"status": "error",
                "error": f"{len(bodies)} bodies but {len(body_speeds_kms)} "
                         "speeds; give one per body or use solar_wind_kms"}
    vsw = list(body_speeds_kms) if body_speeds_kms else [
        float(solar_wind_kms)] * len(bodies)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        sm = SolarMACH(date=str(date), body_list=list(bodies),
                       vsw_list=vsw, coord_sys="Carrington",
                       reference_long=reference_longitude)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error",
                "error": f"solarmach refused this configuration: {exc}. Body "
                         "names must be solarmach's (Earth, STEREO-A, "
                         "Solar Orbiter, PSP, BepiColombo, Mars, ...)"}
    fpath = output_path(out_name)
    # solarmach writes the file itself; `outfile` defaults to '' (not None),
    # and passing None makes it call .split() on nothing. It also owns its own
    # polar axes, so do not impose the repo's rectangular time-series style.
    sm.plot(plot_spirals=True, plot_sun_body_line=True,
            reference_vsw=float(solar_wind_kms), transparent=False,
            markers="letters", long_offset=270, outfile=str(fpath))
    plt.close("all")

    table = sm.coord_table
    df = table if isinstance(table, pd.DataFrame) else pd.DataFrame(table)
    cols = {c.lower().strip(): c for c in df.columns}

    def col(*names):
        for n in names:
            for k, orig in cols.items():
                if n in k:
                    return orig
        return None

    c_name = col("spacecraft", "body")
    c_lon = col("carrington longitude")
    c_lat = col("carrington latitude")
    c_r = col("heliocentric distance")
    c_foot = col("footpoint")
    positions = []
    ref_lon = None
    for _, row in df.iterrows():
        lon = float(row[c_lon]) if c_lon else None
        if ref_lon is None:
            ref_lon = lon
        sep = None
        if lon is not None and ref_lon is not None:
            sep = abs((lon - ref_lon + 180.0) % 360.0 - 180.0)
        positions.append({
            "body": str(row[c_name]) if c_name else "?",
            "carrington_longitude_deg": lon,
            "carrington_latitude_deg": float(row[c_lat]) if c_lat else None,
            "distance_au": float(row[c_r]) if c_r else None,
            "footpoint_longitude_deg": (float(row[c_foot]) if c_foot
                                        and pd.notna(row[c_foot]) else None),
            "separation_from_first_deg": None if sep is None else round(sep, 1),
        })
    return {"file": str(fpath), "date": str(date), "bodies": list(bodies),
            "solar_wind_kms": vsw, "positions": positions,
            "reference_longitude": reference_longitude,
            "note": ("Carrington longitudes are instantaneous. Parker-spiral "
                     "footpoints depend directly on the solar wind speed used "
                     f"({sorted(set(vsw))} km/s here) — longitudinal "
                     "separation is NOT magnetic separation."),
            "citation": ("solarmach: Gieseler et al. 2023, Front. Astron. "
                         "Space Sci. 9, 1058810"),
            "artifacts": [str(fpath)]}
