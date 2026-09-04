"""CCMC model output via the ISWA HAPI server (discover + retrieve).

The repo's own models are analytic: `model_dst` is O'Brien & McPherron's
ring-current integral, `cme_arrival` is the drag-based CME model. CCMC runs
full MHD — SWMF/BATS-R-US coupled to a ring current and ionosphere — in real
time and archives the output. This wires that in so a model nowcast can be
compared against observations and against the analytic models with the same
tooling.

Everything here is **model output, not measurement.** The result labels it,
and the note repeats it. A modelled Dst is a simulation of Dst driven by
whatever L1 data existed at run time; it is not an index.

What is actually available
--------------------------
* **SWMF is the substance.** Real-time runs going back to 2007 across three
  model versions (2008, 2011, 2023): ring-current Dst, geomagnetic indices
  (Kp/AE/AL/AO/AU), magnetopause standoff distance, and field/plasma
  sampled at GOES, THEMIS and the Moon.
* **ENLIL here is historical only.** The ISWA HAPI catalog carries an
  ENLIL-derived Kp series that ended 2015-01-09 and a New Horizons flyby
  run from 2015. There is no live ENLIL solar-wind or CME product on this
  server — the operational WSA-ENLIL cone-model runs are served as images
  and volumes, not HAPI time series, and their CME arrival predictions come
  through DONKI (`search_donki`) instead. `fetch_model_output` says so
  rather than returning an empty frame.

Gotchas
-------
* **Catalog presence does not mean current.** A dataset can sit in the
  catalog years after its last sample: SWMF2023's Dst log stopped
  2025-12-16 while its geomagnetic-index log runs to today. Coverage is
  read live from the server on every call and a stale product is flagged,
  never silently returned as a nowcast.
* Run versions overlap in time and disagree. For the 2024-05-10 storm
  SWMF2023 gives a Dst minimum of -316 nT at 03:28 UT and SWMF2011 -372 nT
  at 08:25 UT, against an observed SYM-H of -518 nT at 02:14 UT. Pin `run`
  when reproducibility matters; the default picks the newest run that
  covers the window and records which it used.
* **Real-time MHD underpredicts extreme storms.** Expect the modelled depth
  to fall well short for a great storm even when the timing is good.
* ISWA parameter names are its own (`dst`, `KP`, `mp_standoff_noon_lt`,
  `B_x`). Columns are renamed here to `swmf_*` so model and observation can
  be merged without a name collision.
"""

from __future__ import annotations

from helio_agent.http import cached_get
from helio_agent.registry import tool
from helio_agent.workspace import data_path

ISWA_HAPI = "https://iswa.ccmc.gsfc.nasa.gov/IswaSystemWebApp/hapi"

# (model, product) -> variants, newest run first. Each variant names the ISWA
# dataset, the parameters to pull, and the column names they become.
_PRODUCTS: dict[tuple[str, str], list[dict]] = {
    ("swmf", "dst"): [
        {"run": "2023", "dataset": "SWMF2023_RT_GMlog_P1M",
         "parameters": "dst,cpcpn,cpcps",
         "columns": {"dst": "swmf_dst", "cpcpn": "swmf_cpcp_north",
                     "cpcps": "swmf_cpcp_south"}},
        {"run": "2011", "dataset": "SWMF2011_RT_DST_P1M",
         "parameters": "dst", "columns": {"dst": "swmf_dst"}},
        {"run": "2008", "dataset": "SWMF2008_RT_DST_P1M",
         "parameters": "dst", "columns": {"dst": "swmf_dst"}},
    ],
    ("swmf", "geoindices"): [
        {"run": "2023", "dataset": "SWMF2023_RT_GEOIndices_P1M",
         "parameters": "KP,AE,AL,AO,AU",
         "columns": {"KP": "swmf_kp", "AE": "swmf_ae", "AL": "swmf_al",
                     "AO": "swmf_ao", "AU": "swmf_au"}},
    ],
    ("swmf", "standoff"): [
        {"run": "2023", "dataset": "SWMF2023_RT_STANDOFF_P1M",
         "parameters": "mp_standoff_noon_lt,mp_standoff_min,geosynchronus_orbit",
         "columns": {"mp_standoff_noon_lt": "swmf_mp_standoff_noon_re",
                     "mp_standoff_min": "swmf_mp_standoff_min_re",
                     "geosynchronus_orbit": "swmf_geosync_inside_mp"}},
        {"run": "2011", "dataset": "SWMF2011_RT_MP_STANDOFF_P5M",
         "parameters": "mp_standoff_noon_lt,mp_standoff_min,geosynchronus_orbit",
         "columns": {"mp_standoff_noon_lt": "swmf_mp_standoff_noon_re",
                     "mp_standoff_min": "swmf_mp_standoff_min_re",
                     "geosynchronus_orbit": "swmf_geosync_inside_mp"}},
        {"run": "2008", "dataset": "SWMF2008_RT_MP_STANDOFF_P5M",
         "parameters": "mp_standoff_noon_lt,mp_standoff_min,geosynchronus_orbit",
         "columns": {"mp_standoff_noon_lt": "swmf_mp_standoff_noon_re",
                     "mp_standoff_min": "swmf_mp_standoff_min_re",
                     "geosynchronus_orbit": "swmf_geosync_inside_mp"}},
    ],
    ("swmf", "goes_field"): [
        {"run": "2011", "dataset": "SWMF2011_RT_MagneticFieldatGOES{sat}",
         "parameters": "B_x,B_y,B_z,N,V_x", "satellites": ("13", "14", "15"),
         "columns": {"B_x": "swmf_bx_gsm", "B_y": "swmf_by_gsm",
                     "B_z": "swmf_bz_gsm", "N": "swmf_n",
                     "V_x": "swmf_vx_gsm"}},
        {"run": "2008", "dataset": "SWMF2008_RT_MagneticFieldatGOES{sat}",
         "parameters": "B_x,B_y,B_z,N,V_x", "satellites": ("13", "14", "15"),
         "columns": {"B_x": "swmf_bx_gsm", "B_y": "swmf_by_gsm",
                     "B_z": "swmf_bz_gsm", "N": "swmf_n",
                     "V_x": "swmf_vx_gsm"}},
    ],
    ("swmf", "themis"): [
        {"run": "2023", "dataset": "SWMF2023_RT_THEMIS{sat}",
         "parameters": "N,V_x,V_y,V_z,B_x,B_y,B_z",
         "satellites": ("A", "B", "C", "D", "E"),
         "columns": {"N": "swmf_n", "V_x": "swmf_vx", "V_y": "swmf_vy",
                     "V_z": "swmf_vz", "B_x": "swmf_bx", "B_y": "swmf_by",
                     "B_z": "swmf_bz"}},
    ],
    ("enlil", "kp"): [
        {"run": "legacy", "dataset": "ENLIL_KP_P7M",
         "parameters": "KP_18,KP_90,KP_180",
         "columns": {"KP_18": "enlil_kp_18", "KP_90": "enlil_kp_90",
                     "KP_180": "enlil_kp_180"}},
    ],
}

_STALE_DAYS = 30.0


def _info(dataset: str) -> dict | None:
    """Live coverage/parameter metadata for one ISWA dataset."""
    try:
        r = cached_get(f"{ISWA_HAPI}/info", params={"id": dataset},
                       timeout=60, ttl_seconds=3600, allow_error=True)
        if getattr(r, "status_code", 200) >= 400:
            return None
        j = r.json()
        return j if j.get("parameters") else None
    except Exception:  # noqa: BLE001
        return None


def available_products() -> list[tuple[str, str]]:
    return sorted(_PRODUCTS)


@tool(family="discover")
def list_model_outputs(model: str | None = None) -> dict:
    """CCMC model products on ISWA, with live coverage and a staleness flag.

    Coverage is read from the ISWA server on every call rather than baked in,
    because presence in the catalog does not mean a product is still running:
    SWMF2023's Dst log stopped in 2025-12 while its geomagnetic-index log is
    current. Each entry reports `stale` (no data in 30 days) so a dead run is
    never mistaken for a nowcast.

    model: 'swmf' or 'enlil' to filter. Returns `products`, each with the
    ISWA dataset id, the run version, coverage, `stale`, `days_behind`, and
    the column names `fetch_model_output` will produce.
    """
    from datetime import datetime, timezone

    import pandas as pd

    now = datetime.now(timezone.utc)
    out = []
    for (mdl, product), variants in sorted(_PRODUCTS.items()):
        if model and mdl != model.lower():
            continue
        for v in variants:
            ds = v["dataset"]
            probe = ds.format(sat=v["satellites"][0]) if "{sat}" in ds else ds
            info = _info(probe)
            entry = {"model": mdl, "product": product, "run": v["run"],
                     "dataset": probe, "columns": sorted(v["columns"].values())}
            if v.get("satellites"):
                entry["satellites"] = list(v["satellites"])
            if info is None:
                entry.update({"available": False,
                              "reason": "ISWA returned no metadata"})
            else:
                stop = info.get("stopDate")
                days = None
                if stop:
                    days = (now - pd.Timestamp(stop).to_pydatetime()
                            .replace(tzinfo=timezone.utc)).total_seconds() / 86400
                entry.update({"available": True,
                              "start": info.get("startDate"),
                              "stop": stop,
                              "days_behind": None if days is None else round(days, 1),
                              "stale": bool(days is not None and days > _STALE_DAYS)})
            out.append(entry)
    live = [e for e in out if e.get("available") and not e.get("stale")]
    return {"products": out, "n_products": len(out), "n_live": len(live),
            "server": ISWA_HAPI,
            "note": ("CCMC model output, not measurement. `stale` means no "
                     f"data in {_STALE_DAYS:.0f} days — the ENLIL entries are "
                     "historical only; live ENLIL CME arrival predictions come "
                     "from DONKI via search_donki.")}


@tool(family="retrieve")
def fetch_model_output(model: str, product: str, start: str, end: str,
                       run: str | None = None, satellite: str | None = None,
                       allow_stale: bool = False) -> dict:
    """Fetch a CCMC model time series from ISWA into a workspace CSV.

    model / product: see `list_model_outputs`. SWMF products are 'dst'
      (ring-current Dst plus cross-polar-cap potentials), 'geoindices'
      (Kp, AE, AL, AO, AU), 'standoff' (magnetopause standoff in Re, and
      whether geosynchronous orbit is outside it), 'goes_field' and 'themis'
      (modelled field and plasma at those spacecraft).
    run: model version ('2023', '2011', '2008'). Default picks the newest run
      whose coverage contains the window, and the result says which.
    satellite: required for 'goes_field' ('13'/'14'/'15') and 'themis'
      ('A'..'E').
    allow_stale: a product with no data for 30 days is refused unless this is
      set — a dead real-time run must not be passed off as a nowcast.

    Columns are renamed to `swmf_*` / `enlil_*` so model output can be merged
    against observations without colliding. **This is simulation output.**
    Real-time MHD underpredicts extreme storms: for 2024-05-10 SWMF2023 gives
    a Dst minimum of -316 nT against an observed SYM-H of -518 nT.
    """
    import pandas as pd

    key = (model.lower().strip(), product.lower().strip())
    if key not in _PRODUCTS:
        return {"status": "error",
                "error": f"no product {product!r} for model {model!r}; "
                         f"available: "
                         + ", ".join(f"{m}/{p}" for m, p in available_products())}
    if key[0] == "enlil":
        note_enlil = ("ISWA's HAPI ENLIL holdings are historical only "
                      "(the Kp series ends 2015-01-09). For live WSA-ENLIL "
                      "CME arrival predictions use search_donki(kind='CME') "
                      "— they are not served as HAPI time series.")
    else:
        note_enlil = None

    try:
        t0, t1 = pd.Timestamp(start), pd.Timestamp(end)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"bad timestamp: {exc}"}
    if t1 <= t0:
        return {"status": "error", "error": "end must be after start"}

    variants = _PRODUCTS[key]
    if run:
        variants = [v for v in variants if v["run"] == str(run)]
        if not variants:
            return {"status": "error",
                    "error": f"no run {run!r} for {model}/{product}; runs: "
                             + ", ".join(v["run"] for v in _PRODUCTS[key])}

    tried, chosen, info = [], None, None
    for v in variants:
        ds = v["dataset"]
        if v.get("satellites"):
            if satellite is None:
                return {"status": "error",
                        "error": f"{model}/{product} needs `satellite`, one of "
                                 + ", ".join(v["satellites"])}
            if str(satellite).upper() not in v["satellites"]:
                return {"status": "error",
                        "error": f"satellite {satellite!r} not in "
                                 + ", ".join(v["satellites"])}
            ds = ds.format(sat=str(satellite).upper())
        meta = _info(ds)
        if meta is None:
            tried.append(f"{ds}: no metadata")
            continue
        a, b = pd.Timestamp(meta.get("startDate")), pd.Timestamp(meta.get("stopDate"))
        if t0 >= b or t1 <= a:
            tried.append(f"{v['run']} covers {str(a)[:10]}..{str(b)[:10]}")
            continue
        chosen, info, dataset_id = v, meta, ds
        break
    if chosen is None:
        return {"status": "error",
                "error": f"no {model}/{product} run covers {start[:10]}.."
                         f"{end[:10]} — " + "; ".join(tried)}

    stop = pd.Timestamp(info["stopDate"])
    days_behind = (pd.Timestamp.utcnow().tz_localize(None)
                   - stop.tz_localize(None)).total_seconds() / 86400
    stale = days_behind > _STALE_DAYS
    if stale and not allow_stale:
        return {"status": "error",
                "error": f"{dataset_id} last produced data {stop} "
                         f"({days_behind:.0f} days ago) — this real-time run "
                         "has stopped, so its output is not a nowcast. Pass "
                         "allow_stale=True to use it as an archive, or call "
                         "list_model_outputs to find a live run."}

    from helio_agent.registry import get_tool
    got = get_tool("fetch_hapi").func(
        server=ISWA_HAPI, dataset=dataset_id,
        parameters=chosen["parameters"], start=start, end=end)
    if got.get("status") == "error":
        return {"status": "error",
                "error": f"ISWA fetch failed for {dataset_id}: {got.get('error')}"}

    df = pd.read_csv(got["file"], index_col=0, parse_dates=True)
    df = df.rename(columns=chosen["columns"])
    fname = f"ISWA_{dataset_id}_{start[:10]}_{end[:10]}.csv".replace("/", "-")
    fpath = data_path(fname)
    df.to_csv(fpath, index_label="time")

    note = (f"{model.upper()} run {chosen['run']} ({dataset_id}) — MODEL "
            "OUTPUT, not measurement. Real-time MHD underpredicts extreme "
            "storms; compare against an observed index before quoting.")
    if stale:
        note += (f" ARCHIVE ONLY: this run stopped {stop} "
                 f"({days_behind:.0f} days ago).")
    if note_enlil:
        note += " " + note_enlil
    return {"file": str(fpath), "n_records": len(df),
            "columns": list(df.columns), "model": model.lower(),
            "product": product.lower(), "run": chosen["run"],
            "dataset": dataset_id, "satellite": satellite,
            "coverage": [info.get("startDate"), info.get("stopDate")],
            "stale": stale, "days_behind": round(days_behind, 1),
            "is_model_output": True, "note": note,
            "artifacts": [str(fpath)]}
