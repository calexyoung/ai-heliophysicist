"""Is the sheath-driven pattern real, or two events in a row?

Two 2024 superstorms were each attributed to their sheath rather than their
ejecta. This tests that against every intense storm in the OMNI record.

    HELIO_AGENT_USER=cayoung uv run python .../study.py
    ... --limit 5      # first N storms only, for a smoke test

Sample: declustered peaks of hourly Dst below a threshold, from
`extreme_value(list_events=True)` — the same declustering that makes a
return-period fit honest also makes the storm list non-overlapping.

For each storm: OMNI 1-min over +/-4 days, then `detect_icme`, then the
sheath and ejecta southward-field budgets.

**The methodological point this study exists to check.** `detect_icme`
attributes a storm by comparing TOTAL southward field-time (nT*h) between
sheath and ejecta. That total is an integral, so a long interval wins by
construction: a 58 h sheath accumulates more nT*h than a 20 h ejecta even
at a weaker mean field. Physically the integral is the right quantity —
ring-current injection integrates VBs — but the *label* could be reporting
duration rather than intensity. So both are recorded here: the total, and
the rate (nT*h per hour, i.e. mean southward Bz). If the pattern survives
normalisation it is about the field; if it does not, it is about duration.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STATE = HERE / "results.json"
sys.path.insert(0, str(ROOT))

DST_THRESHOLD = -200.0
PAD_DAYS = 4
OMNI_VARS = ["F", "BY_GSM", "BZ_GSM", "flow_speed", "proton_density", "T",
             "SYM_H"]


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1, default=str))


def rate(budget: dict | None) -> float | None:
    """Mean southward Bz over the interval (nT*h per hour)."""
    if not budget or not budget.get("hours"):
        return None
    return round(budget["south_nT_hours"] / budget["hours"], 2)


def main() -> int:
    from helio_agent.registry import run_tool

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--fresh", action="append", default=[])
    args = ap.parse_args()
    st = load_state()
    fresh = set(args.fresh)

    def R(key, tool, **kw):
        if key in st and key not in fresh:
            return st[key]
        print(f"  RUN {key} ({tool})", flush=True)
        r = run_tool(tool, **kw)
        if r.get("status") == "error":
            print(f"     FAIL {str(r.get('error'))[:100]}", flush=True)
        st[key] = r
        save_state(st)
        return r

    # ---- sample selection -------------------------------------------------
    print("Selecting the storm sample")
    dst = R("dst_hourly", "fetch_cdaweb_data", dataset="OMNI2_H0_MRG1HR",
            variables=["DST1800"], start="1981-01-01T00:00:00Z",
            end="2025-01-01T00:00:00Z")
    if not dst.get("file"):
        print("cannot build a sample without the hourly Dst record")
        return 1
    ev = R("sample", "extreme_value", file=dst["file"], column="DST1800",
           threshold=DST_THRESHOLD, direction="min",
           decluster_gap_hours=48.0, list_events=True)
    storms = ev.get("events", [])
    if args.limit:
        storms = storms[:args.limit]
    print(f"{len(storms)} storms at Dst <= {DST_THRESHOLD:g} nT "
          f"over {ev.get('record_years')} years")

    # ---- per-storm analysis ----------------------------------------------
    for n, s in enumerate(storms, 1):
        t = datetime.fromisoformat(str(s["time"]))
        tag = f"{t:%Y%m%d}"
        print(f"[{n}/{len(storms)}] {t:%Y-%m-%d %H:%M} Dst {s['value']:.0f}",
              flush=True)
        w0 = (t - timedelta(days=PAD_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
        w1 = (t + timedelta(days=PAD_DAYS)).strftime("%Y-%m-%dT00:00:00Z")
        o = R(f"omni_{tag}", "fetch_omni", start=w0, end=w1,
              resolution="1min", variables=OMNI_VARS)
        if not o.get("file"):
            continue
        R(f"icme_{tag}", "detect_icme", file=o["file"],
          speed_column="flow_speed", temperature_column="T",
          bz_column="BZ_GSM", by_column="BY_GSM",
          density_column="proton_density", plot=False)

    # ---- the published record on the same question ------------------------
    for key, q in (
        ("lit_drivers",
         'abs:sheath abs:("magnetic cloud" OR ejecta) abs:geoeffectiveness '
         'OR abs:"storm intensity" abs:Dst'),
        ("lit_intense",
         'abs:sheath abs:"intense storms" abs:("magnetic cloud" OR ejecta) '
         'year:2004-2026'),
    ):
        R(key, "search_ads", query=q, max_results=10)

    save_state(st)

    # ---- what the sample says --------------------------------------------
    rows = []
    for s in storms:
        t = datetime.fromisoformat(str(s["time"]))
        r = st.get(f"icme_{t:%Y%m%d}")
        if not isinstance(r, dict) or r.get("status") == "error":
            rows.append({"time": str(s["time"]), "dst": s["value"],
                         "driver": None, "why": str((r or {}).get("error"))[:80]})
            continue
        sh = (r.get("sheath") or {}).get("field")
        ej = r.get("ejecta_field")
        rows.append({
            "time": str(s["time"]), "dst": s["value"],
            "driver": r.get("driver"),
            "shock": r.get("shock_time"),
            "sheath_hours": (sh or {}).get("hours"),
            "sheath_total": (sh or {}).get("south_nT_hours"),
            "sheath_rate": rate(sh),
            "ejecta_hours": (ej or {}).get("hours"),
            "ejecta_total": (ej or {}).get("south_nT_hours"),
            "ejecta_rate": rate(ej),
        })
    st["_rows"] = rows
    save_state(st)

    got = [r for r in rows if r.get("driver")]
    print(f"\n{len(rows)} storms, {len(got)} with a sheath/ejecta attribution")
    for label in ("sheath", "ejecta", "ambiguous"):
        n = sum(1 for r in got if r["driver"] == label)
        print(f"  {label:10s} {n:3d}  ({n / max(len(got),1) * 100:.0f}%)")
    # the same comparison on rates rather than totals
    flip = 0
    for r in got:
        if r.get("sheath_rate") is None or r.get("ejecta_rate") is None:
            continue
        by_rate = ("sheath" if r["sheath_rate"] >= r["ejecta_rate"] * 1.5
                   else "ejecta" if r["ejecta_rate"] >= r["sheath_rate"] * 1.5
                   else "ambiguous")
        if by_rate != r["driver"]:
            flip += 1
    print(f"  attribution changes on rates rather than totals: {flip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
