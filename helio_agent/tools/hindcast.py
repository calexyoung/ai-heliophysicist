"""Hindcast: the live monitor's CME-arrival forecast rule scored over history.

Ported from helio-agent's ``campaign.hindcast`` (v1.2.0) onto this repo's
monitor. The forward ledger (``helio-agent monitor``) accumulates one
verified window per real CME — an honest record, but a tiny sample. This
tool builds the track record wholesale: it replays the EXACT live rule in
``helio_agent.monitor`` over a historical window — the same DONKI
CMEAnalysis import, the same Earth-cone test (longitude known and within
``earth_cone_deg``), the same highest-speed-fit selection per CME, the same
drag-based ensemble window (``cme_arrival``), the same verification against
DONKI Earth-located interplanetary shocks (IPS) with ``grace_hours`` — and
scores every window, then checks storm coverage against the DONKI GST
record.

Three questions, answered with counts:

- **Precision**: of the Earth-directed arrival windows issued, how many
  contained an observed L1 shock (hits) vs none (false alarms)? Split by
  the empirical alert-confidence tier (launch speed x source longitude).
- **Timing**: mean absolute error of the central arrival estimate against
  the observed shock on the hits.
- **Recall**: of the geomagnetic storms that happened (DONKI GST, class
  from max Kp), how many had their onset inside a forecast window?

Deterministic given the DONKI record; every DONKI query goes through the
cached, audited ``search_donki``. The hindcast never touches the forward
ledger in ``monitor_state.json`` — it is a diagnostic of the rule, not part
of the record.
"""

from __future__ import annotations

from datetime import date, timedelta

from helio_agent.registry import get_tool, run_tool, tool
from helio_agent.workspace import output_path

# Alert-confidence tiers from helio-agent's 2024 hindcast (229 Earth-directed
# windows): precision stratified hard by launch speed and how close to disk
# center the source sat — high 53%, moderate 24%, low 7% vs a flat 15%. Tiers
# LABEL windows rather than dropping them, so recall is untouched. Re-verify
# on this repo's rule with the tool before quoting those numbers.
HIGH_SPEED_KMS = 1000.0
MODERATE_SPEED_KMS = 700.0
NEAR_DISK_LON_DEG = 30.0
CONFIDENCE_ORDER = ["low", "moderate", "high"]


def confidence_for(speed_kms: float, longitude_deg: float | None) -> str:
    """Empirical alert-confidence tier for an Earth-directed window."""
    near_disk = longitude_deg is not None and abs(longitude_deg) <= NEAR_DISK_LON_DEG
    if speed_kms >= HIGH_SPEED_KMS and near_disk:
        return "high"
    if speed_kms >= HIGH_SPEED_KMS or (speed_kms >= MODERATE_SPEED_KMS and near_disk):
        return "moderate"
    return "low"


def class_for_kp(max_kp: float) -> str:
    """Approximate storm class from a GST record's max Kp (NOAA G scale:
    Kp 9 = G5 superstorm, 8 = G4 severe, 7 = G3 intense, 5-6 = G1-G2)."""
    if max_kp >= 9.0:
        return "superstorm"
    if max_kp >= 8.0:
        return "severe"
    if max_kp >= 7.0:
        return "intense"
    if max_kp >= 5.0:
        return "moderate"
    return "below-moderate"


def _ts(text):
    import pandas as pd
    t = pd.Timestamp(text)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def _chunks(start: date, end: date, days: int):
    a = start
    while a < end:
        b = min(a + timedelta(days=days), end)
        yield a, b
        a = b


@tool(family="measure")
def hindcast_forecasts(start: str, end: str, min_speed_kms: float = 0.0,
                       earth_cone_deg: float | None = None,
                       grace_hours: float = 12.0,
                       chunk_days: int = 30, plot: bool = True,
                       out_name: str = "hindcast.png",
                       table_name: str = "hindcast.md") -> dict:
    """Score the live monitor's CME-arrival forecast rule over a historical
    window: forecast every Earth-directed DONKI cone-model CME exactly as
    `helio-agent monitor` does (longitude known and within earth_cone_deg,
    highest-speed fit per CME, cme_arrival drag ensemble), verify each window
    against DONKI Earth IPS shocks (+/- grace_hours), and check storm
    coverage against DONKI GST. Diagnostic only; the forward ledger is not
    touched.

    start/end: 'YYYY-MM-DD'. earth_cone_deg defaults to the live monitor's
    EARTH_DIRECTED_MAX_LON so this replays the deployed rule; set it only to
    explore a change. min_speed_kms: optional launch-speed floor (the live
    rule has none, deliberately — a floor drops slow CMEs that do drive
    storms). chunk_days: DONKI query span.

    Returns forecasts (every window, time order, with outcome "hit" |
    "false_alarm", the matched IPS, timing error and confidence tier),
    n_hits / n_false_alarms / hit_rate / hit_mae_hours, precision by
    confidence tier, storms (each GST with max Kp, class, whether a window
    covered its onset and by which CME), storm_recall, note, and a markdown
    table + three-panel figure when plot. Hundreds of windows over a year:
    quote hit rate and recall together, never one alone.
    """
    from helio_agent.monitor import EARTH_DIRECTED_MAX_LON
    # Default to the live monitor's cone so the hindcast always replays the
    # deployed rule; pass earth_cone_deg explicitly only to explore a change.
    if earth_cone_deg is None:
        earth_cone_deg = float(EARTH_DIRECTED_MAX_LON)
    import pandas as pd
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    if d1 <= d0:
        return {"status": "error", "error": "end must be after start"}
    if not 5 <= chunk_days <= 45:
        return {"status": "error", "error": "chunk_days must be 5-45 (DONKI query span)"}

    # 1. every cone analysis, grouped per CME (the monitor's import)
    by_cme: dict[str, list] = {}
    n_analyses = 0
    for a, b in _chunks(d0, d1, chunk_days):
        r = run_tool("search_donki", start_date=a.isoformat(), end_date=b.isoformat(),
                     kind="CMEAnalysis")
        if r.get("status") != "ok":
            return {"status": "error", "error": f"DONKI CMEAnalysis {a}..{b}: {r.get('error')}"}
        for an in r.get("events", []):
            cid = an.get("associatedCMEID")
            if cid and an not in by_cme.setdefault(cid, []):
                by_cme[cid].append(an)
                n_analyses += 1

    # 2. verification records: Earth IPS shocks and GST storms, with slack
    # for late arrivals from window-edge CMEs
    tail = d1 + timedelta(days=7)
    shocks, storms_raw = [], []
    for a, b in _chunks(d0, tail, 90):
        ips = run_tool("search_donki", start_date=a.isoformat(), end_date=b.isoformat(), kind="IPS")
        shocks += [(_ts(e["eventTime"]), e.get("activityID"))
                   for e in ips.get("events", [])
                   if e.get("location") == "Earth" and e.get("eventTime")]
        gst = run_tool("search_donki", start_date=a.isoformat(), end_date=b.isoformat(), kind="GST")
        storms_raw += [s for s in gst.get("events", []) if s.get("startTime")]
    shocks = sorted(set(shocks))
    storms = []
    seen = set()
    for s in storms_raw:
        gid = s.get("gstID") or s["startTime"]
        if gid in seen:
            continue
        seen.add(gid)
        kps = [float(k["kpIndex"]) for k in (s.get("allKpIndex") or [])
               if isinstance(k, dict) and isinstance(k.get("kpIndex"), (int, float))]
        storms.append({"gst_id": gid, "start": _ts(s["startTime"]),
                       "max_kp": max(kps) if kps else None})
    storms.sort(key=lambda s: s["start"])

    # 3. forecast + score every Earth-directed CME with the live rule
    arrival = get_tool("cme_arrival").func
    grace = pd.Timedelta(hours=grace_hours)
    forecasts = []
    n_fast = 0
    for cme_id, fits in sorted(by_cme.items()):
        qualifying = [x for x in fits
                      if x.get("longitude") is not None and x.get("speed") is not None
                      and x.get("time21_5") and abs(float(x["longitude"])) <= earth_cone_deg]
        if not qualifying:
            continue
        x = max(qualifying, key=lambda q: float(q["speed"]))
        speed, lon = float(x["speed"]), float(x["longitude"])
        if speed < min_speed_kms:
            continue
        n_fast += 1
        fc = arrival(v0_kms=speed, launch_time=x["time21_5"])
        if fc.get("status") == "error":
            continue
        lo, hi = _ts(fc["arrival_window"][0]), _ts(fc["arrival_window"][1])
        central = _ts(fc["arrival_estimate"])
        hit = next(((t, sid) for t, sid in shocks if lo - grace <= t <= hi + grace), None)
        forecasts.append({
            "cme_id": cme_id, "launch": x["time21_5"], "v0_kms": speed,
            "longitude": lon, "confidence": confidence_for(speed, lon),
            "arrival_estimate": str(central), "window": [str(lo), str(hi)],
            "window_hours": round((hi - lo).total_seconds() / 3600, 1),
            "outcome": "hit" if hit else "false_alarm",
            "observed_arrival": str(hit[0]) if hit else None,
            "ips_id": hit[1] if hit else None,
            "timing_error_hours": (round((hit[0] - central).total_seconds() / 3600, 1)
                                   if hit else None)})
    forecasts.sort(key=lambda f: f["launch"])

    # 4. aggregates
    hits = [f for f in forecasts if f["outcome"] == "hit"]
    n_hits, n_fa = len(hits), len(forecasts) - len(hits)
    errors = [abs(f["timing_error_hours"]) for f in hits]
    widths = sorted(f["window_hours"] for f in forecasts)

    # 5. storm coverage (recall)
    storm_rows = []
    for s in storms:
        if not (d0 <= s["start"].date() <= d1):
            continue
        covering = [f for f in forecasts
                    if _ts(f["window"][0]) - grace <= s["start"] <= _ts(f["window"][1]) + grace]
        best = (max(covering, key=lambda f: CONFIDENCE_ORDER.index(f["confidence"]))
                if covering else None)
        storm_rows.append({"gst_id": s["gst_id"], "start": str(s["start"]),
                           "max_kp": s["max_kp"],
                           "observed_class": class_for_kp(s["max_kp"])
                           if s["max_kp"] is not None else None,
                           "forecast": bool(covering),
                           "matched_cme_id": covering[0]["cme_id"] if covering else None,
                           "best_confidence": best["confidence"] if best else None})
    n_covered = sum(1 for s in storm_rows if s["forecast"])

    # 5b. precision by tier (labels only, recall unchanged)
    tiers = []
    for tier in reversed(CONFIDENCE_ORDER):
        rows = [f for f in forecasts if f["confidence"] == tier]
        th = sum(1 for f in rows if f["outcome"] == "hit")
        tiers.append({"confidence": tier, "n_windows": len(rows), "n_hits": th,
                      "precision": round(th / len(rows), 3) if rows else None,
                      "n_storms_best": sum(1 for s in storm_rows
                                           if s["best_confidence"] == tier)})

    out = {"start": start, "end": end, "n_analyses": n_analyses, "n_cmes": len(by_cme),
           "n_earth_directed": len(forecasts), "n_shocks": len(shocks),
           "forecasts": forecasts, "n_hits": n_hits, "n_false_alarms": n_fa,
           "hit_rate": round(n_hits / len(forecasts), 3) if forecasts else None,
           "hit_mae_hours": round(sum(errors) / len(errors), 1) if errors else None,
           "median_window_hours": widths[len(widths) // 2] if widths else None,
           "confidence_rows": tiers, "storms": storm_rows, "n_storms": len(storm_rows),
           "n_storms_forecast": n_covered,
           "storm_recall": round(n_covered / len(storm_rows), 3) if storm_rows else None,
           "rule": {"earth_cone_deg": earth_cone_deg, "grace_hours": grace_hours,
                    "min_speed_kms": min_speed_kms, "verification": "DONKI IPS (Earth)",
                    "storm_record": "DONKI GST, class from max Kp"},
           "method": "replay of helio_agent.monitor's forecast rule (cme_arrival drag "
                     "ensemble) over DONKI CMEAnalysis; hits vs Earth IPS; storm "
                     "recall vs GST"}
    parts = [f"{start} -> {end}: {len(forecasts)} Earth-directed windows from "
             f"{len(by_cme)} CMEs ({n_analyses} analyses) - {n_hits} hits, {n_fa} false alarms"]
    if out["hit_rate"] is not None:
        parts.append(f"hit rate {out['hit_rate']:.0%}")
    tiered = [t for t in tiers if t["precision"] is not None]
    if tiered:
        parts.append("precision by confidence " + ", ".join(
            f"{t['confidence']} {t['precision']:.0%} (n={t['n_windows']})" for t in tiered))
    if storm_rows:
        parts.append(f"storm recall {n_covered}/{len(storm_rows)}")
    if out["hit_mae_hours"] is not None:
        parts.append(f"hit MAE {out['hit_mae_hours']:g} h")
    out["note"] = "; ".join(parts)

    if plot:
        tpath = output_path(table_name)
        tpath.write_text(_table(out))
        out["table_file"] = str(tpath)
        out["file"] = _plot(out, out_name)
        out["artifacts"] = [out["file"], out["table_file"]]
    return out


def _table(o: dict) -> str:
    L = ["# Forecast hindcast", "",
         f"Window **{o['start']} -> {o['end']}** - the live monitor forecast rule replayed "
         "over history. Diagnostic only; the forward ledger is untouched.", "",
         f"- {o['n_analyses']} cone analyses on {o['n_cmes']} CMEs; "
         f"**{o['n_earth_directed']} Earth-directed windows issued**",
         f"- **{o['n_hits']} hits, {o['n_false_alarms']} false alarms** against "
         f"{o['n_shocks']} Earth IPS shocks"
         + (f" - hit rate {o['hit_rate']:.0%}" if o["hit_rate"] is not None else "")]
    if o["storm_recall"] is not None:
        L.append(f"- **Storm recall {o['n_storms_forecast']}/{o['n_storms']}** "
                 f"({o['storm_recall']:.0%}) - storms whose onset fell inside a window")
    if o["hit_mae_hours"] is not None:
        L.append(f"- Hit timing MAE **{o['hit_mae_hours']:g} h**; median window "
                 f"{o['median_window_hours']:g} h")
    L += ["", "## Precision by alert-confidence tier", "",
          "| confidence | windows | hits | precision | storms best-covered |", "|---|---|---|---|---|"]
    for r in o["confidence_rows"]:
        p = f"{r['precision']:.0%}" if r["precision"] is not None else "-"
        L.append(f"| {r['confidence']} | {r['n_windows']} | {r['n_hits']} | {p} | {r['n_storms_best']} |")
    L += ["", "## Storms in the window", "",
          "| storm onset | max Kp | class | forecast? | best confidence | matched CME |",
          "|---|---|---|---|---|---|"]
    for s in o["storms"]:
        L.append(f"| {s['start']} | {s['max_kp'] if s['max_kp'] is not None else '-'} "
                 f"| {s['observed_class'] or '-'} | {'HIT' if s['forecast'] else 'MISSED'} "
                 f"| {s['best_confidence'] or '-'} | {s['matched_cme_id'] or '-'} |")
    L += ["", "## Every hit", "", "| CME | speed | window (UTC) | shock | timing error |",
          "|---|---|---|---|---|"]
    for f in o["forecasts"]:
        if f["outcome"] == "hit":
            L.append(f"| {f['cme_id']} | {f['v0_kms']:g} km/s | {f['window'][0][5:16]} -> "
                     f"{f['window'][1][5:16]} | {f['observed_arrival']} | "
                     f"{f['timing_error_hours']:+g} h |")
    return "\n".join(L) + "\n"


def _plot(o: dict, out_name: str) -> str:
    import pandas as pd
    from helio_agent.style import EVENT_COLOR, NEUTRAL, PALETTE, apply_style, figsize
    apply_style()
    import matplotlib.pyplot as plt

    w, _ = figsize("page")
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(w, 3.0), layout="constrained")
    hits = [f for f in o["forecasts"] if f["outcome"] == "hit"]
    if hits:
        pred = [pd.Timestamp(f["arrival_estimate"]) for f in hits]
        obs = [pd.Timestamp(f["observed_arrival"]) for f in hits]
        half = [pd.Timedelta(hours=f["window_hours"] / 2) for f in hits]
        ax1.errorbar(pred, obs, xerr=half, fmt="o", ms=3, color=PALETTE[0], ecolor=NEUTRAL,
                     elinewidth=0.6, zorder=3)
        lo, hi = min(min(pred), min(obs)), max(max(pred), max(obs))
        ax1.plot([lo, hi], [lo, hi], color=EVENT_COLOR, ls="--", lw=0.8, label="perfect timing")
        ax1.legend(loc="upper left", fontsize=6)
        ax1.tick_params(axis="x", labelrotation=30, labelsize=6)
        ax1.tick_params(axis="y", labelsize=6)
    ax1.set_xlabel("Predicted central arrival")
    ax1.set_ylabel("Observed shock")
    t1 = f"Hits (n={len(hits)}"
    if o["hit_mae_hours"] is not None:
        t1 += f", MAE {o['hit_mae_hours']:g} h"
    ax1.set_title(t1 + ")")

    labels = ["hits", "false\nalarms", "storms\ncovered", "storms\nmissed"]
    values = [o["n_hits"], o["n_false_alarms"], o["n_storms_forecast"],
              o["n_storms"] - o["n_storms_forecast"]]
    bars = ax2.bar(labels, values, color=[PALETTE[0], PALETTE[1], PALETTE[0], PALETTE[1]],
                   width=0.62)
    for bar, v in zip(bars, values):
        ax2.annotate(str(v), xy=(bar.get_x() + bar.get_width() / 2, v), xytext=(0, 2),
                     textcoords="offset points", ha="center", fontsize=7)
    sub = []
    if o["hit_rate"] is not None:
        sub.append(f"hit rate {o['hit_rate']:.0%}")
    if o["storm_recall"] is not None:
        sub.append(f"recall {o['storm_recall']:.0%}")
    ax2.set_title("Precision vs recall")
    if sub:
        ax2.text(0.98, 0.97, "\n".join(sub), transform=ax2.transAxes, ha="right", va="top",
                 fontsize=7)
    ax2.set_ylabel("Count")

    tiered = [r for r in o["confidence_rows"] if r["precision"] is not None]
    if tiered:
        tb = ax3.bar([r["confidence"] for r in tiered], [r["precision"] * 100 for r in tiered],
                     color=PALETTE[:len(tiered)], width=0.62)
        for bar, r in zip(tb, tiered):
            ax3.annotate(f"{r['precision']:.0%}\n({r['n_hits']}/{r['n_windows']})",
                         xy=(bar.get_x() + bar.get_width() / 2, r["precision"] * 100),
                         xytext=(0, 2), textcoords="offset points", ha="center", fontsize=7)
        ax3.set_ylim(0, max(r["precision"] * 100 for r in tiered) * 1.25 + 5)
    ax3.set_title("Precision by alert confidence")
    ax3.set_ylabel("Window precision (%)")
    for ax in (ax2, ax3):
        ax.grid(True, axis="y", alpha=0.3)
    fig.suptitle(f"Forecast hindcast {o['start']} to {o['end']}", fontsize=9)
    fpath = output_path(out_name)
    fig.savefig(fpath, bbox_inches="tight")
    plt.close(fig)
    return str(fpath)
