"""Discover: find datasets, spacecraft, events, and imagery in the archives.

Wraps HDRL discovery services: CDAWeb dataset search, HelioData API, SSCWeb
spacecraft catalog, VSO instrument search, HEK and DONKI event catalogs.
All read-only; nothing here downloads bulk data (see retrieve.py).
"""

from __future__ import annotations

import requests

from helio_agent.http import cached_get
from helio_agent.registry import tool

_UA = {"User-Agent": "helio-agent/0.1 (AI Heliophysicist)"}
CDAS_BASE = "https://cdaweb.gsfc.nasa.gov/WS/cdasr/1/dataviews/sp_phys"
HELIODATA_API = "https://api.heliophysics.net/api"
DONKI_BASE = "https://kauai.ccmc.gsfc.nasa.gov/DONKI/WS/get"


@tool(family="discover")
def search_cdaweb_datasets(keyword: str, instrument_type: str | None = None,
                           max_results: int = 40) -> dict:
    """Search CDAWeb's ~3000 datasets by keyword (matches ID and label).

    keyword: substring matched case-insensitively against dataset ID and title.
    instrument_type: optional CDAWeb instrumentType filter,
        e.g. 'Magnetic Fields (space)', 'Plasma and Solar Wind', 'Particles (space)'.
    """
    params = {}
    if instrument_type:
        params["instrumentType"] = instrument_type
    r = cached_get(f"{CDAS_BASE}/datasets", params=params,
                   headers={"Accept": "application/json"},
                   timeout=60, ttl_seconds=24 * 3600)
    r.raise_for_status()
    sets = r.json().get("DatasetDescription", [])
    kw = keyword.lower()
    hits = []
    for d in sets:
        text = f"{d.get('Id','')} {d.get('Label','')}".lower()
        if kw in text:
            hits.append({
                "id": d.get("Id"),
                "label": d.get("Label"),
                "start": d.get("TimeInterval", {}).get("Start"),
                "end": d.get("TimeInterval", {}).get("End"),
                "notes_url": d.get("Notes"),
            })
    return {"n_results": len(hits), "datasets": hits[:max_results],
            "truncated": len(hits) > max_results}


@tool(family="discover")
def list_cdaweb_variables(dataset: str) -> dict:
    """List the variables (names, units, descriptions) of a CDAWeb dataset ID."""
    r = cached_get(f"{CDAS_BASE}/datasets/{dataset}/variables",
                   headers={"Accept": "application/json"}, timeout=60)
    r.raise_for_status()
    variables = [
        {"name": v.get("Name"), "description": v.get("LongDescription") or v.get("ShortDescription")}
        for v in r.json().get("VariableDescription", [])
    ]
    return {"dataset": dataset, "n_results": len(variables), "variables": variables}


@tool(family="discover")
def search_heliodata(query: str, max_results: int = 20) -> dict:
    """Freetext search of the HDRL HelioData catalog (>7800 datasets).

    Uses the alpha HelioData API (api.heliophysics.net). Falls back with a
    clear error if the alpha API is down; CDAWeb search still works then.
    """
    # The alpha API used to accept ?search=&limit= but now answers 405 to
    # ANY query parameter (observed 2026-09-05); the bare endpoint returns
    # the full ~7800-row catalog. So fetch once (cached a day) and filter
    # client-side — same behaviour, one honest network shape.
    r = cached_get(f"{HELIODATA_API}/datasets", timeout=90,
                   ttl_seconds=24 * 3600)
    r.raise_for_status()
    payload = r.json()
    items = payload if isinstance(payload, list) else payload.get("data") or payload.get("datasets") or []
    terms = [t for t in query.lower().split() if t]

    def _blob(it: dict) -> str:
        return " ".join(str(v) for v in it.values() if v is not None).lower()

    items = [it for it in items
             if isinstance(it, dict) and all(t in _blob(it) for t in terms)]
    results = []
    for it in items[:max_results]:
        if isinstance(it, dict):
            results.append({k: it.get(k) for k in ("id", "name", "title", "description", "mission")
                            if it.get(k) is not None})
    return {"n_results": len(results), "datasets": results, "api": HELIODATA_API}


@tool(family="discover")
def list_spacecraft() -> dict:
    """List spacecraft trackable in SSCWeb (~200), with IDs for ephemeris queries."""
    from sscws.sscws import SscWs
    ssc = SscWs()
    obs = ssc.get_observatories()["Observatory"]
    sats = [{"id": o["Id"], "name": o["Name"],
             "start": str(o.get("StartTime")), "end": str(o.get("EndTime"))}
            for o in obs]
    return {"n_results": len(sats), "spacecraft": sats}


@tool(family="discover")
def search_vso(start: str, end: str, instrument: str,
               wavelength_angstrom: float | None = None,
               max_results: int = 30) -> dict:
    """Search the Virtual Solar Observatory for solar imagery/data.

    start/end: ISO times, e.g. '2017-09-06T11:00:00'.
    instrument: e.g. 'AIA', 'HMI', 'LASCO', 'EIT', 'SECCHI', 'XRT'.
    wavelength_angstrom: for narrowband imagers (AIA: 94,131,171,193,211,304,335,1600).
    """
    import astropy.units as u
    from sunpy.net import Fido, attrs as a

    query = [a.Time(start, end), a.Instrument(instrument)]
    if wavelength_angstrom is not None:
        query.append(a.Wavelength(wavelength_angstrom * u.angstrom))
    res = Fido.search(*query)
    rows = []
    for table in res:
        for row in table[:max_results]:
            rec = {}
            for col in ("Start Time", "Instrument", "Wavelength", "Source", "Provider", "fileid"):
                if col in table.colnames:
                    rec[col.lower().replace(" ", "_")] = str(row[col])
            rows.append(rec)
    total = sum(len(t) for t in res)
    return {"n_results": total, "sample": rows[:max_results],
            "note": "use retrieve.fetch_vso with the same query to download"}


@tool(family="discover")
def search_hek_events(start: str, end: str, event_type: str = "FL",
                      max_results: int = 50) -> dict:
    """Query the Heliophysics Event Knowledgebase for solar events.

    event_type: HEK two-letter code — FL (flare), CE (CME), AR (active region),
    CH (coronal hole), FI (filament), SS (sunspot).
    """
    from sunpy.net import Fido, attrs as a

    res = Fido.search(a.Time(start, end), a.hek.EventType(event_type))
    events = []
    tbl = res["hek"] if "hek" in res.keys() else res[0]
    for row in tbl[:max_results]:
        ev = {}
        for col in ("event_starttime", "event_peaktime", "event_endtime",
                    "fl_goescls", "ar_noaanum", "frm_name", "obs_observatory",
                    "hgs_x", "hgs_y"):
            if col in tbl.colnames:
                val = row[col]
                ev[col] = str(val) if val is not None else None
        events.append(ev)
    return {"n_results": len(tbl), "events": events,
            "truncated": len(tbl) > max_results}


@tool(family="discover")
def search_donki(start_date: str, end_date: str, kind: str = "FLR") -> dict:
    """Query NASA CCMC's DONKI space-weather event database.

    kind: FLR (flares), CME, CMEAnalysis, GST (geomagnetic storms),
    IPS (interplanetary shocks), SEP, HSS (high speed streams), RBE, MPC.
    Dates: 'YYYY-MM-DD'.
    """
    r = cached_get(f"{DONKI_BASE}/{kind}",
                   params={"startDate": start_date, "endDate": end_date},
                   timeout=90, ttl_seconds=1800)  # DONKI grows through the day
    r.raise_for_status()
    if not r.text.strip():
        return {"n_results": 0, "events": [], "message": "DONKI returned no events"}
    events = r.json()
    keep_keys = {
        "FLR": ["flrID", "beginTime", "peakTime", "endTime", "classType",
                "sourceLocation", "activeRegionNum"],
        "CME": ["activityID", "startTime", "sourceLocation", "note"],
        "CMEAnalysis": ["time21_5", "latitude", "longitude", "halfAngle",
                        "speed", "type", "associatedCMEID"],
        "GST": ["gstID", "startTime", "allKpIndex"],
        "IPS": ["activityID", "eventTime", "location", "instruments"],
        "SEP": ["sepID", "eventTime", "instruments"],
        "HSS": ["hssID", "eventTime", "instruments"],
    }.get(kind)
    slim = []
    for ev in events:
        slim.append({k: ev.get(k) for k in keep_keys} if keep_keys else ev)
    return {"n_results": len(slim), "events": slim}


@tool(family="discover")
def get_noaa_realtime(product: str = "solar_wind") -> dict:
    """Current space-weather conditions from NOAA SWPC (operational real-time).

    product: 'solar_wind' (RTSW plasma+mag at L1), 'kp' (planetary K index),
    'xray' (GOES XRS latest fluxes), 'alerts' (active SWPC alerts).
    Real-time operational data — not science quality; see skills/datasources/noaa_swpc.md.
    """
    urls = {
        "solar_wind": [
            "https://services.swpc.noaa.gov/products/solar-wind/plasma-1-day.json",
            "https://services.swpc.noaa.gov/products/solar-wind/mag-1-day.json",
        ],
        "kp": ["https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"],
        "xray": ["https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json"],
        "alerts": ["https://services.swpc.noaa.gov/products/alerts.json"],
    }
    if product not in urls:
        return {"status": "error", "error": f"unknown product {product!r}; one of {list(urls)}"}
    out = {}
    for url in urls[product]:
        r = cached_get(url, timeout=60, ttl_seconds=300)
        r.raise_for_status()
        data = r.json()
        # products/*.json are list-of-lists with header row; json/*.json are dicts
        if isinstance(data, list) and data and isinstance(data[0], list):
            header, rows = data[0], data[1:]
            out[url.rsplit("/", 1)[-1]] = {"header": header, "last_rows": rows[-5:],
                                           "n_records": len(rows)}
        elif isinstance(data, list):
            # list-of-dicts feeds carry a timestamp field but differ in sort
            # order (alerts.json is newest-FIRST); sort explicitly instead of
            # trusting position, so "latest" always means latest.
            time_key = next((k for k in ("issue_datetime", "time_tag",
                                         "observed_time", "eventTime")
                             if data and isinstance(data[0], dict) and k in data[0]),
                            None)
            records = (sorted(data, key=lambda d: d.get(time_key) or "",
                              reverse=True)[:5] if time_key else data[-5:])
            out[url.rsplit("/", 1)[-1]] = {"latest_records": records,
                                           "sorted_by": time_key or "feed order",
                                           "n_records": len(data)}
        else:
            out[url.rsplit("/", 1)[-1]] = {"latest_records": data, "n_records": 1}
    return {"product": product, "data": out}
