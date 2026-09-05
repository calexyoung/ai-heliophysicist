"""Standing space-weather watch with a scored forecast ledger.

Pattern from helio-agent's monitor/forecast pipelines: one entry point
(`helio-agent monitor`) suitable for cron. Each cycle:

1. reads current conditions (Kp, GOES XRS) from NOAA SWPC;
2. imports new DONKI CMEs; for Earth-directed analyses, issues a drag-based
   arrival forecast (cme_arrival) and stores the window as PENDING;
3. matures pending forecasts whose window has passed: a DONKI Earth IPS or
   GST inside the window (+/- grace) scores a HIT, otherwise a MISS —
   forecasts are never silently forgotten;
4. records new DONKI geomagnetic storms.

State lives in workspace/monitor_state.json; every data access goes through
audited tools, so a cycle is reconstructible from the audit trail.
Forecast skill accumulates in state["ledger"] — report hit rates from there,
never from memory.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from helio_agent.registry import run_tool
from helio_agent.workspace import WORKSPACE

STATE_FILE = WORKSPACE / "monitor_state.json"
# Half-width of the Earth-directed cone, in degrees from the Sun-Earth line.
# 45, not 60: hindcast over four months (May/Oct/Mar 2024, Jun 2025; 163
# windows, 12 storms) cuts false alarms 74 -> 55 while covering exactly the
# same 9 of 12 storms. Tighter is NOT safe — 30 deg, or any launch-speed
# floor, drops June 2025's only covered storm (a 249 km/s CME at 41 deg that
# drove Kp 6.33), taking that month's recall to zero. Missing a storm costs
# more than a false alarm, so recall neutrality is the constraint and
# `hindcast.recall_neutral` pins it.
EARTH_DIRECTED_MAX_LON = 45.0
GRACE_HOURS = 12.0


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"seen_cme_ids": [], "seen_gst_ids": [],
            "pending_forecasts": [], "ledger": []}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=1, default=str))
    temporary.replace(STATE_FILE)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cycle(lookback_days: int = 3) -> dict:
    state = _load_state()
    now = _now()
    summary: dict = {"cycle_time": now.isoformat(), "new_cmes": [],
                     "new_forecasts": [], "matured": [], "new_storms": [],
                     "failed_sources": []}
    required_source_failed = False

    def fetch(tool: str, *, required: bool = False, **kwargs) -> dict:
        nonlocal required_source_failed
        try:
            result = run_tool(tool, **kwargs)
        except Exception as exc:  # noqa: BLE001 - monitor must persist health
            result = {"status": "error", "error": str(exc)}
        if result.get("status") != "ok":
            summary["failed_sources"].append({
                "tool": tool,
                "request": kwargs,
                "error": result.get("error", "source request failed"),
                "required": required,
            })
            required_source_failed = required_source_failed or required
        return result

    # 1. current conditions
    kp = fetch("get_noaa_realtime", product="kp")
    xray = fetch("get_noaa_realtime", product="xray")
    conditions = {}
    try:
        blob = kp["data"]["noaa-planetary-k-index.json"]
        if "last_rows" in blob:            # legacy list-of-lists feed
            conditions["kp_latest"] = float(blob["last_rows"][-1][1])
        else:                              # latest_records is sorted newest-first
            conditions["kp_latest"] = float(blob["latest_records"][0]["Kp"])
    except Exception:  # noqa: BLE001
        conditions["kp_latest"] = None
    try:
        recs = xray["data"]["xrays-1-day.json"]["latest_records"]
        # feed interleaves both XRS channels per timestamp; flare class is
        # defined on the long channel (0.1-0.8 nm)
        rec = next((r for r in recs if r.get("energy") == "0.1-0.8nm"), recs[0])
        conditions["xray_flux_wm2"] = rec.get("flux")
    except Exception:  # noqa: BLE001
        conditions["xray_flux_wm2"] = None
    summary["conditions"] = conditions

    start = (now - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    # 2. new CMEs -> forecasts
    analyses = fetch("search_donki", required=True, start_date=start,
                     end_date=end, kind="CMEAnalysis")
    by_cme: dict[str, list] = {}
    for a in analyses.get("events", []):
        cid = a.get("associatedCMEID")
        if cid:
            by_cme.setdefault(cid, []).append(a)
    for cme_id, fits in by_cme.items():
        if cme_id in state["seen_cme_ids"]:
            continue
        state["seen_cme_ids"].append(cme_id)
        summary["new_cmes"].append(cme_id)
        # a CME may carry several analyst fits; forecast on the qualifying
        # (Earth-directed cone) fit with the highest speed - conservative for
        # arrival, and independent of feed ordering
        qualifying = [a for a in fits
                      if a.get("longitude") is not None
                      and a.get("speed") is not None and a.get("time21_5")
                      and abs(float(a["longitude"])) <= EARTH_DIRECTED_MAX_LON]
        if not qualifying:
            continue
        a = max(qualifying, key=lambda x: float(x["speed"]))
        lon, speed, t215 = a["longitude"], a["speed"], a["time21_5"]
        fc = run_tool("cme_arrival", v0_kms=float(speed), launch_time=t215)
        if fc.get("status") != "ok":
            continue
        forecast = {"cme_id": cme_id, "issued": now.isoformat(),
                    "launch": t215, "v0_kms": speed, "longitude": lon,
                    "arrival_estimate": fc["arrival_estimate"],
                    "window": fc["arrival_window"],
                    "audit_id": fc.get("audit_id")}
        state["pending_forecasts"].append(forecast)
        summary["new_forecasts"].append(forecast)

    # 3. mature pending forecasts
    import pandas as pd
    still_pending = []
    for fc in state["pending_forecasts"]:
        hi = pd.Timestamp(fc["window"][1])
        hi = hi.tz_localize("UTC") if hi.tzinfo is None else hi
        if hi + pd.Timedelta(hours=GRACE_HOURS) > pd.Timestamp(now):
            still_pending.append(fc)
            continue
        lo = pd.Timestamp(fc["window"][0])
        lo = lo.tz_localize("UTC") if lo.tzinfo is None else lo
        ips = fetch("search_donki", required=True,
                    start_date=str(lo.date() - timedelta(days=1)),
                    end_date=str(hi.date() + timedelta(days=1)), kind="IPS")
        if ips.get("status") != "ok":
            # An unavailable observation source is not evidence of a miss.
            still_pending.append(fc)
            continue
        hit_time = None
        for ev in ips.get("events", []):
            if ev.get("location") != "Earth" or not ev.get("eventTime"):
                continue
            t = pd.Timestamp(ev["eventTime"])
            t = t.tz_localize("UTC") if t.tzinfo is None else t
            if (lo - pd.Timedelta(hours=GRACE_HOURS) <= t
                    <= hi + pd.Timedelta(hours=GRACE_HOURS)):
                hit_time = str(t)
                break
        verdict = {"verdict": "hit" if hit_time else "miss",
                   "observed_arrival": hit_time, "matured": now.isoformat(),
                   **fc}
        state["ledger"].append(verdict)
        summary["matured"].append(verdict)
    state["pending_forecasts"] = still_pending

    # 4. new storms
    gst = fetch("search_donki", required=True, start_date=start, end_date=end,
                kind="GST")
    for ev in gst.get("events", []):
        gid = ev.get("gstID")
        if gid and gid not in state["seen_gst_ids"]:
            state["seen_gst_ids"].append(gid)
            summary["new_storms"].append(gid)

    ledger = state["ledger"]
    hits = sum(1 for e in ledger if e["verdict"] == "hit")
    summary["ledger_score"] = {"n_scored": len(ledger), "hits": hits,
                               "pending": len(state["pending_forecasts"])}
    summary["status"] = ("error" if required_source_failed else
                         "degraded" if summary["failed_sources"] else "ok")
    state["last_attempt"] = now.isoformat()
    state["last_cycle"] = now.isoformat()  # backward-compatible state field
    if not required_source_failed:
        state["last_successful_ingestion"] = now.isoformat()
    _save_state(state)
    return summary
