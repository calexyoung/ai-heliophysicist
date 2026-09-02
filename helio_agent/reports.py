"""Saved, rerunnable report builders (pattern from helio-agent's campaigns).

A report is a named, parameterized chain of audited tool calls ending in
figures + a PDF — parse once, rerun any day:

    helio-agent report sun-news [--date YYYY-MM-DD]

Text sections are deterministic templates filled with tool-measured numbers
(no free-form generation); interpretation beyond the numbers stays with the
scientist/agent reviewing the output.
"""

from __future__ import annotations

from helio_agent.registry import run_tool


def _fmt_flare(fl: dict) -> str:
    return f"{fl['class']} (peak {fl['peak'][11:16]} UT, {fl['duration_min']:.0f} min)"


def sun_news(date: str | None = None) -> dict:
    """Daily space-weather report: flares, regions, CMEs, solar wind, Kp, cycle.

    date: report day (UTC, 'YYYY-MM-DD'); window is 11 UT the day before to
    11 UT on `date`. Defaults to today. Data are NOAA operational feeds
    (rolling 3-7 day windows) — dates older than that will refuse.
    """
    import pandas as pd

    day = pd.Timestamp(date) if date else pd.Timestamp.utcnow().tz_localize(None).normalize()
    t0 = (day - pd.Timedelta(days=1)).strftime("%Y-%m-%dT11:00:00")
    t1 = day.strftime("%Y-%m-%dT11:00:00")
    tag = day.strftime("%Y%m%d")
    artifacts: list[str] = []
    steps: list[str] = []

    def step(name: str, **kwargs) -> dict:
        r = run_tool(name, **kwargs)
        steps.append(f"{name}: {r.get('status')} ({r.get('audit_id')})")
        if r.get("status") != "ok":
            raise RuntimeError(f"{name} failed: {r.get('error')}")
        artifacts.extend(r.get("artifacts", []))
        return r

    xray = step("fetch_swpc_timeseries", product="xray", start=t0, end=t1)
    flares = step("find_flares", file=xray["file"], min_class="B1.0",
                  swpc_scale=False)
    plasma = step("fetch_swpc_timeseries", product="plasma", start=t0, end=t1)
    mag = step("fetch_swpc_timeseries", product="mag", start=t0, end=t1)
    kp = step("fetch_swpc_timeseries", product="kp",
              start=(day - pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00:00"),
              end=t1)
    regions = step("get_solar_regions")
    cmes = step("search_donki",
                start_date=(day - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=day.strftime("%Y-%m-%d"), kind="CME")
    cycle = step("fetch_solar_cycle", start="2008-12")
    sw_stats = step("describe_series", file=plasma["file"])
    mag_stats = step("describe_series", file=mag["file"])
    kp_df = pd.read_csv(kp["file"], index_col="time", parse_dates=True)

    big = [f for f in flares.get("flares", []) if f["class"][0] in "CMX"]
    strongest = max(flares.get("flares", []),
                    key=lambda f: f["peak_flux_wm2"], default=None)

    fig_xrs = step("plot_timeseries", file=xray["file"],
                   columns=["xrsb", "xrsa"],
                   series_labels=["1-8 A (xrsb)", "0.5-4 A (xrsa)"],
                   y_label="Flux (W m$^{-2}$)", log_y=True,
                   title=f"GOES XRS (operational), {t0[:10]} 11:00 to {t1[:10]} 11:00 UT",
                   event_times=[f["peak"] for f in big[:6]],
                   event_labels=[f["class"] for f in big[:6]],
                   out_name=f"sunnews_{tag}_xrs.png")
    fig_sw = step("plot_stack", files_columns=[
        {"file": plasma["file"], "column": "proton_speed", "label": "Vsw (km s$^{-1}$)"},
        {"file": plasma["file"], "column": "proton_density", "label": "n (cm$^{-3}$)"},
        {"file": mag["file"], "column": "bt", "label": "Bt (nT)"},
        {"file": mag["file"], "column": "bz_gsm", "label": "Bz GSM (nT)"},
        {"file": kp["file"], "column": "Kp", "label": "Kp"},
    ], title=f"Solar wind at L1 (RTSW) + Kp, {t0[:10]}/{t1[:10]}",
        out_name=f"sunnews_{tag}_sw.png")
    fig_cycle = step("plot_timeseries", file=cycle["file"],
                     columns=["ssn", "smoothed_ssn"],
                     series_labels=["Monthly SSN", "13-month smoothed"],
                     y_label="Sunspot number",
                     title="Solar Cycle Progression (NOAA/SWPC)",
                     out_name=f"sunnews_{tag}_cycle.png")

    sw = sw_stats["columns"]
    mg = mag_stats["columns"]
    n_c = sum(1 for f in flares["flares"] if f["class"].startswith("C"))
    n_m = sum(1 for f in flares["flares"] if f["class"].startswith("M"))
    n_x = sum(1 for f in flares["flares"] if f["class"].startswith("X"))
    region_lines = "\n".join(
        f"  AR{r['region']}  {r['location'] or '?':8s} mag {r['mag_class'] or '-'}  "
        f"{r['number_spots'] or 0} spots, area {r['area_millionths'] or 0} mu"
        for r in regions["regions"] if r.get("mag_class"))
    cme_lines = "\n".join(
        f"  {e['activityID']}: {(e.get('note') or '')[:150]}"
        for e in cmes.get("events", [])) or "  none listed"

    sections = [
        {"heading": "Reporting window and provenance",
         "text": f"Window: {t0} to {t1} UTC. Sources: GOES primary XRS 1-min, "
                 "NOAA RTSW solar wind at L1, NOAA planetary Kp, NOAA/SWPC "
                 "solar region analysis, NASA CCMC DONKI, NOAA Solar Cycle "
                 "Progression. Operational feeds - not science quality; every "
                 "number is audit-logged (workspace/logs/audit.jsonl):\n  "
                 + "\n  ".join(steps)},
        {"heading": "Solar cycle",
         "text": f"Latest monthly sunspot number: {cycle['latest_ssn']} "
                 f"({cycle['latest_month']}; previous month "
                 f"{cycle['previous_month_ssn']}). Cycle 25 smoothed maximum "
                 f"{cycle.get('smoothed_max_ssn')} in {cycle.get('smoothed_max_month')} "
                 f"(smoothed series final through {cycle.get('smoothed_through')}).",
         "image": fig_cycle["file"]},
        {"heading": "Flare activity",
         "text": f"Detected {n_x} X, {n_m} M, {n_c} C flares (plus "
                 f"{len(flares['flares']) - n_x - n_m - n_c} B-level "
                 "enhancements; sensitive detector - the official SWPC event "
                 "list applies stricter criteria). Strongest: "
                 + (_fmt_flare(strongest) if strongest else "none") + ".",
         "image": fig_xrs["file"]},
        {"heading": "Sunspot regions (NOAA analysis)",
         "text": f"Analysis date {regions['observed_date']}:\n{region_lines}"},
        {"heading": "CMEs (DONKI)", "text": cme_lines},
        {"heading": "Solar wind and geomagnetic conditions",
         "text": f"Proton speed {sw['proton_speed']['min']:.0f}-"
                 f"{sw['proton_speed']['max']:.0f} km/s (mean "
                 f"{sw['proton_speed']['mean']:.0f}); density mean "
                 f"{sw['proton_density']['mean']:.1f} /cm3. Bt "
                 f"{mg['bt']['min']:.1f}-{mg['bt']['max']:.1f} nT; Bz GSM "
                 f"{mg['bz_gsm']['min']:.1f} to {mg['bz_gsm']['max']:.1f} nT. "
                 f"Kp {kp_df['Kp'].min():.2f}-{kp_df['Kp'].max():.2f}.",
         "image": fig_sw["file"]},
    ]
    pdf = step("write_pdf_report", title=f"Sun News - {day.date()}",
               sections=sections, out_name=f"sunnews_{tag}.pdf")
    return {"status": "ok", "date": str(day.date()), "pdf": pdf["file"],
            "figures": [fig_xrs["file"], fig_sw["file"], fig_cycle["file"]],
            "n_flares": len(flares["flares"]),
            "strongest_flare": strongest, "steps": steps}


REPORTS = {"sun-news": sun_news}
