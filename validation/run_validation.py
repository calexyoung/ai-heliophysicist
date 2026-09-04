"""Validation suite: prove the tool layer reproduces published results.

Each case pins a tool chain to a canonical, citable anchor. Run after any
dependency upgrade or tool change:

    uv run python validation/run_validation.py

A tool the agent may use must have a passing case here (the "validate against
canonical results" step of the pattern).
"""

from __future__ import annotations

import sys

from helio_agent.registry import run_tool

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")


def case_halloween_2003() -> None:
    """OMNI2 Dst for the Halloween 2003 superstorm.

    Anchor: Dst minimum of -383 nT at 2003-10-30 22:00-23:00 UT
    (Kyoto WDC final Dst; e.g. Gopalswamy et al. 2005, JGR 110, A09S15).
    """
    r = run_tool("fetch_omni", start="2003-10-25T00:00:00Z",
                 end="2003-11-05T00:00:00Z")
    if r["status"] != "ok":
        check("halloween2003.fetch", False, r.get("error", ""))
        return
    m = run_tool("storm_metrics", file=r["file"], dst_column="DST1800")
    ok = m["status"] == "ok" and abs(m["dst_min_nT"] - (-383.0)) <= 5 \
        and m["time_of_min"].startswith("2003-10-30 22")
    check("halloween2003.dst_min", ok,
          f"got {m.get('dst_min_nT')} nT at {m.get('time_of_min')} "
          "(published: -383 nT, 2003-10-30 ~22:30 UT)")


def case_flare_20170906() -> None:
    """GOES XRS flare detection for 2017-09-06.

    Anchor: X9.3 flare (largest of cycle 24) peaking 12:02 UT, and an X2.2
    peaking 09:10 UT, both from AR 12673 (NOAA/SWPC event lists; DONKI).
    """
    r = run_tool("fetch_goes_xrs", start="2017-09-06T00:00:00",
                 end="2017-09-06T23:59:00")
    if r["status"] != "ok":
        check("flare20170906.fetch", False, r.get("error", ""))
        return
    f = run_tool("find_flares", file=r["file"], min_class="X1.0")
    flares = f.get("flares", [])
    peaks = {fl["peak"][:16] for fl in flares}
    big = max(flares, key=lambda fl: fl["peak_flux_wm2"], default=None)
    ok = ("2017-09-06 12:02" in peaks and "2017-09-06 09:10" in peaks
          and big is not None and big["class"].startswith("X")
          and 8.0 <= float(big["class"][1:]) <= 12.0)
    check("flare20170906.detection", ok,
          f"peaks found {sorted(peaks)}, largest {big['class'] if big else None} "
          "(published: X2.2 @ 09:10, X9.3 @ 12:02; class tolerance X8-X12 "
          "covers satellite/scaling differences)")
    d = run_tool("search_donki", start_date="2017-09-06",
                 end_date="2017-09-07", kind="FLR")
    donki_ok = d["status"] == "ok" and any(
        e.get("classType") == "X9.3" for e in d.get("events", []))
    check("flare20170906.donki_crosscheck", donki_ok,
          "DONKI lists X9.3 on 2017-09-06" if donki_ok else "DONKI cross-check failed")


def case_solar_rotation() -> None:
    """Solar rotation period in solar wind speed, 2017 (declining phase).

    Anchor: recurrent high-speed streams give a synodic-rotation signal;
    expect a Lomb-Scargle peak in V at 27 +/- 4 days (Carrington synodic
    period 27.28 d; recurrence peaks are broad and can split into harmonics).
    """
    r = run_tool("fetch_omni", start="2017-01-01T00:00:00Z",
                 end="2017-12-31T23:59:00Z", variables=["V1800"])
    if r["status"] != "ok":
        check("rotation2017.fetch", False, r.get("error", ""))
        return
    p = run_tool("lomb_scargle", file=r["file"], column="V1800",
                 min_period="5D", max_period="60D")
    peaks = p.get("peaks", [])
    hit = next((pk for pk in peaks if abs(pk["period_days"] - 27.28) <= 4), None)
    check("rotation2017.period", hit is not None,
          f"top periods {[pk['period_days'] for pk in peaks[:3]]} d "
          "(expect one near 27.28 d)")


def case_ephemeris_l1() -> None:
    """SSCWeb ephemeris sanity: ACE sits near L1, ~1.4-1.6e6 km upstream (GSE X)."""
    r = run_tool("fetch_spacecraft_ephemeris", spacecraft=["ace"],
                 start="2017-09-05T00:00:00Z", end="2017-09-06T00:00:00Z")
    if r["status"] != "ok":
        check("ephemeris.fetch", False, r.get("error", ""))
        return
    import pandas as pd
    df = pd.read_csv(r["file"], index_col="time", parse_dates=True)
    x = df["ace_x_km"].mean()
    ok = 1.3e6 < x < 1.7e6
    check("ephemeris.ace_l1", ok, f"mean GSE X = {x:.3g} km (expect ~1.5e6)")


def case_pyspedas_crosscheck() -> None:
    """pySPEDAS vs CDAWeb pipeline consistency on the same physical data.

    Anchor: mean ACE |B| over 2017-09-06/08 from pyspedas ace.mfi must agree
    with the CDAWeb AC_H2_MFI Magnitude mean to within 5% (cadence and gap
    handling differ; the underlying measurements are identical).
    """
    import numpy as np
    import pandas as pd
    r1 = run_tool("fetch_pyspedas", mission="ace", instrument="mfi",
                  start="2017-09-06", end="2017-09-08")
    if r1["status"] != "ok":
        check("pyspedas.fetch", False, r1.get("error", ""))
        return
    mag_col = next((c for c in r1["columns"] if "magnitude" in c.lower()), None)
    if mag_col is None:
        check("pyspedas.fetch", False, f"no |B| column among {r1['columns']}")
        return
    r2 = run_tool("fetch_cdaweb_data", dataset="AC_H2_MFI",
                  variables=["Magnitude"], start="2017-09-06T00:00:00Z",
                  end="2017-09-08T00:00:00Z")
    if r2["status"] != "ok":
        check("pyspedas.cdaweb_ref", False, r2.get("error", ""))
        return
    s1 = pd.read_csv(r1["file"], index_col="time",
                     parse_dates=True)[mag_col].resample("1h").mean()
    s2 = pd.read_csv(r2["file"], index_col="time",
                     parse_dates=True)["Magnitude"].resample("1h").mean()
    both = pd.DataFrame({"a": s1, "b": s2}).dropna()
    m1, m2 = float(both["a"].mean()), float(both["b"].mean())
    ok = len(both) > 24 and abs(m1 - m2) / m2 < 0.02
    check("pyspedas.crosscheck", ok,
          f"hourly-matched mean |B|: pyspedas {m1:.3f} nT vs CDAWeb {m2:.3f} nT "
          f"({abs(m1 - m2) / m2 * 100:.2f}% diff over {len(both)} common hours, "
          "tolerance 2%)")


def case_plasma_parameters() -> None:
    """PlasmaPy formulary against the analytic Alfven speed.

    Anchor: v_A = B / sqrt(mu0 * n * m_p) for n=5 cm^-3, B=5 nT
    -> 48.76 km/s (hand-computable), beta ~ 0.69 for T=1e5 K.
    """
    r = run_tool("plasma_parameters", density_cm3=5.0, b_nT=5.0,
                 temperature_K=1e5)
    ok = (r["status"] == "ok"
          and abs(r["alfven_speed_km_s"] - 48.76) < 0.1
          and abs(r["plasma_beta"] - 0.694) < 0.01)
    check("plasmapy.formulary", ok,
          f"v_A={r.get('alfven_speed_km_s'):.2f} km/s (analytic 48.76), "
          f"beta={r.get('plasma_beta'):.3f} (analytic 0.694)")


def case_solar_cycle() -> None:
    """NOAA Solar Cycle Progression against the published cycle-24 maximum.

    Anchor: solar cycle 24's smoothed sunspot number peaked at 116.4 in
    April 2014 (final international SSN, immutable). Also sanity-check that
    the cycle-25 smoothed peak lands in late 2024 at 150-165.
    """
    import pandas as pd
    r = run_tool("fetch_solar_cycle", start="2008-12")
    if r["status"] != "ok":
        check("solarcycle.fetch", False, r.get("error", ""))
        return
    df = pd.read_csv(r["file"], index_col="time", parse_dates=True)
    sc24 = df.loc["2009":"2019", "smoothed_ssn"].dropna()
    ok24 = abs(sc24.max() - 116.4) < 0.5 and str(sc24.idxmax())[:7] == "2014-04"
    check("solarcycle.sc24_peak", ok24,
          f"SC24 smoothed max {sc24.max():.1f} at {str(sc24.idxmax())[:7]} "
          "(published: 116.4, 2014-04)")
    sc25 = df.loc["2020":, "smoothed_ssn"].dropna()
    if len(sc25):
        peak_month = str(sc25.idxmax())[:7]
        ok25 = 150 <= sc25.max() <= 165 and peak_month.startswith("2024")
        check("solarcycle.sc25_peak", ok25,
              f"SC25 smoothed max {sc25.max():.1f} at {peak_month} "
              "(expected 150-165 in 2024)")


def case_cotrans() -> None:
    """Coordinate transform against an independent implementation.

    Anchor: pySPEDAS cotrans (used by transform_coordinates) must agree with
    geopack's GSE->GSM rotation to < 0.01 nT on random vectors, and preserve
    magnitude. Field-line trace: geosynchronous noon footpoints land in the
    auroral zone (55-75 deg) on a closed line (T89, kp=2).
    """
    import numpy as np
    import pandas as pd
    from helio_agent.workspace import data_path

    times = pd.date_range("2017-09-06", periods=24, freq="1h")
    rng = np.random.default_rng(42)
    vecs = rng.normal(0, 5, (24, 3))
    df = pd.DataFrame(vecs, columns=["bx", "by", "bz"], index=times)
    df.index.name = "time"
    fpath = data_path("_validation_cotrans.csv")
    df.to_csv(fpath, index_label="time")
    r = run_tool("transform_coordinates", file=str(fpath),
                 columns=["bx", "by", "bz"], from_coords="gse",
                 to_coords="gsm")
    if r["status"] != "ok":
        check("cotrans.transform", False, r.get("error", ""))
        return
    out = pd.read_csv(r["file"], index_col="time", parse_dates=True)
    from geopack import geopack
    gp = np.empty_like(vecs)
    for i, t in enumerate(times):
        geopack.recalc((t - pd.Timestamp(0)) / pd.Timedelta(seconds=1))
        gp[i] = geopack.gsmgse(*vecs[i], -1)
    py = out[["x_gsm", "y_gsm", "z_gsm"]].values
    maxdiff = float(np.abs(py - gp).max())
    mag_ok = np.allclose(np.linalg.norm(py, axis=1),
                         np.linalg.norm(vecs, axis=1), atol=1e-6)
    check("cotrans.cross_implementation", maxdiff < 0.01 and mag_ok,
          f"pyspedas vs geopack max component diff {maxdiff:.2e} nT "
          "(tolerance 0.01); magnitude preserved: " + str(mag_ok))
    t = run_tool("trace_field_line", x_gsm_re=6.6, y_gsm_re=0.0,
                 z_gsm_re=0.0, time="2017-09-06T12:00:00", kp=2)
    nf = t.get("north_footpoint") or {}
    ok = (t.get("topology") == "closed"
          and 55 <= nf.get("geo_lat_deg", 0) <= 75)
    check("cotrans.field_trace", ok,
          f"geosync noon footpoint {nf.get('geo_lat_deg')} deg GEO, "
          f"{t.get('topology')} (expect auroral zone 55-75, closed)")


def case_indices() -> None:
    """Kyoto WDC Dst and GFZ Kp against immutable published values.

    Anchors: Kyoto FINAL Dst 2003-10 minimum -383 nT, 744 hourly records;
    GFZ definitive Kp reached 9.0 during the 2024-05-10/11 Gannon storm.
    """
    r = run_tool("fetch_kyoto_dst", year=2003, month=10, revision="final")
    ok = (r["status"] == "ok" and r.get("revision") == "final"
          and r.get("n_records") == 744 and r.get("dst_min_nT") == -383.0)
    check("indices.kyoto_dst", ok,
          f"final Dst 2003-10: min {r.get('dst_min_nT')} nT, "
          f"{r.get('n_records')} records (published: -383, 744)")
    g = run_tool("fetch_gfz_index", index="Kp", start="2024-05-10",
                 end="2024-05-12")
    ok = g["status"] == "ok" and g.get("max_value") == 9.0
    check("indices.gfz_kp", ok,
          f"GFZ Kp max {g.get('max_value')} for Gannon storm (published: 9.0)")


def case_dst_model() -> None:
    """O'Brien-McPherron Dst nowcast on the 2015 St. Patrick's Day storm.

    Anchor: driven by OMNI hourly V/Bz/N, the model must correlate > 0.9
    with observed Dst and put the minimum within the storm's main day
    (2015-03-17/18). OBM2000 underpredicts extreme minima by design; the
    check allows up to 80 nT of minimum underprediction.
    """
    r = run_tool("fetch_omni", start="2015-03-15T00:00:00Z",
                 end="2015-03-20T00:00:00Z",
                 variables=["V1800", "BZ_GSM1800", "N1800", "DST1800"])
    if r["status"] != "ok":
        check("dstmodel.fetch", False, r.get("error", ""))
        return
    m = run_tool("model_dst", file=r["file"], v_column="V1800",
                 bz_column="BZ_GSM1800", density_column="N1800",
                 dst_column="DST1800")
    sk = m.get("skill", {})
    ok = (m["status"] == "ok" and sk.get("corr", 0) > 0.9
          and abs(sk.get("min_error_nT", 999)) <= 80
          and m.get("time_of_model_min", "").startswith(("2015-03-17", "2015-03-18")))
    check("dstmodel.stpatrick2015", ok,
          f"corr={sk.get('corr')}, rmse={sk.get('rmse_nT')} nT, "
          f"model min {m.get('model_min_nT')} vs obs {sk.get('obs_min_nT')} nT "
          f"at {m.get('time_of_model_min')}")


def case_cme_arrival() -> None:
    """Drag-based CME arrival for the 2012-07-12 halo CME.

    Anchor: DONKI CMEAnalysis gives v0=1400 km/s at 21.5 Rs (19:35 UT);
    the interplanetary shock reached Earth 2012-07-14 17:26 UT (DONKI IPS).
    The DBM estimate must land within 10 h and the ensemble window must
    contain the observed arrival.
    """
    import pandas as pd
    r = run_tool("cme_arrival", v0_kms=1400.0,
                 launch_time="2012-07-12T19:35Z", w_kms=400.0)
    if r["status"] != "ok":
        check("cmearrival.dbm", False, r.get("error", ""))
        return
    obs = pd.Timestamp("2012-07-14T17:26Z")
    est = pd.Timestamp(r["arrival_estimate"])
    lo, hi = (pd.Timestamp(t) for t in r["arrival_window"])
    err_h = abs((est - obs).total_seconds()) / 3600
    ok = err_h <= 10 and lo <= obs <= hi
    check("cmearrival.20120712", ok,
          f"estimate {est} vs observed {obs} ({err_h:.1f} h error, "
          "tolerance 10 h); window contains observed: " + str(lo <= obs <= hi))


def case_plot_solar_regions() -> None:
    """Region annotation on the 2017-09-06 HMI magnetogram.

    Anchor (analytic, and stronger than a citation): for a region at
    heliographic (lat, lon) seen with the observer at heliographic latitude
    B0, the projected distance from disk centre is r/R = sin(arccos(sin lat
    sin B0 + cos lat cos B0 cos lon)). Three regions spanning the disk must
    match that identity to better than 0.01 R_sun. The residual is expected
    and small: the identity assumes an orthographic view from infinity while
    the map's WCS carries SDO's finite distance.

    The same three coordinates plotted on a flat lat/lon sketch that ignores
    B0 (+7.24 deg on this date) land up to 151 pixels — 0.08 R_sun — off,
    which is the whole reason this tool exists.

    AR 12673 is the X9.3 source at S09W33, Fkc / beta-gamma-delta (SWPC
    region summary for 2017-09-06); the magnetogram case measures >2 kG and
    a delta-class PIL at those same coordinates independently.
    """
    import glob
    import math

    import astropy.units as u
    import sunpy.map

    r = run_tool("fetch_vso", start="2017-09-06T11:00:00", end="2017-09-06T11:20:00",
                 instrument="HMI", max_files=1, physobs="LOS_magnetic_field")
    if r["status"] != "ok" or not r["files"]:
        check("regions.fetch", False, r.get("error", "no file"))
        return
    f = r["files"][0]
    regs = [{"region": 12673, "location": "S09W33", "spot_class": "Fkc",
             "mag_class": "BGD"},
            {"region": 12674, "location": "N14W12", "spot_class": "Dai",
             "mag_class": "B"},
            {"region": 12675, "location": "N08E60", "spot_class": "Hsx",
             "mag_class": "A"},
            {"region": 99999, "location": "S10W120"}]
    m = run_tool("plot_solar_regions", fits_file=f, regions=regs,
                 region_time="2017-09-06T11:01:30", out_name="_validation_regions.png")
    if m["status"] != "ok":
        check("regions.project", False, m.get("error", ""))
        return

    smap = sunpy.map.Map(f)
    b0 = math.radians(float(smap.observer_coordinate.lat.to_value(u.deg)))
    cx, cy = smap.world_to_pixel(smap.center)
    cx, cy = cx.to_value(u.pix), cy.to_value(u.pix)
    rpix = float((smap.rsun_obs / smap.scale[0]).to_value(u.pix))
    worst, naive_worst = 0.0, 0.0
    for e in m["annotated"]:
        lat, lon = math.radians(e["lat_deg"]), math.radians(e["lon_deg"])
        cos_ca = math.sin(lat) * math.sin(b0) + math.cos(lat) * math.cos(b0) * math.cos(lon)
        r_an = math.sin(math.acos(cos_ca))
        r_wcs = math.hypot(e["pixel_x"] - cx, e["pixel_y"] - cy) / rpix
        worst = max(worst, abs(r_an - r_wcs))
        naive = math.sin(math.acos(math.cos(lat) * math.cos(lon)))
        naive_worst = max(naive_worst, abs(naive - r_an) * rpix)

    limb = [e["region"] for e in m["off_disk"]]
    ar73 = next((e for e in m["annotated"] if e["region"] == 12673), None)
    ok = (len(m["annotated"]) == 3 and limb == [99999] and worst < 0.01
          and ar73 is not None and ar73["hale_greek"] == "βγδ"
          and "Fkc/βγδ" in ar73["label"] and m["age_hours"] < 0.1)
    check("regions.project", ok,
          f"3 on disk + W120 behind the limb; worst |analytic - WCS| "
          f"{worst:.5f} R_sun (gate 0.01); a B0-blind sketch would miss by "
          f"{naive_worst:.0f} px; AR12673 labelled {ar73['label'] if ar73 else '?'!r}")

    stale = run_tool("plot_solar_regions", fits_file=f, regions=regs[:1],
                     region_time="2017-09-04T11:00:00", out_name="_validation_regions.png")
    ok2 = (stale["status"] == "error" and "max_age_hours" in stale["error"]
           and "rotation" in stale["error"])
    check("regions.stale_refusal", ok2,
          stale.get("error", "")[:150] if ok2 else f"expected refusal, got {stale['status']}")


def case_flare_probability() -> None:
    """Per-region flare probabilities from the McIntosh classification.

    Anchor: McCloskey, Gallagher & Bloomfield (2016), Sol. Phys. 291, 1711,
    Table 5 (arXiv:1607.00903) — 24-hour flaring rates for sunspot groups
    within +/-75 deg longitude, indexed by yesterday's and today's modified
    Zurich class. Four published cells must come back exactly: D->D and F->F
    at 0.68 and 2.43 flares/24 h for >=C1.0, H->D at 0.89 (upward evolution
    flares more than persistence, the paper's headline), and F->F at 0.07 for
    >=X1.0. Probabilities are the Poisson complement 1 - exp(-rate), so
    D->D must give 0.4934.

    Structure the table must also satisfy: rates rise monotonically A < C <
    D < E < F for >=C1.0 persistence, and P(>=C) >= P(>=M) >= P(>=X) for
    every class. Empty bins (E -> A has no groups) refuse rather than
    returning zero.
    """
    import math

    cells = [("Dxx", "Dxx", "C", 0.68), ("Fxx", "Fxx", "C", 2.43),
             ("Dxx", "Hxx", "C", 0.89), ("Fxx", "Fxx", "X", 0.07)]
    bad = []
    for now, prev, lvl, want in cells:
        r = run_tool("flare_probability", mcintosh_class=now, previous_class=prev)
        if r["status"] != "ok":
            bad.append(f"{prev[0]}->{now[0]} {lvl}: {r.get('error')}")
            continue
        got = r["levels"][lvl]["rate_per_24h"]
        if abs(got - want) > 1e-9:
            bad.append(f"{prev[0]}->{now[0]} >={lvl}1.0: got {got}, table says {want}")

    dd = run_tool("flare_probability", mcintosh_class="Dxx")
    poisson_ok = abs(dd["levels"]["C"]["probability"] - (1 - math.exp(-0.68))) < 5e-5

    rates, mono_ok = [], True
    for z in ("Axx", "Cxx", "Dxx", "Exx", "Fxx"):
        r = run_tool("flare_probability", mcintosh_class=z)
        rates.append(r["levels"]["C"]["rate_per_24h"])
        p = [r["levels"][k]["probability"] for k in ("C", "M", "X")]
        mono_ok = mono_ok and p[0] >= p[1] >= p[2]
    rising = all(a < b for a, b in zip(rates, rates[1:]))

    empty = run_tool("flare_probability", mcintosh_class="Axx", previous_class="Exx")
    junk = run_tool("flare_probability", mcintosh_class="Zxx")
    refuses = (empty["status"] == "error" and "no groups" in empty["error"]
               and junk["status"] == "error" and "Zurich" in junk["error"])

    ok = not bad and poisson_ok and rising and mono_ok and refuses
    check("flareprob.mccloskey2016", ok,
          "; ".join(bad) if bad else
          f">=C1.0 persistence rates A..F {rates} rise monotonically; D->D "
          f"P={dd['levels']['C']['probability']} = 1-exp(-0.68); H->D 0.89 > "
          f"D->D 0.68 (upward evolution flares more); C>=M>=X ordering holds; "
          f"empty bin and bad class both refuse")

    hax = run_tool("flare_probability", mcintosh_class="Hax", lon_deg=79.0)
    honest = (hax["status"] == "ok"
              and hax["levels"]["C"]["rate_resolved"] is True
              and hax["levels"]["X"]["rate_resolved"] is False
              and hax["outside_calibration"] is True
              and hax["assumed_no_evolution"] is True
              and any("Hale" in c for c in hax["caveats"]))
    check("flareprob.honesty", honest,
          f"Hax at W79: C resolved, X not (upper limit "
          f"{hax['levels']['X']['probability_range'][1]:.3f}), flagged outside "
          f"the +/-75 deg calibration, no-evolution assumption declared, and "
          f"the Hale-class blindness stated in caveats")


def case_sunspot_reports() -> None:
    """SWPC raw station reports and their consensus.

    This is a rolling ~1-month operational feed, so there is no fixed
    published value to pin. The anchors are therefore invariants of the
    product plus a cross-source check, which is what can honestly be
    asserted about live data:

    (i) every consensus is internally consistent — the Zurich votes sum to
    at most the report count, the agreement fraction equals the winner's
    share, and a tie always leaves zurich_consensus None rather than
    picking one of two letters that can differ by 3x in flare probability;
    (ii) region numbers in the latest station reports overlap the edited
    daily summary from get_solar_regions, which is the independent product
    built from these same observations;
    (iii) a date outside the window refuses and names the coverage.

    The disagreement this exposes is the point: observatories differ on the
    McIntosh class for a large fraction of region-days, and the Zurich
    letter — the only one the flare rates use — is not exempt.
    """
    r = run_tool("get_sunspot_reports", date="all")
    if r["status"] != "ok":
        check("sunspots.fetch", False, r.get("error", ""))
        return

    bad = []
    for c in r["consensus"]:
        votes = c["zurich_votes"]
        if sum(votes.values()) > c["n_reports"]:
            bad.append(f"{c['date']} AR{c['region']}: votes exceed reports")
        if c["tie"] and c["zurich_consensus"] is not None:
            bad.append(f"{c['date']} AR{c['region']}: tie resolved to "
                       f"{c['zurich_consensus']}")
        if votes and not c["tie"]:
            top = max(votes.values())
            if c["zurich_consensus"] is None:
                bad.append(f"{c['date']} AR{c['region']}: no consensus without a tie")
            elif abs(c["zurich_agreement"] - top / sum(votes.values())) > 1e-3:
                bad.append(f"{c['date']} AR{c['region']}: agreement mismatch")
        if c["zurich_agreement"] is not None and not 0 < c["zurich_agreement"] <= 1:
            bad.append(f"{c['date']} AR{c['region']}: agreement out of range")

    n = len(r["consensus"])
    n_dis = sum(1 for c in r["consensus"] if c["classes_disagree"])
    n_tie = sum(1 for c in r["consensus"] if c["tie"])
    ok = not bad and n > 0
    check("sunspots.consensus", ok, "; ".join(bad[:3]) if bad else
          f"{n} region-days over {r['coverage'][0]}..{r['coverage'][1]}, all "
          f"consistent; {n_dis} ({n_dis / n:.0%}) have observatories "
          f"disagreeing on the McIntosh class and {n_tie} are Zurich ties "
          f"left unresolved")

    today = run_tool("get_sunspot_reports")
    summary = run_tool("get_solar_regions")
    if today["status"] == "ok" and summary["status"] == "ok":
        station = {c["region"] for c in today["consensus"]}
        edited = {g["region"] for g in summary["regions"] if g.get("spot_class")}
        overlap = station & edited
        ok2 = bool(station) and bool(edited) and len(overlap) >= 1
        check("sunspots.vs_edited_summary", ok2,
              f"station reports cover AR{sorted(station)}, edited summary "
              f"classifies AR{sorted(edited)}, {len(overlap)} in common "
              "(the edited class is not a straight vote of these — that is "
              "why get_solar_regions stays the authority)")

    stale = run_tool("get_sunspot_reports", date="1999-01-01")
    check("sunspots.window_refusal",
          stale["status"] == "error" and "rolling" in stale.get("error", ""),
          stale.get("error", "")[:130])


def case_extreme_value() -> None:
    """POT/GPD on the 61-year hourly Dst record.

    Anchors: intense storms (Dst <= -100 nT, 48 h declustering) occur at
    4-7 per year (literature: ~5-6); the strongest declustered event is
    March 1989 at -589 nT (immutable); the 100-yr return level lands in
    the published -450 to -700 nT band.
    """
    r = run_tool("fetch_cdaweb_data", dataset="OMNI2_H0_MRG1HR",
                 variables=["DST1800"], start="1964-01-01T00:00:00Z",
                 end="2024-12-31T23:00:00Z")
    if r["status"] != "ok":
        check("extremes.fetch", False, r.get("error", ""))
        return
    e = run_tool("extreme_value", file=r["file"], column="DST1800",
                 threshold=-100.0, direction="min")
    if e["status"] != "ok":
        check("extremes.gpd", False, e.get("error", ""))
        return
    top = e["strongest_events"][0]
    lvl100 = e["return_levels"].get("100yr")
    ok = (4 <= e["events_per_year"] <= 7
          and top["time"].startswith("1989-03") and top["value"] == -589.0
          and lvl100 is not None and -700 <= lvl100 <= -450)
    check("extremes.dst_pot", ok,
          f"{e['events_per_year']}/yr above -100 nT; strongest {top['value']} "
          f"at {top['time'][:10]} (published: -589, 1989-03-14); "
          f"100-yr level {lvl100} nT (band -450..-700)")


def case_aia_degradation() -> None:
    """aiapy degradation factors against known sensitivity history.

    Anchors: at 2010-06-01 (weeks after first light) 171 A is within 5% of
    1.0 while 304 A has already dropped to 0.8-1.0 (its rapid early
    degradation is real and documented); by 2020-01-01, 304 A is below 0.35
    (>65% sensitivity lost) while 171 A remains in 0.5-0.9.
    """
    r0 = run_tool("aia_degradation", date="2010-06-01", channels=[171, 304])
    r1 = run_tool("aia_degradation", date="2020-01-01", channels=[171, 304])
    if "error" in (r0.get("status"), r1.get("status")):
        check("aia.degradation", False, str(r0.get("error") or r1.get("error")))
        return
    f0, f1 = r0["degradation_factors"], r1["degradation_factors"]
    ok = (abs(f0["171"] - 1) < 0.05 and 0.8 <= f0["304"] <= 1.0
          and f1["304"] < 0.35 and 0.5 <= f1["171"] <= 0.9)
    check("aia.degradation", ok,
          f"2010: 171={f0['171']} (~1), 304={f0['304']} (0.8-1.0, early "
          f"drop is real); 2020: 171={f1['171']} (0.5-0.9), "
          f"304={f1['304']} (<0.35)")


def case_verify_claim() -> None:
    """Claim verifier behavior: match, mismatch, and refusals."""
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500.0)
    audit_id = measured["audit_id"]
    value = measured["delay_minutes"]
    m = run_tool("verify_claim", claimed_value=value, computed_value=value,
                 claimed_units="min", computed_units="minutes",
                 tolerance_percent=1.0, computed_audit_id=audit_id)
    bad_units = run_tool("verify_claim", claimed_value=500.0,
                         computed_value=value, claimed_units="km/s",
                         computed_units="min", computed_audit_id=audit_id)
    no_audit = run_tool("verify_claim", claimed_value=1.0, computed_value=1.0,
                        claimed_units="nT", computed_units="nT",
                        computed_audit_id="")
    mis = run_tool("verify_claim", claimed_value=100.0, computed_value=value,
                   claimed_units="min", computed_units="minutes",
                   tolerance_percent=10.0, computed_audit_id=audit_id)
    ok = (m.get("verdict") == "match"
          and bad_units.get("verdict") == "refused"
          and no_audit.get("verdict") == "refused"
          and mis.get("verdict") == "mismatch")
    check("verify.claim_logic", ok,
          f"match={m.get('verdict')}, unit-mismatch={bad_units.get('verdict')}, "
          f"no-audit={no_audit.get('verdict')}, off-by-50%={mis.get('verdict')}")


def case_repro_20120723() -> None:
    """Paper reproduction: the 2012-07-23 extreme CME at STEREO-A.

    Immutable anchors (Baker et al. 2013 SpWea; Russell et al. 2013 ApJ;
    Cash et al. 2015 SpWea; reproduced end-to-end 2026-09-02): shock arrival
    2012-07-23 20:55 UT in STA_L2_MAGPLASMA_1M |B|, peak field 109.1 nT at
    2012-07-24 ~00:52 UT, spacecraft at 0.964 AU. Also asserts the DOCUMENTED
    L2 plasma gap over the event (PLASTIC moments unusable in the extreme
    flow) — if a future reprocessing fills it, this check flags the change
    rather than letting an old caveat silently go stale.
    """
    import numpy as np
    import pandas as pd
    r = run_tool("fetch_cdaweb_data", dataset="STA_L2_MAGPLASMA_1M",
                 variables=["BTOTAL", "Vp", "Np", "R"],
                 start="2012-07-22T00:00:00Z", end="2012-07-27T00:00:00Z")
    if r["status"] != "ok":
        check("repro20120723.fetch", False, r.get("error", ""))
        return
    df = pd.read_csv(r["file"], index_col="time", parse_dates=True)
    b = df["BTOTAL"]
    pre = b.loc["2012-07-23 12:00":"2012-07-23 20:00"].mean()
    late = b.loc["2012-07-23 20:00":"2012-07-23 23:59"]
    shock = late[late > 2.5 * pre].index[0]
    peak_b = float(b.max())
    t_peak = b.idxmax()
    r_au = float(df["R"].mean())
    ok = (str(shock)[:16] == "2012-07-23 20:55"
          and abs(peak_b - 109.1) < 0.5
          and str(t_peak).startswith("2012-07-24 00:5")
          and abs(r_au - 0.964) < 0.002)
    check("repro20120723.insitu", ok,
          f"shock {shock} (published 20:55 UT), peak |B| {peak_b:.1f} nT "
          f"at {t_peak} (published 109), R {r_au:.4f} AU (0.96)")
    vp_gap = df.loc["2012-07-23 12:00":"2012-07-25 12:00", "Vp"]
    gap_ok = vp_gap.isna().mean() > 0.8  # sporadic points exist inside the gap
    check("repro20120723.l2_plasma_gap", gap_ok,
          f"L2 Vp NaN fraction over the event: {vp_gap.isna().mean():.2f} "
          "(the documented PLASTIC gap; impact-speed claims stay blocked at "
          "L2 while this holds)")
    _ = np.asarray  # keep numpy import used if pandas paths change


def case_export_html() -> None:
    """Self-hosted HTML export (export_html) sanity.

    Anchor: a markdown sample with heading + mermaid + math converts to a
    standalone page containing the inlined template styles, the SRI-pinned
    client runtime, and the source content. Requires UNMARKDOWN_API_KEY;
    without it the tool must refuse cleanly (that refusal is what CI checks).
    """
    import os
    from helio_agent.workspace import DATA_DIR, ensure_dirs
    ensure_dirs()
    sample = DATA_DIR / "_validation_export.md"
    sample.write_text("# Export check\n\nInline math $v_A$.\n\n"
                      "```mermaid\nflowchart LR\n  A --> B\n```\n")
    r = run_tool("export_html", markdown_file=str(sample),
                 out_name="_validation_export.html")
    if not os.environ.get("UNMARKDOWN_API_KEY"):
        ok = r.get("status") == "error" and "UNMARKDOWN_API_KEY" in r.get("error", "")
        check("export.refusal_without_key", ok,
              "no key in this environment; tool must refuse with a reason "
              f"(got: {r.get('error', r.get('status'))!r}). Full render is "
              "validated in keyed environments.")
        return
    if r.get("status") != "ok":
        check("export.render", False, r.get("error", ""))
        return
    html = open(r["file"]).read()
    ok = ("Export check" in html and "integrity=\"sha384-" in html
          and "language-mermaid" in html and "font-family" in html)
    check("export.render", ok,
          f"{r['bytes']} bytes; template styles inlined, SRI-pinned runtime "
          f"present, mermaid block passed through for client render")


def case_detect_icme() -> None:
    """ICME detection on the 2015 St. Patrick's Day storm (1-min OMNI).

    Anchor: Richardson & Cane near-Earth ICME list — shock 2015-03-17
    04:45 UT, ICME 2015-03-17 13:00 to 2015-03-18 05:00 UT (Dst -234 nT).
    Shock must land within 30 min, the ICME start within 2 h, the end within
    3 h (catalog boundaries are judgement calls, hours-level disagreement is
    normal), the driver attribution must be the ejecta (the storm minimum
    fell inside the cloud), and the pre-shock cold interval of 03-16 must be
    ignored.
    """
    import pandas as pd
    r = run_tool("fetch_omni", start="2015-03-16T00:00:00Z",
                 end="2015-03-19T00:00:00Z", resolution="1min",
                 variables=["flow_speed", "T", "proton_density", "BY_GSM", "BZ_GSM"])
    if r["status"] != "ok":
        check("icme.fetch", False, r.get("error", ""))
        return
    m = run_tool("detect_icme", file=r["file"], speed_column="flow_speed",
                 temperature_column="T", by_column="BY_GSM", bz_column="BZ_GSM",
                 density_column="proton_density", out_name="_validation_icme.png")
    if m["status"] != "ok" or m["icme"] is None:
        check("icme.stpatrick2015", False, m.get("error") or m.get("note", ""))
        return
    def h(a, b):  # tool timestamps are naive UTC
        return abs((pd.Timestamp(a) - pd.Timestamp(b)).total_seconds()) / 3600
    d_shock = h(m["shock_time"], "2015-03-17 04:45")
    d_start = h(m["icme"]["start"], "2015-03-17 13:00")
    d_end = h(m["icme"]["end"], "2015-03-18 05:00")
    ok = (d_shock <= 0.5 and d_start <= 2 and d_end <= 3
          and m["driver"] == "ejecta" and "pre-shock" in m["note"])
    check("icme.stpatrick2015", ok,
          f"shock {m['shock_time']} ({d_shock*60:.0f} min off), ICME "
          f"{m['icme']['start']} -> {m['icme']['end']} ({d_start:.1f} h / {d_end:.1f} h off "
          f"R&C 13:00 -> 05:00), driver={m['driver']}, "
          f"rotation {m['icme']['rotation_deg']} deg r2={m['icme']['rotation_r2']}")


def case_characterize_sep() -> None:
    """SEP characterization for the 2017-09-10 X8.2 event (hourly OMNI protons).

    Anchor: NOAA/SWPC S3 radiation storm — GOES >10 MeV onset 2017-09-10
    16:45 UT, peak 1490 pfu at 2017-09-11 11:45 UT; parent flare X8.2 peak
    16:06 UT from AR 12673 at S08W88 (a ground-level enhancement, GLE 72,
    i.e. a well-connected, prompt event). OMNI hourly fluxes are averaged
    half-hour-midpoint samples from a different sensor chain, so the peak
    must land within 1 h and 800-1500 pfu (S3 either way), the onset within
    2 h, and the >30 MeV channel must cross 1 pfu no later than the >10 MeV
    onset (velocity dispersion). OMNI proton fluxes end 2020-03.
    """
    import pandas as pd
    r = run_tool("fetch_omni", start="2017-09-09T00:00:00Z",
                 end="2017-09-16T00:00:00Z",
                 variables=["PR-FLX_101800", "PR-FLX_301800", "V1800"])
    if r["status"] != "ok":
        check("sep.fetch", False, r.get("error", ""))
        return
    m = run_tool("characterize_sep", file=r["file"], flux_10mev_column="PR-FLX_101800",
                 flux_30mev_column="PR-FLX_301800",
                 flare_peak_time="2017-09-10T16:06:00Z", flare_class="X8.2",
                 flare_lon_deg=88.0, out_name="_validation_sep.png")
    if m["status"] != "ok" or m["sep"] is None:
        check("sep.20170910", False, m.get("error") or m.get("note", ""))
        return
    def h(a, b):  # tool timestamps are naive UTC
        return abs((pd.Timestamp(a) - pd.Timestamp(b)).total_seconds()) / 3600
    sep, ph = m["sep"], m["physics"]
    d_onset = h(sep["onset"], "2017-09-10 16:45")
    d_peak = h(sep["peak_10mev"]["time"], "2017-09-11 11:45")
    peak = sep["peak_10mev"]["value"]
    ok = (sep["s_scale"] == "S3" and d_onset <= 2 and d_peak <= 1
          and 800 <= peak <= 1500 and ph is not None
          and ph["dispersion_minutes"] is not None and ph["dispersion_minutes"] >= 0
          and 0 < ph["onset_delay_hours"] <= 3)
    check("sep.20170910", ok,
          f"{sep['s_scale']}, onset {sep['onset']} ({d_onset:.1f} h off 16:45), peak "
          f"{peak:g} pfu at {sep['peak_10mev']['time']} ({d_peak:.1f} h off; GOES 1490), "
          f"hardness {sep['hardness_ratio']}, onset {ph['onset_delay_hours']} h after X8.2 "
          f"(expect {ph['expected_delay_hours_10mev']} h), >30 MeV led by "
          f"{ph['dispersion_minutes']} min, connection {ph['connection_angle_deg']} deg")


def case_goes_protons() -> None:
    """GOES integral proton flux: the measured legacy archive, the derived
    GOES-R reconstruction, and a two-spacecraft cross-check.

    Anchor 1 (measured): NOAA/SWPC put the 2017-09-10 S3 radiation storm's
    GOES >10 MeV peak at 1490 pfu on 2017-09-11 11:45 UT. This reads the
    same EPEAD 'cpflux' archive SWPC did, so it must land within 200 pfu and
    30 minutes -- far tighter than the OMNI-based sep case, which sees a
    different sensor chain.

    Anchor 2 (method): the GOES-R era has no archived >10 MeV integral
    channel, so fetch_goes_protons integrates the SGPS differential
    spectrum. Checked against SWPC's own operational 7-day feed on a window
    two days back (NCEI lags ~1 day, SWPC keeps 7, so the overlap always
    exists). p_gt10 must sit within 0.7-1.4x of the operational value and
    the passthrough p_gt500 within 0.9-1.1x. p_gt30 and above are NOT
    checked here: at quiet background they run 2-3x low by construction
    (GCR above ~390 MeV is unsampled), which the tool's note states.

    Anchor 3 (independent instrument): GOES-16 (GOES-East) and GOES-18
    (GOES-West) are separate spacecraft with separate SGPS units. Across the
    2024-05-10 Gannon SEP event their derived >10 MeV series must track each
    other to within 30% in the median while the event is above 50 pfu, and
    both must reach S2 (>=100 pfu). Instantaneous peaks are deliberately NOT
    compared: the prompt onset is strongly anisotropic, and the two
    spacecraft sit at different magnetic local times, so GOES-16 reads about
    twice GOES-18 for the ~1 h spike while the rest of the event agrees to a
    few percent. That spread is physics, not a reduction error.
    """
    from datetime import datetime, timedelta, timezone

    import pandas as pd
    import requests

    # --- anchor 1: measured legacy archive, 2017-09-10 S3 event ---
    r = run_tool("fetch_goes_protons", start="2017-09-09T00:00:00Z",
                 end="2017-09-16T00:00:00Z", satellite="goes13")
    if r["status"] != "ok":
        check("protons.legacy20170910", False, r.get("error", ""))
    else:
        df = pd.read_csv(r["file"], index_col=0, parse_dates=True)
        peak, t_peak = df["p_gt10"].max(), df["p_gt10"].idxmax()
        d_min = abs((t_peak - pd.Timestamp("2017-09-11 11:45")).total_seconds()) / 60
        ok = (not r["derived"] and abs(peak - 1490) <= 200 and d_min <= 30
              and df["p_gt100"].max() > df["p_gt10"].max() * 1e-3)
        check("protons.legacy20170910", ok,
              f"measured >10 MeV peak {peak:.0f} pfu at {t_peak} "
              f"({d_min:.0f} min off 11:45; SWPC 1490), >100 MeV peak "
              f"{df['p_gt100'].max():.1f} pfu, {r['n_records']} samples "
              f"from {r['source']}")

    # --- anchor 2: derived GOES-R vs the SWPC operational feed ---
    feed = ("https://services.swpc.noaa.gov/json/goes/primary/"
            "integral-protons-7-day.json")
    try:
        rows = requests.get(feed, timeout=90).json()
    except Exception as exc:  # noqa: BLE001
        check("protons.derived_vs_swpc", False, f"SWPC feed unreachable: {exc}")
        rows = None
    if rows:
        sat = f"goes{sorted({d['satellite'] for d in rows})[-1]}"
        b = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0,
                                               microsecond=0) - timedelta(days=2)
        a = b - timedelta(days=2)
        g = run_tool("fetch_goes_protons", start=a.strftime("%Y-%m-%dT00:00:00Z"),
                     end=b.strftime("%Y-%m-%dT00:00:00Z"), satellite=sat)
        if g["status"] != "ok":
            check("protons.derived_vs_swpc", False, g.get("error", ""))
        else:
            d = pd.read_csv(g["file"], index_col=0, parse_dates=True)
            ratios = {}
            for lbl, col in ((">=10 MeV", "p_gt10"), (">=500 MeV", "p_gt500")):
                sw = pd.Series({pd.Timestamp(x["time_tag"]).tz_localize(None):
                                x["flux"] for x in rows if x["energy"] == lbl})
                sw = sw.sort_index().resample("5min").mean()
                m = pd.concat([d[col].rename("o"), sw.rename("s")], axis=1,
                              sort=True).dropna()
                ratios[col] = float((m["o"] / m["s"]).median()) if len(m) else float("nan")
            ok = (g["derived"] and 0.7 <= ratios["p_gt10"] <= 1.4
                  and 0.9 <= ratios["p_gt500"] <= 1.1)
            check("protons.derived_vs_swpc", ok,
                  f"{sat} {a:%Y-%m-%d}..{b:%Y-%m-%d}: derived/operational "
                  f">10 MeV {ratios['p_gt10']:.2f}x, >500 MeV passthrough "
                  f"{ratios['p_gt500']:.2f}x")

    # --- anchor 3: GOES-16 vs GOES-18 on the 2024-05-10 Gannon SEP ---
    series = {}
    for sat in ("goes16", "goes18"):
        g = run_tool("fetch_goes_protons", start="2024-05-10T00:00:00Z",
                     end="2024-05-13T00:00:00Z", satellite=sat)
        if g["status"] != "ok":
            check("protons.gannon2024", False, f"{sat}: {g.get('error', '')}")
            return
        series[sat] = pd.read_csv(g["file"], index_col=0,
                                  parse_dates=True)["p_gt10"]
    both = pd.concat([series["goes16"].rename("g16"),
                      series["goes18"].rename("g18")], axis=1, sort=True).dropna()
    event = both[both["g18"] >= 50.0]
    ratio = float((event["g16"] / event["g18"]).median()) if len(event) else float("nan")
    peaks = {s: float(v.max()) for s, v in series.items()}
    ok = (0.7 <= ratio <= 1.3 and len(event) >= 50
          and min(peaks.values()) >= 100)  # both reach S2
    check("protons.gannon2024", ok,
          f"GOES-16 vs GOES-18 over the event ({len(event)} samples above 50 "
          f"pfu): median >10 MeV ratio {ratio:.2f}x; peaks "
          f"{peaks['goes16']:.0f} / {peaks['goes18']:.0f} pfu (both S2; the "
          f"prompt spike is anisotropic)")


def case_radio_bursts() -> None:
    """WIND/WAVES radio bursts for the 2017-09-06 X9.3 flare.

    Anchor: GOES X9.3 flare 11:53-12:02-12:10 UT from AR 12673; WIND/WAVES
    recorded an intense type III group at flare onset followed by a
    decametric-hectometric type II (CME-driven shock, CDAW/DONKI CME speed
    ~1500-2000 km/s) drifting down through the afternoon (e.g. Gopalswamy et
    al. 2018, ApJL 863, L39). At the 3-min K0 cadence the type III and type
    II merge into one burst, so the check is: a burst starting within 10 min
    of the flare onset, peaking above 40 dB within 15 min of the X-ray peak,
    spanning >= 2 decades of frequency, classified type III or type II
    candidate with a drift speed between 1000 and 10000 km/s. 2017-09-10 (the
    X8.2) is a WI_K0_WAV data gap and cannot serve.
    """
    import pandas as pd
    r = run_tool("fetch_cdaweb_spectrogram", start="2017-09-06T08:00:00Z",
                 end="2017-09-06T20:00:00Z")
    if r["status"] != "ok":
        check("radio.fetch", False, r.get("error", ""))
        return
    check("radio.fetch", r["n_channels"] == 76 and r["channel_units"] == "Hz",
          f"{r['n_records']} spectra x {r['n_channels']} channels "
          f"({r['channels'][0]:g}-{r['channels'][-1]:g} {r['channel_units']})")
    m = run_tool("radio_bursts", file=r["file"], out_name="_validation_radio.png")
    if m["status"] != "ok" or not m["bursts"]:
        check("radio.20170906", False, m.get("error") or m.get("note", ""))
        return
    def mins(a, b):
        return abs((pd.Timestamp(a) - pd.Timestamp(b)).total_seconds()) / 60
    flare = [b for b in m["bursts"] if mins(b["start"], "2017-09-06 11:53") <= 10]
    if not flare:
        check("radio.20170906", False,
              f"no burst within 10 min of 11:53; starts {[b['start'][11:16] for b in m['bursts']]}")
        return
    b = flare[0]
    import math
    decades = math.log10(b["freq_max_hz"] / b["freq_min_hz"])
    speed = b["inferred_speed_km_s"] or 0
    ok = (b["peak_db"] >= 40 and mins(b["peak_time"], "2017-09-06 12:02") <= 15
          and decades >= 2 and b["classification"] in ("type III", "type II candidate")
          and 1000 <= speed <= 10000)
    check("radio.20170906", ok,
          f"burst {b['start'][11:16]}-{b['end'][11:16]} UT, peak {b['peak_db']} dB at "
          f"{b['peak_time'][11:16]} (X9.3 peak 12:02), {b['freq_max_hz']:.3g}-"
          f"{b['freq_min_hz']:.3g} Hz ({decades:.1f} decades), {b['classification']} at "
          f"{speed:g} km/s; {m['n_bursts']} bursts in window: {m['counts']}")


def case_hindcast() -> None:
    """Forecast-rule hindcast over May 2024 (the Gannon superstorm month).

    Anchor: DONKI records the 2024-05-10 15:00 UT G5 storm (max Kp 9) driven
    by the 2024-05-08/09 halo CMEs (DONKI CMEAnalysis 1150-1560 km/s from
    AR 13664 near disk center) with the Earth shock at 16:36 UT on 05-10.
    The replayed monitor rule must cover that storm with a "high"-confidence
    window, the 2024-05-08T22:24 CME (1257 km/s) must score a hit within
    12 h, the high tier must reach >= 70% precision, and the hit MAE must
    stay within the drag model's stated +/- 15 h. DONKI is a living record;
    the counts drift as analysts revise fits, so only these invariants are
    asserted.
    """
    m = run_tool("hindcast_forecasts", start="2024-05-01", end="2024-05-31",
                 out_name="_validation_hindcast.png", table_name="_validation_hindcast.md")
    if m["status"] != "ok":
        check("hindcast.may2024", False, m.get("error", ""))
        return
    gannon = next((s for s in m["storms"] if s["gst_id"].startswith("2024-05-10")), None)
    halo = next((f for f in m["forecasts"] if f["cme_id"].startswith("2024-05-08T22:24")), None)
    high = next((r for r in m["confidence_rows"] if r["confidence"] == "high"), None)
    ok = (gannon is not None and gannon["forecast"] and gannon["best_confidence"] == "high"
          and gannon["observed_class"] == "superstorm"
          and halo is not None and halo["outcome"] == "hit"
          and abs(halo["timing_error_hours"]) <= 12
          and high is not None and high["precision"] is not None and high["precision"] >= 0.7
          and m["hit_mae_hours"] is not None and m["hit_mae_hours"] <= 15)
    check("hindcast.may2024", ok,
          f"{m['n_earth_directed']} windows, {m['n_hits']} hits / {m['n_false_alarms']} FA "
          f"(hit rate {m['hit_rate']}), high-tier precision {high['precision'] if high else None} "
          f"(n={high['n_windows'] if high else 0}), storm recall {m['n_storms_forecast']}/"
          f"{m['n_storms']}, hit MAE {m['hit_mae_hours']} h; Gannon covered="
          f"{gannon['forecast'] if gannon else None} ({gannon['best_confidence'] if gannon else None}), "
          f"05-08T22:24 halo {halo['outcome'] if halo else None} "
          f"{halo['timing_error_hours'] if halo else None} h")


def case_magnetogram() -> None:
    """HMI LOS magnetogram metrics for AR 12673 on 2017-09-06 11:01 UT.

    Anchor (order of magnitude, plus a qualitative delta-class check): AR
    12673, the source of the X9.3 at S09W33, was a compact delta-class
    region with umbral fields above 2 kG and an unsigned flux of a few
    10^22 Mx at the time of the flare (Sun & Norton 2017, RNAAS 1, 24; Yang
    et al. 2017, ApJL 849, L21). The 16-degree box must hold 1e22-1e23 Mx,
    peak |B| >= 1500 G, a strong-PIL chain >= 100 Mm threading >= 1e20 Mx,
    and at least 10x the unsigned flux of an equal quiet-Sun box at the
    mirrored longitude (no PIL there). Full-disk unsigned flux for a
    declining-phase day must land in 1e23-1e24 Mx. LOS fluxes carry no mu
    correction, so these are bounds, not a precision comparison.
    """
    r = run_tool("fetch_vso", start="2017-09-06T11:00:00", end="2017-09-06T11:20:00",
                 instrument="HMI", max_files=1, physobs="LOS_magnetic_field")
    if r["status"] != "ok" or not r["files"]:
        check("magnetogram.fetch", False, r.get("error", "no file"))
        return
    f = r["files"][0]
    check("magnetogram.fetch", "magnetogram" in f, f.rsplit("/", 1)[-1])
    m = run_tool("magnetogram_metrics", fits_file=f, lat_deg=-9.0, lon_deg=33.0,
                 half_deg=8.0, out_name="_validation_magnetogram.png")
    q = run_tool("magnetogram_metrics", fits_file=f, lat_deg=-9.0, lon_deg=-33.0,
                 half_deg=8.0, plot=False)
    if m["status"] != "ok" or q["status"] != "ok":
        check("magnetogram.ar12673", False, m.get("error") or q.get("error", ""))
        return
    a, b = m["region"], q["region"]
    ok = (1e22 <= a["unsigned_flux_mx"] <= 1e23 and a["max_abs_b_g"] >= 1500
          and a["pil_length_mm"] >= 100 and a["pil_flux_mx"] >= 1e20
          and a["unsigned_flux_mx"] >= 10 * b["unsigned_flux_mx"]
          and 1e23 <= m["disk_unsigned_flux_mx"] <= 1e24)
    check("magnetogram.ar12673", ok,
          f"AR box {a['unsigned_flux_mx']:.2e} Mx, max |B| {a['max_abs_b_g']:.0f} G, strong "
          f"PIL {a['pil_length_mm']:g} Mm ({a['pil_flux_mx']:.2e} Mx); mirrored quiet box "
          f"{b['unsigned_flux_mx']:.2e} Mx, PIL {b['pil_length_mm']:g} Mm; disk "
          f"{m['disk_unsigned_flux_mx']:.2e} Mx (published: a few 1e22 Mx, >2 kG, delta)")


CASES = {
    "halloween2003": case_halloween_2003,
    "flare20170906": case_flare_20170906,
    "rotation2017": case_solar_rotation,
    "ephemeris": case_ephemeris_l1,
    "pyspedas": case_pyspedas_crosscheck,
    "plasmapy": case_plasma_parameters,
    "solarcycle": case_solar_cycle,
    "cotrans": case_cotrans,
    "indices": case_indices,
    "dstmodel": case_dst_model,
    "cmearrival": case_cme_arrival,
    "icme": case_detect_icme,
    "sep": case_characterize_sep,
    "protons": case_goes_protons,
    "radio": case_radio_bursts,
    "hindcast": case_hindcast,
    "magnetogram": case_magnetogram,
    "regions": case_plot_solar_regions,
    "flareprob": case_flare_probability,
    "sunspots": case_sunspot_reports,
    "extremes": case_extreme_value,
    "aia": case_aia_degradation,
    "verify": case_verify_claim,
    "repro20120723": case_repro_20120723,
    "export": case_export_html,
}


def main() -> int:
    names = sys.argv[1:] or list(CASES)
    for n in names:
        print(f"\n== {n} ==")
        try:
            CASES[n]()
        except Exception as exc:  # noqa: BLE001
            check(n, False, f"exception: {exc}")
    n_fail = sum(1 for _, ok, _ in RESULTS if not ok)
    print(f"\n{len(RESULTS) - n_fail}/{len(RESULTS)} checks passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
