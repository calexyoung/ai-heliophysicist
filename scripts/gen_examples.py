"""Generate docs/EXAMPLES.md — one worked, audit-logged example per tool.

Unlike gen_docs.py (which rewrites reference docs from the registry), this
script RUNS every example against live archives, so it is a manual build,
not a CI step:

    uv run python scripts/gen_examples.py            # run everything, write the doc
    uv run python scripts/gen_examples.py --only measure
    uv run python scripts/gen_examples.py --fresh radio_bursts

Results are cached per-example in workspace scratch (delete the cache file
or use --fresh to re-run one). Figures and small artifacts produced by the
examples are copied into docs/examples/ so the document is self-contained
in the repository; large solar images are downscaled to keep the repo light.
Every example records the audit id of the real call that produced its
numbers — nothing in the document is typed in by hand.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
EXDIR = DOCS / "examples"
STATE = ROOT / "workspace" / "logs" / "examples_state.json"
OUT = DOCS / "EXAMPLES.md"
MAX_PNG_WIDTH = 1400

sys.path.insert(0, str(ROOT))


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def _save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1, default=str))


def _dig(obj, path):
    """'sep.s_scale' / 'papers[0].title' style lookups, forgiving."""
    cur = obj
    for part in path.replace("]", "").split("."):
        if "[" in part:
            key, idx = part.split("[")
            cur = cur.get(key) if isinstance(cur, dict) else None
            if isinstance(cur, (list, tuple)) and len(cur) > int(idx):
                cur = cur[int(idx)]
            else:
                return None
        else:
            cur = cur.get(part) if isinstance(cur, dict) else None
        if cur is None:
            return None
    return cur


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    s = str(v)
    return s if len(s) <= 110 else s[:107] + "..."


def _resolve(kwargs, results):
    out = {}
    for k, v in kwargs.items():
        if isinstance(v, tuple) and len(v) == 3 and v[0] == "ref":
            _, ex_name, key = v
            out[k] = _dig(results[ex_name]["result"], key)
        elif isinstance(v, list):
            out[k] = [
                _dig(results[x[1]]["result"], x[2])
                if isinstance(x, tuple) and len(x) == 3 and x[0] == "ref" else x
                for x in v
            ]
        else:
            out[k] = v
    return out


def _copy_artifact(src: str, stem: str) -> str | None:
    """Copy a produced file into docs/examples/, downscaling large PNGs."""
    p = Path(src)
    if not p.is_file():
        return None
    dest = EXDIR / f"{stem}{p.suffix.lower()}"
    EXDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(p, dest)
    if dest.suffix == ".png":
        try:
            out = subprocess.run(["sips", "-g", "pixelWidth", str(dest)],
                                 capture_output=True, text=True, check=True)
            width = int(out.stdout.rsplit(":", 1)[-1])
            if width > MAX_PNG_WIDTH:
                subprocess.run(["sips", "--resampleWidth", str(MAX_PNG_WIDTH),
                                str(dest)], capture_output=True, check=True)
        except Exception:  # noqa: BLE001 - sips is a macOS nicety, not a need
            pass
    return dest.name


def run_examples(examples, only=None, fresh=()):
    from helio_agent.registry import run_tool

    state = _load_state()
    results = {}
    failures = []
    for ex in examples:
        name = ex["name"]
        if name in state and name not in fresh and not ex.get("always"):
            entry = state[name]
            # heal a cached entry whose figure was never copied (or whose
            # fig key was corrected after the run)
            if ex.get("fig") and not entry.get("figure"):
                src = _dig(entry.get("result", {}), ex["fig"])
                if src:
                    copied = _copy_artifact(str(src), ex["save_as"])
                    if copied:
                        entry["figure"] = copied
                        state[name] = entry
                        _save_state(state)
            results[name] = entry
            continue
        if only and ex["family"] != only and name not in fresh:
            # not cached and not selected: leave a hole; a later ref into it
            # fails loudly, which is the correct behaviour for a partial run
            continue
        kwargs = (ex["build"](results) if ex.get("build")
                  else _resolve(ex["kwargs"], results))
        print(f"RUN  {ex['family']:10s} {name}")
        try:
            res = run_tool(ex["tool"], **kwargs)
        except Exception as exc:  # noqa: BLE001
            res = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        entry = {"result": json.loads(json.dumps(res, default=str)),
                 "kwargs": json.loads(json.dumps(kwargs, default=str))}
        if res.get("status") == "error":
            failures.append((name, res.get("error", "")[:160]))
            print(f"   FAIL {res.get('error', '')[:120]}")
        elif ex.get("fig"):
            src = _dig(res, ex["fig"])
            if src:
                copied = _copy_artifact(str(src), ex["save_as"])
                entry["figure"] = copied
                print(f"   fig -> {copied}")
        results[name] = entry
        state[name] = entry
        _save_state(state)
    return results, failures


def E(family, tool, kwargs=None, note="", show=(), fig=None, save_as=None,
      name=None, hidden=False, build=None, skills=()):
    return {"family": family, "tool": tool, "name": name or tool,
            "kwargs": kwargs or {}, "note": note, "show": list(show),
            "fig": fig, "save_as": save_as, "hidden": hidden, "build": build,
            "skills": list(skills)}


def R(name, key):
    return ("ref", name, key)


def _stack_kwargs(results):
    f = results["_omni_gannon1m"]["result"]["file"]
    return {"files_columns": [
        {"file": f, "column": "F", "label": "|B| (nT)"},
        {"file": f, "column": "BZ_GSM", "label": "Bz GSM (nT)"},
        {"file": f, "column": "flow_speed", "label": "V (km s$^{-1}$)"},
        {"file": f, "column": "proton_density", "label": "n (cm$^{-3}$)",
         "log": True},
        {"file": f, "column": "SYM_H", "label": "SYM-H (nT)"}],
        "title": "Gannon superstorm, 2024 May — OMNI 1-min",
        "event_times": ["2024-05-10T17:05:00", "2024-05-11T02:14:00"],
        "out_name": "examples_stack.png"}


def _pdf_sections(results):
    stack = str(EXDIR / "gannon_stack.png")
    sep = str(EXDIR / "sep_20170910.png")
    return {"title": "Example: two storms, one page", "sections": [
        {"heading": "May 2024 solar wind",
         "text": "OMNI 1-min through the Gannon storm: field, Bz, speed, "
                 "density and SYM-H, shock and minimum marked.",
         "image": stack},
        {"heading": "September 2017 radiation storm",
         "text": "GOES >10 and >30 MeV integral proton flux around the "
                 "X8.2 event, S-scale threshold and event span shaded.",
         "image": sep},
    ], "out_name": "examples_report.pdf"}


def _manifest_kwargs(results):
    d = results["_repro_delay"]["result"]
    v = results["verify_claim_repro"]["result"]
    value = d["delay_minutes"]
    return {"paper": {"title": "Worked example (deterministic)",
                      "doi": "10.0000/example"},
            "claims": [{
                "id": "c1",
                "statement": "The ballistic L1 propagation delay at 500 km/s "
                             "is reproduced.",
                "capability": "ready",
                "claimed": {"value": value, "units": "minutes"},
                "data": {"dataset": "constant-speed example",
                         "instrument": "none",
                         "processing_level": "derived",
                         "cadence": "not applicable", "revision": "1",
                         "time_window": "instantaneous"},
                "recipe": [{"tool": "propagation_delay",
                            "args": {"solar_wind_speed_kms": 500.0},
                            "audit_id": d["audit_id"]}],
                "computed": {"value": value, "units": "minutes",
                             "tolerance_percent": 1.0, "verdict": "match",
                             "verification_audit_id": v["audit_id"]},
                "caveats": ["Deterministic input, chosen so the manifest "
                            "chain can be demonstrated without archive "
                            "access."],
            }],
            "out_name": "examples_manifest.json"}


GANNON_EPOCHS = ["2026-05-10T19:21:00Z"]  # placeholder, replaced below

EXAMPLES = [
    # ------------------------------------------------------------- discover
    E("discover", "get_noaa_realtime", {"product": "kp"},
      "Current planetary Kp from the SWPC real-time feed. Operational data — quote it as such.",
      show=["n_feeds"], skills=["datasources/noaa_swpc.md"]),
    E("discover", "get_solar_regions", {},
      "Today's edited sunspot-region summary. `location` is valid at 2400 UT of "
      "`observed_date` — match images against `coordinates_epoch`, never the date stamp.",
      show=["observed_date", "coordinates_epoch", "n_results"],
      skills=["datasources/noaa_swpc.md"]),
    E("discover", "get_sunspot_reports", {},
      "The raw per-observatory reports behind that summary. Observatories disagree on the "
      "McIntosh class for ~65% of region-days; ties are reported, never resolved by fiat.",
      show=["coverage", "n_reports", "note"],
      skills=["datasources/noaa_swpc.md", "methods/flare_analysis.md"]),
    E("discover", "search_cdaweb_datasets", {"keyword": "WAVES radio"},
      "Keyword search over CDAWeb's ~3000 datasets when you know the physics but not the ID.",
      show=["n_results", "datasets[0].Id"], skills=["datasources/cdaweb.md"]),
    E("discover", "list_cdaweb_variables", {"dataset": "OMNI2_H0_MRG1HR"},
      "Variable names and units for a dataset — run before any fetch_cdaweb_data call.",
      show=["n_variables"], skills=["datasources/cdaweb.md", "datasources/omniweb.md"]),
    E("discover", "search_donki", {"start_date": "2017-09-05",
                                   "end_date": "2017-09-08", "kind": "FLR"},
      "DONKI flare records around the 2017-09-06 X9.3 — the standard cross-check for "
      "any flare detection.", show=["n_results"],
      skills=["datasources/donki.md", "methods/flare_analysis.md"]),
    E("discover", "search_hek_events", {"start": "2017-09-06T00:00:00",
                                        "end": "2017-09-07T00:00:00",
                                        "event_type": "FL"},
      "The same day in the Heliophysics Event Knowledgebase; HEK and DONKI are "
      "independent catalogs, which is what makes agreement meaningful.",
      show=["n_results"], skills=["datasources/hek.md"]),
    E("discover", "search_heliodata", {"query": "interplanetary magnetic field ACE"},
      "Freetext search of the HDRL HelioData catalog (>7800 datasets).",
      show=["n_results"], skills=["datasources/heliodata.md"]),
    E("discover", "search_vso", {"start": "2017-09-06T11:00:00",
                                 "end": "2017-09-06T11:20:00",
                                 "instrument": "HMI"},
      "What the VSO holds for a 20-minute HMI window — search before fetch.",
      show=["n_results"], skills=["datasources/vso.md"]),
    E("discover", "list_spacecraft", {},
      "Spacecraft trackable through SSCWeb, with the IDs fetch_spacecraft_ephemeris needs.",
      show=["n_results"], skills=["datasources/sscweb.md"]),
    E("discover", "list_pyspedas_missions", {},
      "Mission projects pySPEDAS can load.", show=["n_missions"],
      skills=["tools/pyspedas_pytplot.md"]),
    E("discover", "list_pyspedas_loaders", {"mission": "ace"},
      "Instrument load routines for one mission.", show=["n_loaders"],
      skills=["tools/pyspedas_pytplot.md"]),
    E("discover", "list_model_outputs", {"model": "swmf"},
      "CCMC model products on ISWA with live coverage — catalog presence is not "
      "currency, so every entry carries a staleness flag read from the server.",
      show=["n_products", "n_live"], skills=["datasources/hapi.md"]),
]

EXAMPLES += [
    # ----------------------------------------------------------- literature
    E("literature", "search_ads",
      {"query": 'title:"McIntosh" AND abs:"flaring rates"', "max_results": 5},
      "ADS search that located the flare-rate tables behind flare_probability.",
      show=["n_results"], skills=["methods/paper_reproduction.md"]),
    E("literature", "search_arxiv",
      {"query": "McIntosh sunspot classification flaring rates", "max_results": 5},
      "The same hunt on arXiv, which is where the open PDF turned out to live.",
      show=["n_results"]),
    E("literature", "fetch_arxiv_pdf", {"arxiv_id": "1607.00903"},
      "Download the paper into the workspace. Its Tables 5/7/9 were then parsed "
      "into flare_probability's rate tables rather than transcribed by hand.",
      show=["file"]),
    E("literature", "get_bibtex", {"bibcodes": ["2016SoPh..291.1711M"]},
      "Citable BibTeX for the same paper, from ADS.", show=["n_entries"]),

    # ------------------------------------------------------------- retrieve
    E("retrieve", "fetch_omni",
      {"start": "2003-10-28T00:00:00Z", "end": "2003-11-02T00:00:00Z"},
      "Hourly OMNI through the Halloween 2003 superstorm — the repo's oldest "
      "validation anchor (Dst -383 nT).",
      show=["n_records", "columns"], skills=["datasources/omniweb.md"]),
    E("retrieve", "fetch_omni",
      {"start": "2024-05-09T00:00:00Z", "end": "2024-05-15T00:00:00Z",
       "resolution": "1min",
       "variables": ["F", "BY_GSM", "BZ_GSM", "flow_speed", "proton_density",
                     "T", "SYM_H", "Pressure"]},
      name="_omni_gannon1m", hidden=True),
    E("retrieve", "fetch_omni",
      {"start": "2015-03-16T00:00:00Z", "end": "2015-03-19T00:00:00Z",
       "resolution": "1min",
       "variables": ["flow_speed", "T", "proton_density", "BY_GSM", "BZ_GSM"]},
      name="_omni_stpatrick1m", hidden=True),
    E("retrieve", "fetch_omni",
      {"start": "2015-03-15T00:00:00Z", "end": "2015-03-20T00:00:00Z",
       "variables": ["V1800", "BZ_GSM1800", "N1800", "DST1800"]},
      name="_omni_stpatrick1h", hidden=True),
    E("retrieve", "fetch_omni",
      {"start": "2017-01-01T00:00:00Z", "end": "2017-12-31T23:59:00Z",
       "variables": ["V1800"]}, name="_omni_2017", hidden=True),
    E("retrieve", "fetch_cdaweb_data",
      {"dataset": "AC_H2_MFI", "variables": ["Magnitude"],
       "start": "2017-09-06T00:00:00Z", "end": "2017-09-08T00:00:00Z"},
      "Any CDAWeb dataset by ID and variable list; here ACE field magnitude, "
      "later cross-checked against the same data through pySPEDAS.",
      show=["n_records", "columns"], skills=["datasources/cdaweb.md"]),
    E("retrieve", "fetch_cdaweb_data",
      {"dataset": "STA_L2_MAGPLASMA_1M", "variables": ["BTOTAL", "Vp", "Np", "R"],
       "start": "2012-07-22T00:00:00Z", "end": "2012-07-27T00:00:00Z"},
      name="_sta_2012", hidden=True),
    E("retrieve", "fetch_cdaweb_data",
      {"dataset": "OMNI2_H0_MRG1HR", "variables": ["DST1800"],
       "start": "1964-01-01T00:00:00Z", "end": "2024-12-31T23:00:00Z"},
      name="_dst_60yr", hidden=True),
    E("retrieve", "fetch_cdaweb_spectrogram",
      {"start": "2017-09-06T08:00:00Z", "end": "2017-09-06T20:00:00Z"},
      "A 2-D dynamic spectrum with its frequency axis kept — WIND/WAVES around "
      "the X9.3. The generic fetch flattens 2-D variables; this one does not.",
      show=["n_records", "n_channels", "channel_units"],
      skills=["methods/radio_burst_analysis.md"]),
    E("retrieve", "fetch_goes_xrs",
      {"start": "2017-09-06T00:00:00Z", "end": "2017-09-07T00:00:00Z"},
      "Science-grade GOES X-ray flux for flare work.",
      show=["n_records", "columns"], skills=["methods/flare_analysis.md"]),
    E("retrieve", "fetch_goes_protons",
      {"start": "2017-09-09T00:00:00Z", "end": "2017-09-16T00:00:00Z",
       "satellite": "goes13"},
      "Integral proton flux around the 2017-09-10 S3 radiation storm. Before "
      "2020-03 these are measured channels; after, the tool reconstructs them "
      "from the SGPS spectrum and says so in `derived`.",
      show=["n_records", "satellite", "derived", "source"],
      skills=["datasources/goes_ncei.md", "methods/sep_analysis.md"]),
    E("retrieve", "fetch_hapi",
      {"server": "https://iswa.ccmc.gsfc.nasa.gov/IswaSystemWebApp/hapi",
       "dataset": "goesp_xray_flux_P1M", "parameters": "Short_Wave,Long_Wave",
       "start": "2026-09-04T06:00:00Z", "end": "2026-09-04T09:00:00Z"},
      "Any HAPI server by URL. `reader` reports whether hapiclient or the "
      "direct-CSV fallback served it (ISWA declares a non-spec `float` type).",
      show=["n_records", "reader"], skills=["datasources/hapi.md"]),
    E("retrieve", "fetch_model_output",
      {"model": "swmf", "product": "dst", "start": "2024-05-09T00:00:00Z",
       "end": "2024-05-15T00:00:00Z", "allow_stale": True},
      "CCMC SWMF real-time Dst for the Gannon storm. The run has stopped, so "
      "`allow_stale` is required — a dead real-time run is archive, not nowcast.",
      show=["run", "n_records", "stale", "is_model_output"],
      skills=["datasources/hapi.md"]),
    E("retrieve", "fetch_helioviewer_image",
      {"date": "2024-05-10T12:00:00Z", "layers": "[SDO,AIA,AIA,304,1,100]"},
      "Context imagery (PNG, display-grade). AR 13664 dominates the southeast "
      "quadrant hours before the first Gannon CME arrival.",
      show=["bytes"], fig="file", save_as="helioviewer_aia304",
      skills=["datasources/helioviewer.md"]),
    E("retrieve", "fetch_vso",
      {"start": "2017-09-06T11:00:00", "end": "2017-09-06T11:20:00",
       "instrument": "HMI", "max_files": 1, "physobs": "LOS_magnetic_field"},
      "Science FITS from the VSO — the AR 12673 magnetogram used throughout "
      "the measure examples. Byte-stable: the hmipin validation case "
      "checksums this exact file.",
      show=["n_files"], skills=["datasources/vso.md", "missions/sdo.md"]),
    E("retrieve", "fetch_vso",
      {"start": "2026-09-04T06:25:00", "end": "2026-09-04T06:27:00",
       "instrument": "AIA", "wavelength_angstrom": 1600, "max_files": 1},
      name="_aia1600", hidden=True),
    E("retrieve", "fetch_vso",
      {"start": "2017-09-06T12:00:00", "end": "2017-09-06T12:02:00",
       "instrument": "AIA", "wavelength_angstrom": 171, "max_files": 1},
      name="_aia171", hidden=True),
    E("retrieve", "fetch_spacecraft_ephemeris",
      {"spacecraft": ["ace", "wind"], "start": "2017-09-01T00:00:00Z",
       "end": "2017-09-08T00:00:00Z"},
      "L1 monitor trajectories from SSCWeb (GSE km).",
      show=["n_records", "columns"], skills=["datasources/sscweb.md"]),
    E("retrieve", "fetch_pyspedas",
      {"mission": "ace", "instrument": "mfi", "start": "2017-09-06",
       "end": "2017-09-08"},
      "The same ACE field through the mission's own pySPEDAS loader — the "
      "validation suite holds the two pipelines to 2% agreement.",
      show=["n_records", "columns"], skills=["tools/pyspedas_pytplot.md"]),
    E("retrieve", "fetch_swpc_timeseries", {"product": "plasma"},
      "Real-time L1 solar wind (last few days, operational grade).",
      show=["n_records", "columns"], skills=["datasources/noaa_swpc.md"]),
    E("retrieve", "fetch_kyoto_dst", {"year": 2003, "month": 10,
                                      "revision": "final"},
      "Kyoto WDC hourly Dst, pinned to the *final* revision — the revision "
      "is part of the citation.", show=["n_records", "revision"],
      skills=["methods/geomagnetic_storm_analysis.md"]),
    E("retrieve", "fetch_gfz_index", {"index": "Kp", "start": "2024-05-10",
                                      "end": "2024-05-12"},
      "Definitive GFZ Kp for the Gannon storm (max 9.0).",
      show=["n_records"], skills=["methods/geomagnetic_storm_analysis.md"]),
    E("retrieve", "fetch_solar_cycle", {},
      "NOAA solar-cycle progression: monthly and smoothed sunspot number.",
      show=["n_records"], skills=["methods/timing_periodicity.md"]),
    E("retrieve", "save_json",
      {"name": "examples_note",
       "payload": {"purpose": "persist derived event lists between steps",
                   "created_by": "gen_examples.py"}},
      "Persist any JSON-able intermediate so a later session can pick it up.",
      show=["file"]),
]

EXAMPLES += [
    # --------------------------------------------------------------- reduce
    E("reduce", "describe_series", {"file": R("_omni_gannon1m", "file")},
      "First thing to run on any fetched CSV: coverage, gaps, fill fractions. "
      "A third of the Gannon plasma record is missing, and analyses must know that.",
      show=["n_records", "cadence_median"], skills=["methods/troubleshooting.md"]),
    E("reduce", "resample_series",
      {"file": R("_omni_gannon1m", "file"), "cadence": "1h",
       "out_name": "examples_gannon_1h.csv"},
      "1-min to hourly. Averaging shallows extremes: the -518 nT SYM-H spike "
      "becomes -436 nT on this grid — quote which grid a minimum came from.",
      show=["n_records"], skills=["methods/error_estimation.md"]),
    E("reduce", "compute_derived",
      {"file": R("resample_series", "file"),
       "expression": "1.6726e-6 * proton_density * flow_speed**2",
       "out_column": "pdyn_npa", "out_name": "examples_gannon_1h.csv"},
      "Derived column via pandas eval — dynamic pressure from n and V. No "
      "arbitrary code: numeric expressions over existing columns only.",
      show=["columns"]),
    E("reduce", "interpolate_gaps",
      {"file": R("resample_series", "file"), "max_gap": "3h",
       "out_name": "examples_gannon_interp.csv"},
      "Gap-aware interpolation: short gaps filled, long ones left NaN so data "
      "absence stays visible.", show=["interp_limit_points"]),
    E("reduce", "shift_time",
      {"file": R("resample_series", "file"), "shift": "45min",
       "out_name": "examples_gannon_shifted.csv"},
      "Fixed lag shift, e.g. L1 to magnetopause before driving a model with "
      "real-time wind.", show=["n_records"]),
    E("reduce", "merge_series",
      {"files": [R("resample_series", "file"),
                 R("_swmf_gannon_1h", "file")],
       "out_name": "examples_gannon_merged.csv"},
      "Outer join on the time index. Timezone-aware inputs are converted to "
      "naive UTC and every conversion is reported; duplicate column names "
      "refuse rather than silently suffixing.",
      show=["n_records", "tz_normalized"]),
    E("reduce", "transform_coordinates",
      {"file": R("fetch_pyspedas", "file"),
       "columns": ["BGSEc_0", "BGSEc_1", "BGSEc_2"],
       "from_coords": "gse", "to_coords": "gsm",
       "out_name": "examples_ace_gsm.csv"},
      "GSE to GSM for the ACE field — validated against an independent "
      "geopack implementation to 1e-4 nT.", show=["n_records"],
      skills=["methods/coordinate_systems.md"]),
    E("reduce", "load_solar_map", {"fits_file": R("fetch_vso", "files[0]")},
      "Open a FITS as a sunpy Map and report its identity — instrument, time, "
      "scale, observer — without plotting anything.",
      show=["instrument", "date", "shape"], skills=["tools/sunpy.md"]),
    E("reduce", "aia_degradation", {"date": "2020-06-01",
                                    "channels": [171, 304]},
      "AIA sensitivity loss by 2020: 171 at ~0.74 of launch, 304 at ~0.06. "
      "Ignoring this turns instrument decay into fake solar variability.",
      show=["factors"], skills=["missions/sdo.md", "tools/sunpy.md"]),
    E("reduce", "correct_aia_map", {"fits_file": R("_aia171", "files[0]")},
      "Apply that correction to an AIA 171 image, writing a corrected FITS. "
      "UV channels (1600/1700) have no degradation series and are refused.",
      show=["factor", "channel"], skills=["missions/sdo.md"]),

    # -------------------------------------------------------------- measure
    E("measure", "find_extrema",
      {"file": R("fetch_omni", "file"), "column": "DST1800", "mode": "min"},
      "The Halloween 2003 Dst minimum — matches the published -383 nT.",
      show=["value", "time"],
      skills=["methods/geomagnetic_storm_analysis.md"]),
    E("measure", "storm_metrics",
      {"file": R("fetch_omni", "file"), "dst_column": "DST1800"},
      "Minimum, classification, main-phase and recovery durations from a Dst series.",
      show=["dst_min_nT", "time_of_min", "classification", "main_phase_hours"],
      skills=["methods/geomagnetic_storm_analysis.md"]),
    E("measure", "verify_claim",
      {"claimed_value": -383.0, "computed_value": R("find_extrema", "value"),
       "claimed_units": "nT", "computed_units": "nT",
       "tolerance_percent": 2.0,
       "claim_description": "Halloween 2003 Dst minimum (Kyoto final)",
       "computed_audit_id": R("find_extrema", "audit_id")},
      "Formal verdict on a published value vs an audit-logged computation. "
      "Refuses unit mismatches and unknown audit ids rather than comparing anyway.",
      show=["verdict", "difference_percent"],
      skills=["methods/paper_reproduction.md"]),
    E("measure", "find_flares",
      {"file": R("fetch_goes_xrs", "file")},
      "SWPC-style flare detection on the XRS long channel: 2017-09-06 yields "
      "the X2.2 and the X9.3.", show=["n_flares", "flares[0].peak_class"],
      skills=["methods/flare_analysis.md"]),
    E("measure", "flare_probability",
      {"mcintosh_class": "Dkc", "previous_class": "Dai", "lon_deg": -20.0},
      "Per-region flare probability from the McIntosh class, evolution-aware. "
      "The three letters are read from three separate tables and never "
      "multiplied — `component_span` carries the honest spread.",
      show=["levels.C.probability", "levels.M.probability",
            "levels.C.components", "assumed_no_evolution"],
      skills=["methods/flare_analysis.md"]),
    E("measure", "model_dst",
      {"file": R("_omni_stpatrick1h", "file"), "v_column": "V1800",
       "bz_column": "BZ_GSM1800", "density_column": "N1800",
       "dst_column": "DST1800", "out_name": "examples_modeldst.csv"},
      "O'Brien & McPherron ring-current nowcast over the 2015 St Patrick's "
      "storm, scored against the observed index it was given.",
      show=["model_min_nT", "time_of_model_min", "skill"],
      skills=["methods/geomagnetic_storm_analysis.md",
              "methods/solar_wind_analysis.md"]),
    E("measure", "cme_arrival",
      {"v0_kms": 1400.0, "launch_time": "2012-07-12T19:35Z", "w_kms": 400.0},
      "Drag-based arrival for the 2012-07-12 CME: 1.9 h from the observed "
      "shock, inside the stated window.",
      show=["arrival_estimate", "transit_hours"],
      skills=["methods/cme_analysis.md"]),
    E("measure", "propagation_delay", {"solar_wind_speed_kms": 450.0},
      "Ballistic L1-to-magnetopause delay at a typical wind speed.",
      show=["delay_minutes"], skills=["methods/solar_wind_analysis.md"]),
    E("measure", "detect_icme",
      {"file": R("_omni_stpatrick1m", "file"), "speed_column": "flow_speed",
       "temperature_column": "T", "by_column": "BY_GSM",
       "bz_column": "BZ_GSM", "density_column": "proton_density",
       "out_name": "examples_icme.png"},
      "Shock, sheath and low-Tp ejecta for St Patrick's 2015 — boundaries "
      "within the hour of Richardson & Cane.",
      show=["shock_time", "icme.start", "icme.end", "driver"],
      fig="file", save_as="icme_stpatrick",
      skills=["methods/solar_wind_analysis.md",
              "methods/geomagnetic_storm_analysis.md"]),
    E("measure", "characterize_sep",
      {"file": R("fetch_goes_protons", "file"), "flux_10mev_column": "p_gt10",
       "flux_30mev_column": "p_gt30",
       "flare_peak_time": "2017-09-10T16:06:00Z", "flare_class": "X8.2",
       "flare_lon_deg": 88.0, "out_name": "examples_sep.png"},
      "The 2017-09-10 S3 radiation storm from measured GOES channels: peak "
      "1493 pfu vs SWPC's published 1490, onset physics against the Parker "
      "spiral.", show=["sep.s_scale", "sep.peak_10mev", "sep.onset",
                       "physics.connection_angle_deg"],
      fig="file", save_as="sep_20170910",
      skills=["methods/sep_analysis.md", "datasources/goes_ncei.md"]),
    E("measure", "radio_bursts",
      {"file": R("fetch_cdaweb_spectrogram", "file"),
       "out_name": "examples_radio.png"},
      "Type III / type II classification on the WIND/WAVES spectrum; the "
      "X9.3's shock drives a 2160 km/s type II candidate.",
      show=["n_bursts", "counts"], fig="file", save_as="radio_20170906",
      skills=["methods/radio_burst_analysis.md"]),
    E("measure", "magnetogram_metrics",
      {"fits_file": R("fetch_vso", "files[0]"), "lat_deg": -9.0,
       "lon_deg": 33.0, "half_deg": 8.0, "out_name": "examples_magnetogram.png"},
      "Unsigned flux, peak field and the polarity-inversion-line proxy for "
      "AR 12673 — the delta-class signature, measured rather than eyeballed.",
      show=["region.unsigned_flux_mx", "region.max_abs_b_g",
            "region.pil_length_mm"], fig="file", save_as="magnetogram_ar12673",
      skills=["missions/sdo.md", "methods/flare_analysis.md"]),
    E("measure", "cross_correlate",
      {"file": R("model_dst", "file"), "column_a": "DST1800",
       "column_b": "dst_model", "max_lag": "12h"},
      "Lagged correlation between observed and modelled Dst.",
      show=["best_corr", "best_lag"], skills=["methods/timing_periodicity.md"]),
    E("measure", "linear_fit",
      {"file": R("model_dst", "file"), "x_column": "DST1800",
       "y_column": "dst_model"},
      "Least-squares fit with parameter uncertainties.",
      show=["coefficients", "r_squared"], skills=["methods/error_estimation.md"]),
    E("measure", "lomb_scargle",
      {"file": R("_omni_2017", "file"), "column": "V1800",
       "min_period": "2D", "max_period": "60D"},
      "Periodogram of a year of solar wind speed: the ~27-day synodic "
      "rotation and its 13.5-day harmonic.", show=["top_periods_days"],
      skills=["methods/timing_periodicity.md"]),
    E("measure", "superposed_epoch",
      {"file": R("_omni_gannon1m", "file"), "column": "SYM_H",
       "epochs": ["2024-05-10T19:21:00Z", "2024-05-10T23:12:00Z",
                  "2024-05-11T02:14:00Z"],
       "before": "6h", "after": "12h", "cadence": "5min"},
      "SYM-H stacked around the Gannon storm's three published intensification "
      "steps (Hajra et al. 2024).", show=["n_epochs", "n_records"],
      skills=["methods/superposed_epoch.md"]),
    E("measure", "extreme_value",
      {"file": R("_dst_60yr", "file"), "column": "DST1800",
       "threshold": -100.0, "direction": "min"},
      "Peaks-over-threshold statistics on six decades of Dst: the 1989 "
      "storm's -589 nT and a ~-580 nT 100-year level.",
      show=["n_exceedances", "rate_per_year", "return_levels"],
      skills=["methods/error_estimation.md",
              "methods/geomagnetic_storm_analysis.md"]),
    E("measure", "extreme_value_sweep",
      {"file": R("_dst_60yr", "file"), "column": "DST1800",
       "thresholds": [-80.0, -100.0, -120.0],
       "decluster_gaps_hours": [24.0, 48.0, 72.0], "direction": "min"},
      "The same return level across threshold and declustering conventions — "
      "how sensitive is the answer to the analyst's choices?",
      show=["n_conventions"], skills=["methods/error_estimation.md"]),
    E("measure", "plasma_parameters",
      {"density_cm3": 5.0, "b_nT": 5.0, "temperature_K": 1e5},
      "Alfven speed, beta, gyroradius from PlasmaPy's formulary — checked "
      "against the analytic expressions in validation.",
      show=["alfven_speed_km_s", "plasma_beta"],
      skills=["tools/plasmapy.md", "tools/pyhc_ecosystem.md"]),
    E("measure", "trace_field_line",
      {"x_gsm_re": 6.6, "y_gsm_re": 0.0, "z_gsm_re": 0.0,
       "time": "2017-09-06T12:00:00", "kp": 2},
      "Tsyganenko T89 + IGRF trace from geosynchronous noon: closed line, "
      "auroral-zone footpoint.", show=["topology",
                                       "north_footpoint.geo_lat_deg"],
      skills=["methods/coordinate_systems.md"]),
    E("measure", "hindcast_forecasts",
      {"start": "2024-05-01", "end": "2024-05-31",
       "out_name": "examples_hindcast.png",
       "table_name": "examples_hindcast.md"},
      "The live monitor's forecast rule replayed over the Gannon month and "
      "scored against DONKI shocks and storms. This is the tool that set the "
      "45-degree cone.", show=["n_hits", "n_false_alarms", "hit_rate",
                               "storm_recall"],
      fig="file", save_as="hindcast_may2024",
      skills=["methods/cme_analysis.md"]),
    E("measure", "sta_20120723_summary", {"file": R("_sta_2012", "file")},
      "A user-scoped one-off tool (users/cayoung): the 2012-07-23 STEREO-A "
      "event summary, encoding that event's shock-finding convention. "
      "One-off analyses live in profiles; core stays general.",
      show=["shock_time", "peak_b_nt", "r_au"],
      skills=["methods/cross_spacecraft.md"]),
]

# _swmf_gannon_1h must run before merge_series consumes it: insert in order.
_swmf_1h = E("reduce", "resample_series",
             {"file": R("fetch_model_output", "file"), "cadence": "1h",
              "out_name": "examples_swmf_1h.csv"},
             name="_swmf_gannon_1h", hidden=True)
EXAMPLES.insert(
    next(i for i, x in enumerate(EXAMPLES) if x["name"] == "merge_series"),
    _swmf_1h)

EXAMPLES += [
    # --------------------------------------------------------------- report
    E("report", "plot_timeseries",
      {"file": R("model_dst", "file"), "columns": ["DST1800", "dst_model"],
       "series_labels": ["Observed Dst (OMNI hourly)",
                         "O'Brien & McPherron model"],
       "y_label": "Dst (nT)",
       "title": "St Patrick's Day 2015 — observed vs modelled ring current",
       "event_times": ["2015-03-17T04:45:00"], "event_labels": ["shock"],
       "out_name": "examples_timeseries.png"},
      "Publication-styled single-panel comparison; event markers as dashed "
      "verticals.", fig="file", save_as="timeseries_modeldst",
      skills=["tools/plotting_conventions.md"]),
    E("report", "plot_stack", build=_stack_kwargs,
      note="The standard space-physics figure: stacked panels on a shared "
           "time axis, shock arrival and SYM-H minimum marked.",
      fig="file", save_as="gannon_stack",
      skills=["tools/plotting_conventions.md",
              "methods/solar_wind_analysis.md"]),
    E("report", "plot_scatter",
      {"file": R("compute_derived", "file"), "x_column": "flow_speed",
       "y_column": "pdyn_npa", "fit": False, "log_y": True,
       "x_label": "V (km/s)", "y_label": "Pdyn (nPa)",
       "title": "Gannon storm — dynamic pressure vs speed (hourly)",
       "out_name": "examples_scatter.png"},
      "Two-column scatter from the derived-pressure file.",
      fig="file", save_as="scatter_pdyn"),
    E("report", "plot_distribution",
      {"file": R("_omni_gannon1m", "file"), "columns": ["BZ_GSM"],
       "kind": "hist", "y_label": "Bz GSM (nT)",
       "title": "Bz distribution through the Gannon storm",
       "out_name": "examples_dist.png"},
      "Distribution view of a column — the -47.9 nT southward tail is the "
      "storm.", fig="file", save_as="dist_bz"),
    E("report", "plot_solar_map", {"fits_file": R("fetch_vso", "files[0]"),
                                   "out_name": "examples_solarmap.png"},
      "Any solar FITS with its proper colormap — the AR 12673 magnetogram.",
      fig="file", save_as="solarmap_hmi", skills=["tools/sunpy.md"]),
    E("report", "plot_solar_regions",
      {"fits_file": R("_aia1600", "files[0]"),
       "regions": [
           {"region": 4521, "location": "N09E23", "spot_class": "Hsx",
            "mag_class": "A"},
           {"region": 4523, "location": "N10E31", "spot_class": "Hsx",
            "mag_class": "A"},
           {"region": 4524, "location": "N12E64", "spot_class": "Cso",
            "mag_class": "B"}],
       "region_time": "2026-09-04T06:25:00Z", "label": "class",
       "out_name": "examples_regions.png"},
      "NOAA regions projected through the map's own WCS (B0 and P handled). "
      "Positions here are raw station measurements at their own observation "
      "time, two minutes from the image — no rotation correction to get "
      "wrong. The matching epoch matters: SWPC's daily `location` is valid "
      "at 2400 UT and sits ~14.5 deg west of these.",
      show=["n_annotated", "age_hours"], fig="file", save_as="regions_aia1600",
      skills=["missions/sdo.md", "datasources/noaa_swpc.md"]),
    E("report", "plot_orbits",
      {"file": R("fetch_spacecraft_ephemeris", "file"), "plane": "xy",
       "units": "Re", "title": "ACE and Wind, 2017-09-01 to 08 (GSE)",
       "out_name": "examples_orbits.png"},
      "Trajectories from the ephemeris CSV; Earth at origin.",
      fig="file", save_as="orbits_l1", skills=["datasources/sscweb.md"]),
    E("report", "write_pdf_report", build=_pdf_sections,
      note="Assemble figures and prose into a PDF. This example binds two "
           "figures generated above into one page.",
      show=["file", "n_sections"], fig="file", save_as="examples_report"),

    # ------------------------------------- reproduction chain (report+measure)
    E("measure", "propagation_delay", {"solar_wind_speed_kms": 500.0},
      name="_repro_delay", hidden=True),
    E("measure", "verify_claim",
      {"claimed_value": R("_repro_delay", "delay_minutes"),
       "computed_value": R("_repro_delay", "delay_minutes"),
       "claimed_units": "minutes", "computed_units": "minutes",
       "tolerance_percent": 1.0,
       "claim_description": "L1 propagation delay (worked example)",
       "computed_audit_id": R("_repro_delay", "audit_id")},
      name="verify_claim_repro", hidden=True),
    E("report", "create_reproduction_manifest", build=_manifest_kwargs,
      note="A deterministic, versioned record of a reproduced claim: what the "
           "paper said, what was computed, by which audited calls. The real "
           "worked example is the 2012-07-23 extreme CME under "
           "users/cayoung/analyses/.",
      show=["file", "n_claims"]),
    E("measure", "validate_reproduction_manifest",
      {"file": R("create_reproduction_manifest", "file")},
      "Validates the manifest schema AND that every referenced audit id "
      "exists with matching recorded values.",
      show=["valid", "n_claims", "n_audit_refs"]),
    E("report", "render_reproduction_report",
      {"file": R("create_reproduction_manifest", "file"),
       "out_name": "examples_reproduction.md"},
      "Deterministic Markdown from the validated manifest — same input, same "
      "bytes.", show=["file"], fig="file", save_as="reproduction_example"),
    E("report", "export_html",
      {"markdown_file": R("render_reproduction_report", "file"),
       "out_name": "examples_export.html"},
      "Self-hostable HTML from any workspace Markdown; offline, styles "
      "inlined, client-render runtimes SRI-pinned.",
      show=["bytes"], fig="file", save_as="examples_export"),
]


# --------------------------------------------------------------------------
# skills and modules sections
# --------------------------------------------------------------------------

SKILL_DIR_TITLES = {
    "missions": "Missions", "methods": "Methods", "datasources": "Data sources",
    "tools": "Software craft", "": "General",
}


def _skill_catalog():
    """(relpath, title, summary) for every skill document."""
    out = []
    for p in sorted((ROOT / "skills").rglob("*.md")):
        rel = p.relative_to(ROOT / "skills").as_posix()
        if rel == "README.md":
            continue
        lines = p.read_text().splitlines()
        title = lines[0].lstrip("# ").strip() if lines else rel
        summary = ""
        for ln in lines[1:6]:
            if ln.startswith("> "):
                summary = ln[2:].strip()
                break
        out.append((rel, title, summary))
    return out


MODULE_EXAMPLES = [
    ("helio_agent.registry", "Every tool call goes through here; run_tool "
     "wraps the function with an audit entry.", '''from helio_agent.registry import run_tool, list_tools, get_tool

r = run_tool("propagation_delay", solar_wind_speed_kms=450.0)
print(r["delay_minutes"], r["audit_id"])   # every call carries its audit id
print(len(list_tools()), "tools registered")
print(get_tool("fetch_omni").doc.splitlines()[0])'''),
    ("helio_agent.audit", "The append-only record every result traces back "
     "to.", '''import json
from helio_agent.workspace import LOG_DIR

last = json.loads(open(LOG_DIR / "audit.jsonl").readlines()[-1])
print(last["audit_id"], last["tool"], last["status"])'''),
    ("helio_agent.http", "Content-addressed cache for direct HTTP GETs "
     "(library-managed transfers are NOT covered — see the input-pin "
     "validation cases).", '''from helio_agent.http import cached_get

r = cached_get("https://services.swpc.noaa.gov/json/solar_regions.json",
               ttl_seconds=3600)
print(len(r.json()), "rows, served with HELIO_CACHE_MODE readwrite")'''),
    ("helio_agent.workspace", "Where everything lands. With HELIO_AGENT_USER "
     "set, data/outputs/logs resolve to users/<name>/workspace.",
     '''from helio_agent.workspace import WORKSPACE, data_path, output_path, active_user

print(active_user(), WORKSPACE)
print(data_path("example.csv"))     # workspace/data/example.csv
print(output_path("example.png"))   # workspace/outputs/example.png'''),
    ("helio_agent.monitor", "One standing-watch cycle: import CMEs, forecast "
     "Earth-directed ones, grade matured windows. docs/MONITOR.md explains "
     "it in plain language.", '''from helio_agent.monitor import cycle, EARTH_DIRECTED_MAX_LON

print(EARTH_DIRECTED_MAX_LON)       # 45.0 — see hindcast.recall_neutral
summary = cycle()                   # what `helio-agent monitor` runs
print(summary["ledger_score"])'''),
    ("helio_agent.reports", "The daily sun-news report builder behind "
     "`helio-agent report sun-news`.", '''# CLI is the intended interface:
#   uv run helio-agent report sun-news --archive
# Builds markdown + HTML + PDF editions from audited tool calls.'''),
    ("helio_agent.reproduction", "Schema and rendering for reproduction "
     "manifests (see the create/validate/render chain above).",
     '''from helio_agent.registry import run_tool

m = run_tool("validate_reproduction_manifest", file="papers/example.json")
print(m["valid"], m["n_audit_refs"])'''),
    ("helio_agent.style", "One matplotlib style for every figure: "
     "CVD-checked palette, UTC axes.", '''from helio_agent.style import apply_style, PALETTE

apply_style()
print(PALETTE[:3])   # the first three series colours'''),
    ("helio_agent.cli", "The `helio-agent` entry point.", '''# uv run helio-agent list
# uv run helio-agent describe detect_icme
# uv run helio-agent run fetch_omni '{"start":"...","end":"..."}'
# uv run helio-agent audit 5
# uv run helio-agent replay <audit-id>
# uv run helio-agent monitor'''),
    ("helio_agent.tools.*", "The six tool families themselves — every "
     "example in sections 1-6 exercises one of these modules.", None),
]


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

FAMILY_ORDER = ["discover", "literature", "retrieve", "reduce", "measure",
                "report"]
FAMILY_INTROS = {
    "discover": "Find out what exists before fetching it: catalog searches, "
                "event databases, live conditions.",
    "literature": "ADS and arXiv access — search, fetch, cite. Used both for "
                  "context and to source the constants inside tools.",
    "retrieve": "Every retrieval writes a workspace CSV (naive-UTC index, "
                "NaN fills) or a FITS/PNG, and returns the path plus a "
                "summary. Downstream tools operate on those files.",
    "reduce": "Shape data without measuring anything: resample, merge, "
              "derive, transform, correct.",
    "measure": "Every quantitative claim in a report comes from one of "
               "these, and carries the audit id to prove it.",
    "report": "Publication-styled figures and documents. The plotting "
              "conventions (UTC axes, CVD-safe palette, labelled units) come "
              "from one shared style module.",
}


def _cli_line(tool, kwargs):
    return (f"uv run helio-agent run {tool} "
            f"'{json.dumps(kwargs, default=str)}'")


def _shorten_paths(text):
    return (text.replace(str(ROOT) + "/", "")
                .replace("users/cayoung/workspace/", "<workspace>/"))


def render(examples, results):
    lines = []
    add = lines.append
    add("# Worked examples\n")
    add("*Generated by `scripts/gen_examples.py` — every example below was "
        "actually executed, and every number carries the audit id of the "
        "call that produced it. Regenerate with "
        "`uv run python scripts/gen_examples.py` (runs against live "
        "archives; not a CI step).*\n")
    n_vis = sum(1 for e in examples if not e["hidden"])
    n_fig = sum(1 for e in examples
                if results.get(e["name"], {}).get("figure"))
    add(f"{n_vis} worked examples across the six tool families, "
        f"{n_fig} of them producing the figures embedded here "
        "(copied into `docs/examples/`, large images downscaled). "
        "Chained inputs — a measure example reading a retrieve example's "
        "file — are real chains: the CSVs referenced are the ones the "
        "earlier example wrote.\n")
    add("Sections 1–6 cover the tools, section 7 shows where each skill "
        "document earns its place, section 8 the Python API of the "
        "supporting modules.\n")

    counter = 0
    skill_uses: dict[str, list] = {}
    for fi, family in enumerate(FAMILY_ORDER, 1):
        fam_ex = [e for e in examples if e["family"] == family
                  and not e["hidden"]]
        add(f"\n## {fi}. {family} ({len(fam_ex)} tools)\n")
        add(FAMILY_INTROS[family] + "\n")
        for ex in fam_ex:
            counter += 1
            name = ex["name"]
            entry = results.get(name, {})
            res = entry.get("result", {})
            add(f"\n### {fi}.{counter} `{ex['tool']}`\n")
            if ex["note"]:
                add(ex["note"] + "\n")
            kwargs = entry.get("kwargs", ex["kwargs"])
            add("```bash")
            add(_shorten_paths(_cli_line(ex["tool"], kwargs)))
            add("```")
            if res.get("status") == "error":
                add(f"\n**FAILED**: {res.get('error', '')[:200]}\n")
                continue
            shown = []
            for key in ex["show"]:
                v = _dig(res, key)
                if v is not None:
                    shown.append((key, v))
            if not shown:
                for k, v in res.items():
                    if k in ("status", "audit_id", "artifacts", "note"):
                        continue
                    if isinstance(v, (str, int, float, bool)):
                        shown.append((k, v))
                    if len(shown) >= 6:
                        break
            add("```text")
            for k, v in shown:
                add(f"{k:<28s} {_shorten_paths(_fmt(v))}")
            add(f"{'audit_id':<28s} {res.get('audit_id', '')}")
            add("```")
            if entry.get("figure"):
                add(f"\n![{ex['tool']} example](examples/{entry['figure']})\n")
            if ex["skills"]:
                links = ", ".join(f"[`{s}`](../skills/{s})"
                                  for s in ex["skills"])
                add(f"*Skills exercised: {links}*\n")
            for s in ex["skills"]:
                skill_uses.setdefault(s, []).append(f"{fi}.{counter}")

    # ---- skills section
    add("\n## 7. Skills in practice\n")
    add("Skills are knowledge documents, not code — the contract requires "
        "reading the relevant ones before an analysis. This table shows "
        "where each one is exercised by the examples above; a skill with no "
        "example number is background craft that shapes how the others are "
        "used.\n")
    catalog = _skill_catalog()
    by_dir: dict[str, list] = {}
    for rel, title, summary in catalog:
        d = rel.split("/")[0] if "/" in rel else ""
        by_dir.setdefault(d, []).append((rel, title, summary))
    for d in ("missions", "datasources", "methods", "tools", ""):
        if d not in by_dir:
            continue
        add(f"\n### {SKILL_DIR_TITLES[d]} ({len(by_dir[d])})\n")
        add("| Skill | What it teaches | Exercised by |")
        add("|---|---|---|")
        for rel, title, summary in by_dir[d]:
            used = ", ".join(skill_uses.get(rel, [])) or "—"
            add(f"| [`{rel}`](../skills/{rel}) | {summary or title} | {used} |")

    # ---- modules section
    add("\n## 8. Modules — the Python API\n")
    add("Longer pipelines can be driven from Python instead of the CLI; "
        "every call is still one audit entry. `docs/MODULES.md` documents "
        "each module in full — these are the entry points in action.\n")
    for mod, blurb, snippet in MODULE_EXAMPLES:
        add(f"\n### `{mod}`\n")
        add(blurb + "\n")
        if snippet:
            add("```python")
            add(snippet)
            add("```")
    add("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run only this family (others from cache)")
    ap.add_argument("--fresh", action="append", default=[],
                    help="re-run this example name even if cached")
    args = ap.parse_args()
    results, failures = run_examples(EXAMPLES, only=args.only,
                                     fresh=set(args.fresh))
    OUT.write_text(render(EXAMPLES, results))
    print(f"\nwrote {OUT} ({len(OUT.read_text().splitlines())} lines)")
    if failures:
        print(f"{len(failures)} example(s) FAILED:")
        for n, err in failures:
            print(f"  {n}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
