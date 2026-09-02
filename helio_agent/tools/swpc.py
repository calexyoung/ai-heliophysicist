"""NOAA SWPC operational time-series retrieval.

Real-time/nowcast feeds — NOT science quality (see skills/datasources/noaa_swpc.md).
Use these when the science archives (NCEI, CDAWeb) do not yet cover the
requested interval, and say so in any report built on them.
"""

from __future__ import annotations

import requests

from helio_agent.http import cached_get
from helio_agent.registry import tool
from helio_agent.workspace import data_path

_UA = {"User-Agent": "helio-agent/0.1 (AI Heliophysicist)"}
_BASE = "https://services.swpc.noaa.gov"

_PRODUCTS = {
    "xray": f"{_BASE}/json/goes/primary/xrays-7-day.json",
    "plasma": f"{_BASE}/json/rtsw/rtsw_wind_1m.json",
    "mag": f"{_BASE}/json/rtsw/rtsw_mag_1m.json",
    "kp": f"{_BASE}/products/noaa-planetary-k-index.json",
}

_KEEP = {
    "plasma": ["proton_density", "proton_speed", "proton_temperature"],
    "mag": ["bt", "bx_gsm", "by_gsm", "bz_gsm"],
    "kp": ["Kp", "a_running"],
}


@tool(family="retrieve")
def fetch_swpc_timeseries(product: str, start: str | None = None,
                          end: str | None = None) -> dict:
    """Fetch a NOAA SWPC operational time series into a workspace CSV.

    product:
      'xray'   - GOES primary XRS 1-min flux, last 7 days -> columns xrsa, xrsb
                 (W/m^2, operational scale: use find_flares with swpc_scale=false)
      'plasma' - real-time solar wind (DSCOVR/ACE RTSW), last 3 days ->
                 density (1/cm^3), speed (km/s), temperature (K)
      'mag'    - real-time IMF, last 3 days -> bx/by/bz GSM, bt (nT)
      'kp'     - planetary K index (3-hourly)
    start/end: optional ISO UTC times to trim the feed's native window.

    Operational nowcast data: gaps, spikes, and later revisions are normal.
    """
    import pandas as pd

    if product not in _PRODUCTS:
        return {"status": "error",
                "error": f"unknown product {product!r}; one of {list(_PRODUCTS)}"}
    r = cached_get(_PRODUCTS[product], timeout=90, ttl_seconds=300)
    r.raise_for_status()
    raw = r.json()

    if product == "xray":
        df = pd.DataFrame(raw)
        df["time"] = pd.to_datetime(df["time_tag"]).dt.tz_localize(None)
        band = df["energy"].map({"0.05-0.4nm": "xrsa", "0.1-0.8nm": "xrsb"})
        df = (df.assign(band=band).pivot_table(index="time", columns="band",
                                               values="flux", aggfunc="first"))
        df.columns.name = None
        units = {"xrsa": "W/m^2", "xrsb": "W/m^2"}
    else:
        df = pd.DataFrame(raw)
        df["time"] = pd.to_datetime(df["time_tag"]).dt.tz_localize(None)
        source = str(df["source"].iloc[-1]) if "source" in df.columns else None
        df = df.set_index("time")[_KEEP[product]]
        df = df.apply(pd.to_numeric, errors="coerce")
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]  # feed repeats timestamps
        units = {"plasma": {"proton_density": "1/cm^3", "proton_speed": "km/s",
                            "proton_temperature": "K"},
                 "mag": {"bt": "nT", "bx_gsm": "nT", "by_gsm": "nT",
                         "bz_gsm": "nT"},
                 "kp": {"Kp": "0-9", "a_running": "index"}}[product]
        if source:
            units["source_spacecraft"] = source

    if start:
        df = df[df.index >= pd.Timestamp(start).tz_localize(None)]
    if end:
        df = df[df.index <= pd.Timestamp(end).tz_localize(None)]
    if df.empty:
        return {"status": "error",
                "error": "no records in requested window (feed covers only the "
                         "last 3-7 days)"}
    stamp = str(df.index[0])[:10]
    fpath = data_path(f"swpc_{product}_{stamp}.csv")
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "units": units, "time_range": [str(df.index[0]), str(df.index[-1])],
            "quality": "operational nowcast - not science quality",
            "artifacts": [str(fpath)]}


@tool(family="retrieve")
def fetch_solar_cycle(start: str = "2008-12", end: str | None = None,
                      include_prediction: bool = False) -> dict:
    """Fetch NOAA's Solar Cycle Progression (monthly sunspot number + F10.7).

    The observed record runs 1749-01 to the latest released month, one row per
    month: ssn (international monthly SSN), smoothed_ssn (13-month smoothed,
    lags ~6 months), f10.7 and smoothed_f10.7 (from 1947). NOAA's -1.0
    sentinel becomes NaN. start/end: 'YYYY-MM'. Default start 2008-12 is the
    cycle 24 minimum (cycles 24-25).

    include_prediction: also save the SWPC prediction (predicted_ssn with
    high/low bounds) to a second CSV.

    Summary includes the latest monthly value and the window's smoothed
    maximum (the cycle peak once smoothing has caught up).
    """
    import numpy as np
    import pandas as pd

    r = cached_get(f"{_BASE}/json/solar-cycle/observed-solar-cycle-indices.json",
                   timeout=90, ttl_seconds=6 * 3600)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df["time"] = pd.to_datetime(df["time-tag"], format="%Y-%m")
    df = (df.set_index("time")
            .drop(columns=["time-tag"])
            .replace(-1.0, np.nan)
            .sort_index())
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]
    if df.empty:
        return {"status": "error", "error": "no months in requested range"}
    fpath = data_path(f"solar_cycle_observed_{str(df.index[0])[:7]}.csv")
    df.to_csv(fpath, index_label="time")
    artifacts = [str(fpath)]

    result: dict = {
        "file": str(fpath), "n_records": len(df), "columns": list(df.columns),
        "latest_month": str(df.index[-1])[:7],
        "latest_ssn": float(df["ssn"].iloc[-1]),
        "previous_month_ssn": float(df["ssn"].iloc[-2]) if len(df) > 1 else None,
    }
    sm = df["smoothed_ssn"].dropna()
    if len(sm):
        result["smoothed_max_ssn"] = float(sm.max())
        result["smoothed_max_month"] = str(sm.idxmax())[:7]
        result["smoothed_through"] = str(sm.index[-1])[:7]

    if include_prediction:
        rp = cached_get(f"{_BASE}/json/solar-cycle/predicted-solar-cycle.json",
                        timeout=90, ttl_seconds=6 * 3600)
        rp.raise_for_status()
        dp = pd.DataFrame(rp.json())
        dp["time"] = pd.to_datetime(dp["time-tag"], format="%Y-%m")
        dp = dp.set_index("time").drop(columns=["time-tag"]).sort_index()
        ppath = data_path("solar_cycle_predicted.csv")
        dp.to_csv(ppath, index_label="time")
        artifacts.append(str(ppath))
        result["prediction_file"] = str(ppath)

    result["artifacts"] = artifacts
    result["note"] = ("monthly SSN is finalized with ~1 month lag; "
                      "smoothed_ssn lags ~6 months and defines cycle peaks")
    return result


@tool(family="discover")
def get_solar_regions() -> dict:
    """Current NOAA/SWPC numbered sunspot regions: location, magnetic class,
    area, spot count, and recent flare counts. Operational daily analysis."""
    r = cached_get(f"{_BASE}/json/solar_regions.json", timeout=60, ttl_seconds=3600)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        return {"n_results": 0, "regions": []}
    latest_date = max(row["observed_date"] for row in rows)
    regions = [
        {"region": row.get("region"), "location": row.get("location"),
         "carrington_longitude": row.get("carrington_longitude"),
         "area_millionths": row.get("area"),
         "spot_class": row.get("spot_class"),
         "mag_class": row.get("mag_class"),
         "number_spots": row.get("number_spots"),
         "c_flares": row.get("c_xray_events"),
         "m_flares": row.get("m_xray_events"),
         "x_flares": row.get("x_xray_events")}
        for row in rows if row["observed_date"] == latest_date
    ]
    return {"observed_date": latest_date, "n_results": len(regions),
            "regions": regions}
