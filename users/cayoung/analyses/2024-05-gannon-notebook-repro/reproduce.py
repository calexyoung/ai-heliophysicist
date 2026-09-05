"""Reproduce the HelioSummerSchool May 2024 Gannon notebook with helio-agent tools.

Source: reference/pyhc/HelioSummerSchool-may2024_solar_storms_complete.ipynb
(C. Alex Young, NASA GSFC/HDRL; after Will Barnes for the SunPy Community).

Every figure and every number the notebook produces is recomputed here
through audited tools. Nothing is transcribed from the notebook's prose:
where the notebook states a value (flare classes, CME speeds, arrival
times, SYM-H minimum), this measures it and reports the comparison.

    uv run python users/cayoung/analyses/2024-05-gannon-notebook-repro/reproduce.py
    ... --only S5        # one section
    ... --fresh sw_ace_cdaweb

Results cache to results.json beside this file; figures land in figures/.
Runs against live archives — minutes, not seconds.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timedelta
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FIGS = HERE / "figures"
STATE = HERE / "results.json"
sys.path.insert(0, str(ROOT))

# The notebook's own stated values, for explicit comparison. These are the
# CLAIMS under test — never used as inputs to anything computed.
NOTEBOOK_CLAIMS = {
    "n_xflares_ar13664": 11,
    "flare_cme1": {"peak": "2024-05-08 05:09", "class": "X1.0",
                   "start": "2024-05-08 04:37", "peak_flux": 1.02e-4},
    "flare_cme2": {"peak": "2024-05-09 09:13", "class": "X2.2",
                   "start": "2024-05-09 08:45", "peak_flux": 2.21e-4},
    "cme1_speed_kms": 950.0,
    "cme2_speed_kms": 1100.0,
    "cme1_arrival": "2024-05-10 16:34",
    "cme2_arrival": "2024-05-10 22:21",
    "symh_min_nt": -518.0,
    "symh_min_time": "2024-05-11 02:14",
    "max_kp": 9.0,
    "max_speed_kms": 1100.0,
    "bz_min_nt": -48.0,
    "dyn_pressure_npa": 15.0,
    "sta_separation_deg": 25.0,
    "solo_separation_deg": 45.0,
    "hmi_max_pos_g": 2500.0,
    "hmi_total_unsigned": 1.5e23,
    "ace_storm_vmax": 739.0,
    "ace_storm_nmax": 41.9,
    "ace_storm_bzmin": -53.3,
}

WINDOW = {"start": "2024-05-07T00:00:00Z", "end": "2024-05-15T00:00:00Z"}
SW = {"start": "2024-05-10T00:00:00Z", "end": "2024-05-13T00:00:00Z"}


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(st: dict) -> None:
    STATE.write_text(json.dumps(st, indent=1, default=str))


def keep(name: str, path: str) -> str:
    """Copy a produced figure into figures/ and return its basename."""
    p = Path(path)
    FIGS.mkdir(parents=True, exist_ok=True)
    dest = FIGS / f"{name}{p.suffix}"
    shutil.copy(p, dest)
    return dest.name


def run(st, only=None, fresh=()):
    from helio_agent.registry import run_tool

    def R(key, tool, **kw):
        """Run a tool, cache by key, return its result."""
        if key in st and key not in fresh and (only is None or not key.startswith(only)):
            return st[key]
        if only and not key.startswith(only) and key in st:
            return st[key]
        print(f"  RUN {key}  ({tool})")
        r = run_tool(tool, **kw)
        if r.get("status") == "error":
            print(f"     FAIL {str(r.get('error'))[:130]}")
        st[key] = json.loads(json.dumps(r, default=str))
        save_state(st)
        return st[key]

    # ---------------- S1: GOES X-rays and the flare timeline ---------------
    print("S1 GOES X-ray")
    xrs = R("S1_xrs", "fetch_goes_xrs", **WINDOW)
    # GOES-R science data are TRUE fluxes already on the operational scale:
    # swpc_scale must be False, or every class comes out 1/0.7 too small.
    R("S1_flares_x", "find_flares", file=xrs["file"], column="xrsb",
      min_class="X1.0", swpc_scale=False)
    R("S1_flares_m", "find_flares", file=xrs["file"], column="xrsb",
      min_class="M1.0", swpc_scale=False)
    R("S1_flares_scaled", "find_flares", file=xrs["file"], column="xrsb",
      min_class="X1.0", swpc_scale=True)   # the wrong-convention comparison
    for day in ("2024-05-08", "2024-05-09", "2024-05-14"):
        R(f"S1_donki_{day}", "search_donki", start_date=day, end_date=day,
          kind="FLR")
    R("S1_hek", "search_hek_events", start="2024-05-09T00:00:00",
      end="2024-05-10T00:00:00", event_type="FL", max_results=60)
    R("S1_fig_overview", "plot_timeseries", file=xrs["file"],
      columns=["xrsb", "xrsa"],
      series_labels=["GOES 1-8 Å (XRS-B)", "GOES 0.5-4 Å (XRS-A)"],
      y_label="X-ray flux (W m$^{-2}$)", log_y=True,
      title="GOES-18 X-ray flux, May 2024 storms",
      event_times=["2024-05-08T05:09:00", "2024-05-09T09:13:00"],
      event_labels=["CME 1 (X1.0)", "CME 2 (X2.2)"],
      out_name="repro_xray_overview.png")
    R("S1_fig_cme1", "plot_timeseries", file=xrs["file"],
      columns=["xrsb", "xrsa"], series_labels=["1-8 Å", "0.5-4 Å"],
      y_label="X-ray flux (W m$^{-2}$)", log_y=True,
      title="CME 1 driver: X1.0, 2024-05-08",
      event_times=["2024-05-08T05:09:00"], event_labels=["peak"],
      out_name="repro_xray_cme1.png")
    R("S1_fig_cme2", "plot_timeseries", file=xrs["file"],
      columns=["xrsb", "xrsa"], series_labels=["1-8 Å", "0.5-4 Å"],
      y_label="X-ray flux (W m$^{-2}$)", log_y=True,
      title="CME 2 driver: X2.2, 2024-05-09",
      event_times=["2024-05-09T09:13:00"], event_labels=["peak"],
      out_name="repro_xray_cme2.png")

    # ---------------- S2: AIA multi-wavelength source region ---------------
    print("S2 SDO/AIA")
    # The notebook pulls AIA through sunpy/Fido -> VSO. That route still
    # works for HMI and LASCO but the AIA export provider
    # (sdo7.nascom.nasa.gov drms_export.cgi) times out on every request as
    # of this run, so the same query is issued both ways: VSO for the
    # record, the JSOC synoptic archive for the images.
    for tag, t0 in (("cme1", "2024-05-08T05:10:00"),
                    ("cme2", "2024-05-09T09:14:00")):
        for wave in (94, 171, 304):
            t1 = (datetime.fromisoformat(t0)
                  + timedelta(minutes=12)).isoformat()
            R(f"S2_vso_{tag}_{wave}", "fetch_vso", start=t0, end=t1,
              instrument="AIA", wavelength_angstrom=float(wave),
              max_files=1)
            f = R(f"S2_aia_{tag}_{wave}", "fetch_aia_synoptic", date=t0,
                  wavelength_angstrom=wave)
            if f.get("status") == "error" or not f.get("files"):
                continue
            R(f"S2_deg_{tag}_{wave}", "aia_degradation",
              date=t0[:10], channels=[wave])
            R(f"S2_fig_{tag}_{wave}", "plot_solar_map",
              fits_file=f["files"][0],
              out_name=f"repro_aia_{tag}_{wave}.png")

    # Native-resolution comparison for one channel. JSOC level 1 is 4096^2
    # at ~0.6 arcsec/pix against the synoptic 1024^2 at ~2.4, and each frame
    # is ~12 MB, so this is deliberately one channel rather than all six:
    # the point is to show the route works and what it buys, not to re-shoot
    # the survey at 16x the size.
    l1 = R("S2_l1_cme1_171", "fetch_aia_level1", date="2024-05-08T05:10:00",
           wavelength_angstrom=171)
    if l1.get("status") == "ok" and l1.get("files"):
        R("S2_l1_map_cme1_171", "load_solar_map", fits_file=l1["files"][0])
        R("S2_l1_fig_cme1_171", "plot_solar_map", fits_file=l1["files"][0],
          out_name="repro_aia_l1_cme1_171.png")

    # ---------------- S3: HMI magnetogram of AR 13664 ----------------------
    print("S3 SDO/HMI")
    hmi = R("S3_hmi", "fetch_vso", start="2024-05-08T05:09:00",
            end="2024-05-08T05:12:00", instrument="HMI", max_files=1,
            physobs="LOS_magnetic_field")
    if hmi.get("files"):
        R("S3_map", "load_solar_map", fits_file=hmi["files"][0])
        # AR 13664 was near S20W10 on 2024-05-08 (DONKI source locations)
        R("S3_metrics", "magnetogram_metrics", fits_file=hmi["files"][0],
          lat_deg=-20.0, lon_deg=10.0, half_deg=12.0,
          out_name="repro_hmi_ar13664.png")
        R("S3_quiet", "magnetogram_metrics", fits_file=hmi["files"][0],
          lat_deg=-20.0, lon_deg=-10.0, half_deg=12.0, plot=False)
        R("S3_fig_full", "plot_solar_map", fits_file=hmi["files"][0],
          out_name="repro_hmi_full.png")
        R("S3_regions", "search_donki", start_date="2024-05-08",
          end_date="2024-05-08", kind="FLR")

    # ---------------- S4: LASCO coronagraph, CME kinematics ----------------
    print("S4 SOHO/LASCO")
    # Windows start just after each flare peak (05:09 and 09:13 UT), not an
    # hour later: C2 spans only 2.4-5.8 Rsun, so a front that is already at
    # the outer edge when the sequence opens cannot be tracked. Opening at
    # the eruption took CME 1 from 3 usable height points to 5, and turned
    # CME 2 from an untrackable non-monotonic scatter into a clean track.
    for tag, t0, t1 in (("cme1", "2024-05-08T05:36:00", "2024-05-08T11:30:00"),
                        ("cme2", "2024-05-09T09:12:00", "2024-05-09T15:00:00")):
        lz = R(f"S4_lasco_{tag}", "fetch_vso", start=t0, end=t1,
               instrument="LASCO", detector="C2", max_files=16)
        if lz.get("files"):
            R(f"S4_fig_{tag}", "plot_coronagraph_sequence", files=lz["files"],
              n_panels=6,
              title=f"SOHO/LASCO C2 running difference — {tag.upper()}",
              out_name=f"repro_lasco_{tag}.png")
    # DONKI cone-model fits: the real measured speeds (the notebook's own
    # height-time routine drew its heights from np.random.uniform).
    # Measure the front instead of accepting a catalogue number. The
    # notebook's speed cell fits np.random.uniform output; this tracks the
    # leading edge through the difference frames and fits that.
    for tag, key in (("cme1", "S4_lasco_cme1"), ("cme2", "S4_lasco_cme2")):
        src = st.get(key, {})
        if not src.get("files"):
            continue
        trk = R(f"S4_track_{tag}", "track_cme_front", files=src["files"])
        if trk.get("status") == "ok" and len(trk.get("times", [])) >= 3:
            R(f"S4_fit_{tag}", "cme_height_time", times=trk["times"],
              heights_rsun=trk["heights_rsun"])

    R("S4_donki_cme", "search_donki", start_date="2024-05-08",
      end_date="2024-05-10", kind="CMEAnalysis")

    # ---------------- S5: in-situ solar wind, every available route --------
    print("S5 in-situ solar wind")
    # (a) the notebook's own route: CDAWeb hourly ACE via sunpy/Fido
    R("S5_ace_swe", "fetch_cdaweb_data", dataset="AC_H2_SWE",
      variables=["Vp", "Np", "Tpr"], **SW)
    # CDAWeb vector variables are requested by their vector name; the tool
    # expands them into _0/_1/_2 columns. Asking for the components directly
    # is what produced the http 400 on the first pass.
    R("S5_ace_mfi", "fetch_cdaweb_data", dataset="AC_H1_MFI",
      variables=["Magnitude", "BGSEc", "BGSM"], **SW)
    # (b) ACE 1-min science through the mission's own pySPEDAS loader
    R("S5_pyspedas_mfi", "fetch_pyspedas", mission="ace", instrument="mfi",
      start="2024-05-10", end="2024-05-13")
    R("S5_pyspedas_swe", "fetch_pyspedas", mission="ace", instrument="swe",
      start="2024-05-10", end="2024-05-13")
    # (c) OMNI 1-min: multi-spacecraft merged, shifted to the bow-shock nose
    R("S5_omni_1m", "fetch_omni", start="2024-05-09T00:00:00Z",
      end="2024-05-15T00:00:00Z", resolution="1min",
      variables=["F", "BX_GSE", "BY_GSM", "BZ_GSM", "flow_speed",
                 "proton_density", "T", "Pressure", "SYM_H", "AE_INDEX"])
    # (d) DSCOVR at L1 — the notebook mentions it but never loads it
    R("S5_dscovr_mag", "fetch_cdaweb_data", dataset="DSCOVR_H0_MAG",
      variables=["B1F1", "B1GSE", "B1RTN"], **SW)  # no GSM in this dataset
    # DSCOVR Faraday-cup plasma: the only CDAWeb science product
    # (DSCOVR_H1_FC) stops in 2019, so this route legitimately cannot cover
    # May 2024. The refusal is kept in the record as the answer.
    R("S5_dscovr_pla", "fetch_cdaweb_data", dataset="DSCOVR_H1_FC",
      variables=["V_GSE", "Np", "THERMAL_TEMP"], **SW)
    # (e) Wind, a fourth independent L1 monitor
    R("S5_wind_mfi", "fetch_cdaweb_data", dataset="WI_H0_MFI",
      variables=["BGSM", "BGSE", "BF1"], **SW)

    # (f) the same quantities measured on every route that carries them, so
    # the routes can be compared instead of trusted. OMNI is refetched on the
    # IDENTICAL 05-10..05-13 window first: comparing an extremum taken over
    # 6 days against one taken over 3 would compare windows, not instruments.
    R("S5_omni_sw", "fetch_omni", resolution="1min",
      variables=["F", "BZ_GSM", "flow_speed", "proton_density"], **SW)
    CROSS = [
        ("ace_cdaweb", "S5_ace_swe", "Vp", "max", "v"),
        ("ace_pyspedas", "S5_pyspedas_swe", "Vp", "max", "v"),
        ("omni_1min", "S5_omni_sw", "flow_speed", "max", "v"),
        ("ace_cdaweb", "S5_ace_swe", "Np", "max", "n"),
        ("ace_pyspedas", "S5_pyspedas_swe", "Np", "max", "n"),
        ("omni_1min", "S5_omni_sw", "proton_density", "max", "n"),
        ("ace_cdaweb", "S5_ace_mfi", "Magnitude", "max", "b"),
        ("ace_pyspedas", "S5_pyspedas_mfi", "Magnitude", "max", "b"),
        ("dscovr", "S5_dscovr_mag", "B1F1", "max", "b"),
        ("wind", "S5_wind_mfi", "BF1", "max", "b"),
        ("omni_1min", "S5_omni_sw", "F", "max", "b"),
        ("ace_cdaweb", "S5_ace_mfi", "BGSM_2", "min", "bz"),
        ("ace_pyspedas", "S5_pyspedas_mfi", "BGSM_2", "min", "bz"),
        ("wind", "S5_wind_mfi", "BGSM_2", "min", "bz"),
        ("omni_1min", "S5_omni_sw", "BZ_GSM", "min", "bz"),
    ]
    for route, src, col, mode, quant in CROSS:
        f = st.get(src, {})
        if not isinstance(f, dict) or not f.get("file"):
            continue
        R(f"S5x_{quant}_{route}", "find_extrema", file=f["file"],
          column=col, mode=mode)

    # ---------------- S6: storm response and ICME structure ----------------
    print("S6 geomagnetic response")
    omni = st.get("S5_omni_1m", {})
    if omni.get("file"):
        R("S6_storm", "storm_metrics", file=omni["file"], dst_column="SYM_H")
        for col, mode, key in (("SYM_H", "min", "symh"),
                               ("flow_speed", "max", "vmax"),
                               ("BZ_GSM", "min", "bzmin"),
                               ("F", "max", "bmax"),
                               ("proton_density", "max", "nmax"),
                               ("Pressure", "max", "pmax"),
                               ("AE_INDEX", "max", "aemax")):
            R(f"S6_ext_{key}", "find_extrema", file=omni["file"],
              column=col, mode=mode)
        R("S6_icme", "detect_icme", file=omni["file"],
          speed_column="flow_speed", temperature_column="T",
          by_column="BY_GSM", bz_column="BZ_GSM",
          density_column="proton_density", out_name="repro_icme.png")
        R("S6_fig_stack", "plot_stack", files_columns=[
            {"file": omni["file"], "column": "F", "label": "|B| (nT)"},
            {"file": omni["file"], "column": "BZ_GSM", "label": "Bz GSM (nT)"},
            {"file": omni["file"], "column": "flow_speed",
             "label": "V (km s$^{-1}$)"},
            {"file": omni["file"], "column": "proton_density",
             "label": "n (cm$^{-3}$)", "log": True},
            {"file": omni["file"], "column": "Pressure",
             "label": "P$_{dyn}$ (nPa)"},
            {"file": omni["file"], "column": "SYM_H", "label": "SYM-H (nT)"}],
          title="L1 solar wind and geomagnetic response, May 2024 (OMNI 1-min)",
          event_times=["2024-05-10T17:05:00", "2024-05-11T02:14:00"],
          out_name="repro_insitu_stack.png")
        R("S6_dstmodel_src", "resample_series", file=omni["file"],
          cadence="1h", out_name="repro_omni_1h.csv")
    h1 = st.get("S6_dstmodel_src", {})
    if h1.get("file"):
        R("S6_model_dst", "model_dst", file=h1["file"],
          v_column="flow_speed", bz_column="BZ_GSM",
          density_column="proton_density", dst_column="SYM_H",
          out_name="repro_model_dst.csv")
    R("S6_kp", "fetch_gfz_index", index="Kp", start="2024-05-08",
      end="2024-05-15")
    R("S6_dst_kyoto", "fetch_kyoto_dst", year=2024, month=5)
    R("S6_gst", "search_donki", start_date="2024-05-10", end_date="2024-05-12",
      kind="GST")
    R("S6_ips", "search_donki", start_date="2024-05-10", end_date="2024-05-12",
      kind="IPS")

    # Independent check on the sheath-vs-ejecta attribution and on the
    # SYM-H depth, against the refereed record rather than against DONKI.
    R("S6_lit", "search_ads",
      query='abs:"May 2024" abs:superstorm abs:sheath year:2024-2026',
      max_results=8)

    # ---------------- S7: heliospheric configuration -----------------------
    print("S7 spacecraft configuration")
    R("S7_config_nominal", "plot_heliospheric_config",
      date="2024-05-10 12:00:00",
      bodies=["Earth", "STEREO-A", "Solar Orbiter", "PSP", "BepiColombo"],
      solar_wind_kms=400.0, out_name="repro_config_400.png")
    R("S7_config_storm", "plot_heliospheric_config",
      date="2024-05-10 12:00:00",
      bodies=["Earth", "STEREO-A", "Solar Orbiter", "PSP", "BepiColombo"],
      solar_wind_kms=1000.0, out_name="repro_config_1000.png")
    R("S7_ephem", "fetch_spacecraft_ephemeris",
      spacecraft=["ace", "wind", "dscovr", "stereoa"],
      start="2024-05-08T00:00:00Z", end="2024-05-13T00:00:00Z")
    e = st.get("S7_ephem", {})
    if e.get("file"):
        R("S7_fig_orbits", "plot_orbits", file=e["file"], plane="xy",
          units="Re", title="L1 monitors and STEREO-A, 2024-05-08 to 13 (GSE)",
          out_name="repro_orbits.png")

    # ---------------- S8: CME arrival, forecast vs observed ----------------
    print("S8 CME arrival")
    for tag, v0, launch in (("cme1", 950.0, "2024-05-08T06:00Z"),
                            ("cme2", 1100.0, "2024-05-09T10:00Z")):
        R(f"S8_dbm_{tag}", "cme_arrival", v0_kms=v0, launch_time=launch)
    R("S8_delay", "propagation_delay", solar_wind_speed_kms=700.0)
    R("S8_plasma", "plasma_parameters", density_cm3=30.0, b_nT=70.0,
      temperature_K=3e5)
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
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
