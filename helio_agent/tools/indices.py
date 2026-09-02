"""Geomagnetic index sources beyond OMNI: Kyoto WDC Dst and GFZ Kp/Hp.

Why not just OMNI: OMNI's Dst/Kp are copies that lag and never carry the
revision state. Kyoto serves Dst by revision (final/provisional/real-time)
— cite which one you used. GFZ is the *producer* of Kp and also serves the
higher-cadence Hp30/Hp60 indices (keyless JSON API).
"""

from __future__ import annotations

import re

from helio_agent.http import cached_get
from helio_agent.registry import tool
from helio_agent.workspace import data_path

_KYOTO = "https://wdc.kugi.kyoto-u.ac.jp"
_GFZ = "https://kp.gfz.de/app/json/"
_GFZ_INDICES = ("Kp", "ap", "Ap", "Hp30", "Hp60", "ap30", "ap60", "SN", "Fobs")


@tool(family="retrieve")
def fetch_kyoto_dst(year: int, month: int, revision: str = "auto") -> dict:
    """Fetch one month of hourly Dst from Kyoto WDC into a CSV.

    revision: 'final', 'provisional', 'realtime', or 'auto' (try final ->
    provisional -> realtime and report which one answered). Final values are
    immutable; provisional/real-time get revised — always cite the revision.
    """
    import numpy as np
    import pandas as pd

    dirs = {"final": "dst_final", "provisional": "dst_provisional",
            "realtime": "dst_realtime"}
    order = ([revision] if revision in dirs else
             ["final", "provisional", "realtime"] if revision == "auto" else None)
    if order is None:
        return {"status": "error",
                "error": f"refusing: revision must be one of {list(dirs)} or 'auto'"}
    ym = f"{year:04d}{month:02d}"
    used, text = None, None
    for rev in order:
        r = cached_get(f"{_KYOTO}/{dirs[rev]}/{ym}/index.html",
                       timeout=90, allow_error=True,
                       ttl_seconds=None if rev == "final" else 6 * 3600)
        if r.ok and "DAY" in r.text:
            used, text = rev, r.text
            break
    if text is None:
        return {"status": "error",
                "error": f"refusing: Kyoto has no Dst for {ym} in {order} "
                         "(month too recent, too old, or service down)"}
    rows = []
    for line in text.splitlines():
        nums = re.findall(r"-?\d+", line)
        if len(nums) >= 25 and 1 <= int(nums[0]) <= 31:
            day, vals = int(nums[0]), [int(v) for v in nums[1:25]]
            for hour, v in enumerate(vals):
                rows.append((pd.Timestamp(year, month, day, hour),
                             np.nan if v in (9999, 99999) else float(v)))
    if not rows:
        return {"status": "error", "error": "Kyoto page found but no data rows parsed"}
    df = pd.DataFrame(rows, columns=["time", "Dst"]).set_index("time").sort_index()
    fpath = data_path(f"kyoto_dst_{ym}_{used}.csv")
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df), "revision": used,
            "units": {"Dst": "nT"}, "dst_min_nT": float(df["Dst"].min()),
            "columns": ["Dst"], "artifacts": [str(fpath)],
            "note": "hourly Dst; cite the revision in any report"}


@tool(family="retrieve")
def fetch_gfz_index(index: str, start: str, end: str) -> dict:
    """Fetch a geomagnetic activity index from GFZ Potsdam (the Kp producer).

    index: Kp (3-hourly), ap, Ap (daily), Hp30/Hp60 (30/60-min Kp-like,
    open-ended above 9 - resolves storm structure Kp cannot), ap30/ap60,
    SN (sunspot number), Fobs (F10.7). start/end: ISO dates or datetimes.
    Keyless JSON API; status column 'def' = definitive, 'nowcast' = may revise.
    """
    import pandas as pd

    if index not in _GFZ_INDICES:
        return {"status": "error",
                "error": f"refusing: index must be one of {_GFZ_INDICES}"}
    def _iso(t: str, end_of_day: bool) -> str:
        if "T" in t:
            return t if t.endswith("Z") else t + "Z"
        return f"{t}T23:59:59Z" if end_of_day else f"{t}T00:00:00Z"
    r = cached_get(_GFZ, params={"start": _iso(start, False),
                                 "end": _iso(end, True), "index": index},
                   timeout=90, ttl_seconds=6 * 3600)
    r.raise_for_status()
    payload = r.json()
    times = payload.get("datetime") or []
    vals = payload.get(index) or []
    if not times:
        return {"status": "error",
                "error": f"refusing: GFZ returned no {index} records for "
                         f"{start}..{end} (index starts 1932 for Kp, "
                         "1995 for Hp30/Hp60)"}
    df = pd.DataFrame({index: vals},
                      index=pd.to_datetime(times).tz_localize(None))
    df.index.name = "time"
    if "status" in payload:
        df["status"] = payload["status"]
    fpath = data_path(f"gfz_{index.lower()}_{str(df.index[0])[:10]}.csv")
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df),
            "columns": list(df.columns),
            "max_value": float(pd.to_numeric(df[index], errors="coerce").max()),
            "time_range": [str(df.index[0]), str(df.index[-1])],
            "artifacts": [str(fpath)]}
