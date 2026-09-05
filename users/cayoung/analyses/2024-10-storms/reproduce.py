"""October 2024: survey the month, then carry the 10-11 Oct superstorm
from the Sun to the ground through audited tools only.

    HELIO_AGENT_USER=cayoung uv run python .../reproduce.py
    ... --only S5          # one section (prefix match)
    ... --fresh S5_sep     # re-run one step

Results cache to results.json beside this file; figures land in figures/.
Runs against live archives — tens of minutes on a cold cache.

No number in the report is typed by hand: render_report.py reads only this
cache. Values quoted from the literature are labelled as claims under test
and never used as inputs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIGS = HERE / "figures"
STATE = HERE / "results.json"
sys.path.insert(0, str(ROOT))

MONTH = {"start": "2024-10-01T00:00:00Z", "end": "2024-11-01T00:00:00Z"}
# The superstorm window: X1.8 on 09 Oct 01:56 UT -> shock 10 Oct 14:46 ->
# SYM-H minimum late on 10 Oct. Padded either side for the recovery.
SW = {"start": "2024-10-08T00:00:00Z", "end": "2024-10-14T00:00:00Z"}


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1, default=str))


def keep(name: str, path: str) -> str:
    p = Path(path)
    FIGS.mkdir(parents=True, exist_ok=True)
    dest = FIGS / f"{name}{p.suffix}"
    shutil.copy(p, dest)
    return dest.name


def run(st, only=None, fresh=()):
    from helio_agent.registry import run_tool

    def R(key, tool, **kw):
        if key in st and key not in fresh and (only is None or not key.startswith(only)):
            return st[key]
        if only and not key.startswith(only) and key in st:
            return st[key]
        print(f"  RUN {key}  ({tool})")
        r = run_tool(tool, **kw)
        if r.get("status") == "error":
            print(f"     FAIL {str(r.get('error'))[:110]}")
        st[key] = r
        save_state(st)
        return r

    # ---------------- S1: survey the whole month --------------------------
    print("S1 month survey")
    xrs = R("S1_xrs", "fetch_goes_xrs", **MONTH)
    if xrs.get("file"):
        for key, mc in (("S1_flares_x", "X1.0"), ("S1_flares_m", "M1.0"),
                        ("S1_flares_c", "C1.0")):
            R(key, "find_flares", file=xrs["file"], min_class=mc,
              swpc_scale=False)
        R("S1_fig_month", "plot_timeseries", file=xrs["file"],
          columns=["xrsa", "xrsb"], log_y=True,
          title="GOES-18 XRS, October 2024",
          out_name="oct_xrs_month.png")
    for kind in ("FLR", "CME", "GST", "IPS", "SEP"):
        R(f"S1_donki_{kind}", "search_donki", start_date="2024-10-01",
          end_date="2024-11-01", kind=kind)
    omni = R("S1_omni", "fetch_omni", resolution="1min",
             variables=["F", "BZ_GSM", "flow_speed", "proton_density",
                        "Pressure", "SYM_H", "AE_INDEX"], **MONTH)
    R("S1_kp", "fetch_gfz_index", start="2024-10-01", end="2024-11-01",
      index="Kp")
    R("S1_dst_kyoto", "fetch_kyoto_dst", year=2024, month=10)
    if omni.get("file"):
        R("S1_storm_month", "storm_metrics", file=omni["file"],
          dst_column="SYM_H")
        R("S1_fig_symh", "plot_timeseries", file=omni["file"],
          columns=["SYM_H"], title="SYM-H, October 2024",
          out_name="oct_symh_month.png")
        # Daily minima locate every disturbed interval, not just the deepest.
        R("S1_daily_symh", "resample_series", file=omni["file"],
          cadence="1D", method="min", out_name="oct_symh_daily_min.csv")

    # ---------------- S2: the source regions ------------------------------
    print("S2 source regions")
    for day in ("2024-10-01", "2024-10-03", "2024-10-07", "2024-10-09",
                "2024-10-24", "2024-10-26", "2024-10-31"):
        R(f"S2_flr_{day}", "search_donki", start_date=day, end_date=day,
          kind="FLR")
    # AR 13848 at the time of the storm-driving X1.8 (N13W08, near centre).
    aia = R("S2_aia_193", "fetch_aia_synoptic", date="2024-10-09T01:56:00",
            wavelength_angstrom=193)
    if aia.get("files"):
        R("S2_fig_aia193", "plot_solar_map", fits_file=aia["files"][0],
          out_name="oct_aia_193.png")
    for wave in (94, 304):
        a = R(f"S2_aia_{wave}", "fetch_aia_synoptic",
              date="2024-10-09T01:56:00", wavelength_angstrom=wave)
        if a.get("files"):
            R(f"S2_fig_aia{wave}", "plot_solar_map", fits_file=a["files"][0],
              out_name=f"oct_aia_{wave}.png")
    hmi = R("S2_hmi", "fetch_vso", start="2024-10-09T01:50:00",
            end="2024-10-09T02:00:00", instrument="HMI",
            physobs="LOS_magnetic_field", max_files=1)
    if hmi.get("files"):
        R("S2_map", "load_solar_map", fits_file=hmi["files"][0])
        # AR 13848 at N13W08; a mirrored box in the south is the control.
        R("S2_metrics", "magnetogram_metrics", fits_file=hmi["files"][0],
          lon_deg=8.0, lat_deg=13.0, half_deg=12.0,
          out_name="oct_hmi_metrics.png")
        R("S2_quiet", "magnetogram_metrics", fits_file=hmi["files"][0],
          lon_deg=8.0, lat_deg=-13.0, half_deg=12.0)
        R("S2_fig_hmi", "plot_solar_map", fits_file=hmi["files"][0],
          out_name="oct_hmi_full.png")

    # ---------------- S3: coronagraph, CME kinematics ---------------------
    print("S3 coronagraph")
    # Windows open at each flare peak: C2 spans only 2.4-5.8 Rsun, so a late
    # window catches a front already leaving the field.
    for tag, t0, t1 in (("x18", "2024-10-09T02:00:00", "2024-10-09T07:00:00"),
                        ("x90", "2024-10-03T12:20:00", "2024-10-03T17:00:00")):
        lz = R(f"S3_lasco_{tag}", "fetch_vso", start=t0, end=t1,
               instrument="LASCO", detector="C2", max_files=16)
        # Both of these are fast halos that cross C2 (2.4-5.8 Rsun) in one
        # or two frames, so C2 alone cannot give a height-time fit: its
        # track saturates at the outer edge. C3 spans 3.9-29 Rsun.
        c3 = R(f"S3_c3_{tag}", "fetch_vso", start=t0,
               end=t1.replace("T07:", "T10:").replace("T17:", "T20:"),
               instrument="LASCO", detector="C3", max_files=16)
        if c3.get("files"):
            R(f"S3_fig_c3_{tag}", "plot_coronagraph_sequence",
              files=c3["files"], n_panels=6,
              title=f"SOHO/LASCO C3 running difference — {tag.upper()}",
              out_name=f"oct_lasco_c3_{tag}.png")
            t3 = R(f"S3_track_c3_{tag}", "track_cme_front", files=c3["files"])
            if t3.get("status") == "ok" and len(t3.get("times", [])) >= 3:
                R(f"S3_fit_c3_{tag}", "cme_height_time", times=t3["times"],
                  heights_rsun=t3["heights_rsun"])
        if lz.get("files"):
            R(f"S3_fig_{tag}", "plot_coronagraph_sequence", files=lz["files"],
              n_panels=6,
              title=f"SOHO/LASCO C2 running difference — {tag.upper()}",
              out_name=f"oct_lasco_{tag}.png")
            trk = R(f"S3_track_{tag}", "track_cme_front", files=lz["files"])
            if trk.get("status") == "ok" and len(trk.get("times", [])) >= 3:
                R(f"S3_fit_{tag}", "cme_height_time", times=trk["times"],
                  heights_rsun=trk["heights_rsun"])
    R("S3_donki_cme", "search_donki", start_date="2024-10-08",
      end_date="2024-10-10", kind="CMEAnalysis")

    # ---------------- S4: the SEP event -----------------------------------
    print("S4 SEP event")
    pro = R("S4_protons", "fetch_goes_protons", start="2024-10-08T00:00:00Z",
            end="2024-10-14T00:00:00Z", resolution="5min")
    if pro.get("file"):
        cols = pro.get("columns", [])
        c10 = next((c for c in cols if "10" in c and "gt" in c.lower()), None)
        c30 = next((c for c in cols if "30" in c and "gt" in c.lower()), None)
        if c10:
            R("S4_sep", "characterize_sep", file=pro["file"],
              flux_10mev_column=c10, flux_30mev_column=c30,
              flare_peak_time="2024-10-09T01:56:00", flare_class="X1.8",
              flare_lon_deg=8.0, out_name="oct_sep.png")
    R("S4_donki_sep", "search_donki", start_date="2024-10-08",
      end_date="2024-10-12", kind="SEP")

    # ---------------- S5: in-situ, every route ----------------------------
    print("S5 in-situ")
    R("S5_omni_sw", "fetch_omni", resolution="1min",
      variables=["F", "BX_GSE", "BY_GSM", "BZ_GSM", "flow_speed",
                 "proton_density", "T", "Pressure", "SYM_H", "AE_INDEX"], **SW)
    # ACE SWEPAM Level 2 (both AC_H2_SWE hourly and AC_H0_SWE 64-s) stops
    # at 2024-07-09, so the route the May analysis used does NOT cover
    # October. The refusal is kept in the record; Wind SWE replaces it.
    R("S5_ace_swe", "fetch_cdaweb_data", dataset="AC_H2_SWE",
      variables=["Vp", "Np", "Tpr"], **SW)
    R("S5_wind_swe", "fetch_cdaweb_data", dataset="WI_H1_SWE",
      variables=["Proton_V_nonlin", "Proton_Np_nonlin", "Proton_W_nonlin"],
      **SW)
    R("S5_ace_mfi", "fetch_cdaweb_data", dataset="AC_H1_MFI",
      variables=["Magnitude", "BGSEc", "BGSM"], **SW)
    R("S5_wind_mfi", "fetch_cdaweb_data", dataset="WI_H0_MFI",
      variables=["BGSM", "BGSE", "BF1"], **SW)
    R("S5_dscovrl2_fc", "fetch_dscovr_l2", product="faraday_cup", **SW)
    R("S5_dscovrl2_mag", "fetch_dscovr_l2", product="magnetometer", **SW)
    CROSS = [
        ("omni_1min", "S5_omni_sw", "flow_speed", "max", "v"),
        ("wind", "S5_wind_swe", "Proton_V_nonlin", "max", "v"),
        ("dscovr_l2", "S5_dscovrl2_fc", "proton_speed", "max", "v"),
        ("omni_1min", "S5_omni_sw", "proton_density", "max", "n"),
        ("wind", "S5_wind_swe", "Proton_Np_nonlin", "max", "n"),
        ("dscovr_l2", "S5_dscovrl2_fc", "proton_density", "max", "n"),
        ("omni_1min", "S5_omni_sw", "F", "max", "b"),
        ("ace", "S5_ace_mfi", "Magnitude", "max", "b"),
        ("wind", "S5_wind_mfi", "BF1", "max", "b"),
        ("dscovr_l2", "S5_dscovrl2_mag", "bt", "max", "b"),
        ("omni_1min", "S5_omni_sw", "BZ_GSM", "min", "bz"),
        ("ace", "S5_ace_mfi", "BGSM_2", "min", "bz"),
        ("wind", "S5_wind_mfi", "BGSM_2", "min", "bz"),
        ("dscovr_l2", "S5_dscovrl2_mag", "bz_gsm", "min", "bz"),
    ]
    for route, src, col, mode, quant in CROSS:
        f = st.get(src, {})
        if isinstance(f, dict) and f.get("file"):
            R(f"S5x_{quant}_{route}", "find_extrema", file=f["file"],
              column=col, mode=mode)

    # ---------------- S6: geomagnetic response ----------------------------
    print("S6 geomagnetic response")
    sw = st.get("S5_omni_sw", {})
    if sw.get("file"):
        R("S6_storm", "storm_metrics", file=sw["file"], dst_column="SYM_H")
        for col, mode, key in (("SYM_H", "min", "symh"),
                               ("flow_speed", "max", "vmax"),
                               ("BZ_GSM", "min", "bzmin"),
                               ("F", "max", "bmax"),
                               ("proton_density", "max", "nmax"),
                               ("Pressure", "max", "pmax"),
                               ("AE_INDEX", "max", "aemax")):
            R(f"S6_ext_{key}", "find_extrema", file=sw["file"], column=col,
              mode=mode)
        R("S6_icme", "detect_icme", file=sw["file"],
          speed_column="flow_speed", temperature_column="T",
          bz_column="BZ_GSM", by_column="BY_GSM",
          density_column="proton_density", out_name="oct_icme.png")
        R("S6_fig_stack", "plot_stack", files_columns=[
            {"file": sw["file"], "column": "F", "label": "|B| (nT)"},
            {"file": sw["file"], "column": "BZ_GSM", "label": "Bz GSM (nT)"},
            {"file": sw["file"], "column": "flow_speed", "label": "V (km s$^{-1}$)"},
            {"file": sw["file"], "column": "proton_density", "label": "n (cm$^{-3}$)", "logy": True},
            {"file": sw["file"], "column": "Pressure", "label": "P$_{dyn}$ (nPa)"},
            {"file": sw["file"], "column": "SYM_H", "label": "SYM-H (nT)"}],
          title="L1 solar wind and geomagnetic response, October 2024",
          event_times=["2024-10-10T14:46:00", "2024-10-10T23:14:00"],
          out_name="oct_insitu_stack.png")
        R("S6_dstmodel_src", "resample_series", file=sw["file"], cadence="1h",
          out_name="oct_omni_1h.csv")
        src = st.get("S6_dstmodel_src", {})
        if src.get("file"):
            R("S6_model_dst", "model_dst", file=src["file"],
              v_column="flow_speed", bz_column="BZ_GSM",
              density_column="proton_density", dst_column="SYM_H",
              out_name="oct_model_dst.csv")

    # ---------------- S7: arrival and configuration -----------------------
    print("S7 arrival and configuration")
    R("S7_config", "plot_heliospheric_config", date="2024-10-09 02:00:00",
      bodies=["Earth", "STEREO-A", "Solar Orbiter", "PSP", "BepiColombo"],
      solar_wind_kms=400.0, out_name="oct_config.png")
    R("S7_delay", "propagation_delay", solar_wind_speed_kms=800.0)
    R("S7_donki_ips", "search_donki", start_date="2024-10-08",
      end_date="2024-10-12", kind="IPS")

    # ---------------- S8: literature --------------------------------------
    print("S8 literature")
    for key, q in (
        ("S8_lit_storm",
         'abs:"October 2024" abs:(superstorm OR "geomagnetic storm") year:2024-2026'),
        ("S8_lit_ar13842", 'abs:"AR 13842" OR abs:"NOAA 13842" year:2024-2026'),
        ("S8_lit_sep", 'abs:"October 2024" abs:"solar energetic particle" year:2024-2026'),
    ):
        R(key, "search_ads", query=q, max_results=10)
    return st


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--fresh", action="append", default=[])
    args = ap.parse_args()
    st = load_state()
    st = run(st, only=args.only, fresh=set(args.fresh))
    save_state(st)
    bad = [k for k, v in st.items()
           if isinstance(v, dict) and v.get("status") == "error"]
    figs = 0
    for k, v in st.items():
        if isinstance(v, dict) and isinstance(v.get("file"), str) \
                and v["file"].endswith((".png", ".pdf")):
            try:
                keep(k.lower(), v["file"])
                figs += 1
            except Exception:  # noqa: BLE001
                pass
    print(f"\n{len(st)} steps cached, {figs} figures kept, {len(bad)} failed")
    for k in bad:
        print(f"  FAILED {k}: {str(st[k].get('error'))[:150]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
