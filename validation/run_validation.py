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


CASES = {
    "halloween2003": case_halloween_2003,
    "flare20170906": case_flare_20170906,
    "rotation2017": case_solar_rotation,
    "ephemeris": case_ephemeris_l1,
    "pyspedas": case_pyspedas_crosscheck,
    "plasmapy": case_plasma_parameters,
    "solarcycle": case_solar_cycle,
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
