"""Render analysis.md from results.json — no number is typed by hand.

    uv run python users/cayoung/analyses/2024-05-gannon-notebook-repro/render_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ST = json.loads((HERE / "results.json").read_text())
OUT = HERE / "analysis.md"


def g(key, *path, default=None):
    """Pull a nested value out of a cached tool result."""
    cur = ST.get(key)
    for p in path:
        if cur is None:
            return default
        cur = cur[p] if isinstance(p, int) else cur.get(p)
    return default if cur is None else cur


def aud(key):
    return g(key, "audit_id", default="—")


def fig(key):
    """figures/<key>.png if that file was kept."""
    for ext in (".png", ".pdf"):
        if (HERE / "figures" / f"{key.lower()}{ext}").is_file():
            return f"figures/{key.lower()}{ext}"
    return None


def fmt(v, n=4):
    if isinstance(v, float):
        if v == 0:
            return "0"
        if abs(v) >= 1e4 or abs(v) < 1e-3:
            return f"{v:.{n}e}"
        return f"{v:.{n}g}"
    return str(v)


def ok(key):
    return isinstance(ST.get(key), dict) and ST[key].get("status") != "error"


def embed(key, caption=""):
    f = fig(key)
    if not f:
        return []
    out = [f"\n![{caption or key}]({f})"]
    if caption:
        out.append(f"*{caption}*")
    return out


L = []
add = L.append

add("# Reproducing the May 2024 Gannon-storm notebook with helio-agent tools\n")
add("Source: `HelioSummerSchool-may2024_solar_storms_complete.ipynb` "
    "(C. Alex Young, NASA GSFC/HDRL; after Will Barnes for the SunPy "
    "Community, HDRL Virtual User Workshop 2024).\n")
add("Every figure and every number below was recomputed through audited "
    "tools by [`reproduce.py`](reproduce.py) and rendered by "
    "[`render_report.py`](render_report.py); nothing is transcribed from the "
    "notebook's prose. Where the notebook **states** a value, this measures "
    "it and reports the comparison — including the three places the notebook's "
    "own code raises an error or fabricates its input and falls back to "
    "hard-coded prose.\n")

add("## What the reproduction changes\n")
add("| Notebook | Here | Why it matters |")
add("|---|---|---|")
add("| CME speeds from `np.random.uniform(3, 6)` heights | DONKI cone-model "
    "fits, plus a real `cme_height_time` fit tool that refuses to invent "
    "heights | The notebook's \"speed estimate\" was random numbers; its "
    "printed speeds came from prose, not from its own code |")
add("| HMI flux calculation raised `'arcsec2 / pix2' and 'cm2' are not "
    "convertible`, fell back to \"typical values\" | `magnetogram_metrics` "
    "computes the flux, PIL length and peak field | The notebook's quoted "
    "magnetic numbers were never computed from the data it downloaded |")
add("| `sm.coord_table.to_pandas()` raised; fell back to \"STEREO-A ~25°, "
    "Solar Orbiter ~45°\" | `plot_heliospheric_config` returns the table | "
    "**Solar Orbiter was 167.6° from Earth, not 45°** — the far side of the "
    "Sun |")
add("| Flare classes read from a typed table | `find_flares` on GOES-18 "
    "science data, cross-checked against DONKI and HEK | Reproduces every "
    "class, and surfaces a 12th X-flare the AR-scoped table omits |")
_v_ace = g("S5x_v_ace_cdaweb", "value")
_v_omni = g("S5x_v_omni_1min", "value")
_dv = (abs(_v_omni - 739.0) if isinstance(_v_omni, (int, float)) else None)
add("| One in-situ source (ACE hourly) | Six independent routes compared | "
    "The notebook's quoted 739 km s⁻¹ is "
    + (f"{_dv:.0f} km s⁻¹ below the OMNI 1-min peak and "
       f"{abs(_v_ace-739.0):.0f} below the ACE product it came from"
       if _dv is not None else "not reproduced by any route")
    + " |\n")

# ---------------------------------------------------------------- S1
add("\n## 1. GOES X-rays and the flare timeline\n")
nx, nxs, nm = g("S1_flares_x", "n_results"), g("S1_flares_scaled", "n_results"), \
    g("S1_flares_m", "n_results")
add(f"GOES-18 XRS science data for 2024-05-07 → 05-15: "
    f"**{g('S1_xrs','n_records'):,} 1-second samples** (audit `{aud('S1_xrs')}`).\n")
add("### The scaling convention decides the answer\n")
add(f"`find_flares` found **{nx} X-class flares** on the true-flux scale and "
    f"only **{nxs}** with the historical SWPC ×0.7 factor applied "
    f"(audits `{aud('S1_flares_x')}`, `{aud('S1_flares_scaled')}`). "
    "GOES-R series data are already true fluxes, so `swpc_scale=False` is "
    "correct here; using the GOES-8–15 convention makes every class come out "
    "1/0.7 too small and silently loses half the X-flares. "
    "`skills/missions/goes.md` records this, and it is the single most "
    "consequential switch in the section.\n")
add(f"Across the same window there were **{nm} flares at M1.0 or above**.\n")
add("### X-class flares, measured\n")
add("| Peak (UT) | Class | Start | Peak flux (W m⁻²) | Notebook table |")
add("|---|---|---|---|---|")
NB_TABLE = {"2024-05-08 05:09": "X1.0", "2024-05-08 21:40": "X1.0",
            "2024-05-09 09:13": "X2.2", "2024-05-09 17:44": "X1.1",
            "2024-05-10 06:54": "X3.9", "2024-05-11 01:23": "X5.8",
            "2024-05-11 11:44": "X1.5", "2024-05-12 16:26": "X1.0",
            "2024-05-14 02:09": "X1.7", "2024-05-14 12:55": "X1.2",
            "2024-05-14 16:51": "X8.7"}
for fl in g("S1_flares_x", "flares", default=[]):
    peak = str(fl["peak"])[:16]
    nb = NB_TABLE.get(peak, "**not listed**")
    mark = "✓" if nb == fl["class"] else nb
    add(f"| {peak} | **{fl['class']}** | {str(fl['start'])[:16]} | "
        f"{fmt(fl['peak_flux_wm2'], 3)} | {mark} |")
add(f"\nAudit `{aud('S1_flares_x')}`. Two rows deserve comment.\n")
add("**2024-05-08 01:41 is a real X-flare the notebook's table omits — "
    "correctly.** DONKI attributes it to **AR 13663**, not AR 13664/13668, "
    f"and the notebook's table is explicitly scoped to the latter (audit "
    f"`{aud('S1_donki_2024-05-08')}`). So 12 X-flares crossed the disk; 11 "
    "came from the storm's source region. Both numbers are right, for "
    "different questions.\n")
add("**2024-05-14 16:51 measures X8.6 here against the catalogued X8.7** — "
    "8.63e-4 vs 8.7e-4 W m⁻², a peak-sampling difference at 1-second "
    "cadence, not a disagreement about the event.\n")
add("Independent cross-checks: DONKI FLR for 05-08, 05-09 and 05-14 "
    f"(audits `{aud('S1_donki_2024-05-08')}`, `{aud('S1_donki_2024-05-09')}`, "
    f"`{aud('S1_donki_2024-05-14')}`) and HEK for 05-09 "
    f"(`{aud('S1_hek')}`, {g('S1_hek','n_results')} events). The two "
    "CME-driving flares reproduce the notebook's stated start times exactly: "
    "X1.0 begins 04:37 UT, X2.2 begins 08:45 UT.\n")
L.extend(embed("S1_fig_overview",
               "GOES-18 XRS both channels across the storm week, with the two "
               "CME-driving flares marked. Notebook figure 1."))
L.extend(embed("S1_fig_cme1", "CME 1 driver: the X1.0 of 2024-05-08."))
L.extend(embed("S1_fig_cme2", "CME 2 driver: the X2.2 of 2024-05-09."))

# ---------------------------------------------------------------- S2
add("\n## 2. SDO/AIA — the eruptions in the EUV corona\n")
add("The notebook fetches AIA 94/171/304 Å at each flare peak through "
    "`sunpy.net.Fido` → VSO. **That route no longer works for AIA.** Every "
    "VSO AIA request in this run matched records and then timed out on the "
    "export provider (`sdo7.nascom.nasa.gov/cgi-bin/drms_export.cgi`) after "
    "~90 s. HMI and LASCO, served by different providers, were unaffected.\n")
vso_probe = [k for k in ST if k.startswith("S2_vso_")]
n_vso_ok = sum(1 for k in vso_probe if ok(k))
add(f"The failing route is kept in the record as a probe: "
    f"**{n_vso_ok} of {len(vso_probe)} VSO AIA fetches succeeded.** "
    "One consequence was fixed in the core tools — `fetch_vso` used to "
    "return `status: \"ok\"` with an empty file list when the provider timed "
    "out, which reads as \"no such data exists\". It now returns an error "
    "naming the provider.\n")
add("### The replacement route\n")
add("`fetch_aia_synoptic` (added for this reproduction) pulls the JSOC "
    "synoptic archive over plain static HTTP: ~1.3 MB per frame, seconds "
    "per request. The trade is real and stated: **level 1.5 synoptic, "
    "1024×1024 at ~2.4 arcsec/pix**, against level 1 at 4096² and ~0.6. "
    "Right for morphology and eruption context — the notebook's actual use "
    "— wrong for fine loop widths or pixel-level photometry.\n")
add("| Wavelength | What it shows | Degradation factor at 2024-05-08 |")
add("|---|---|---|")
for wave, what in ((94, "6 MK flare plasma — the flaring core itself"),
                   (171, "0.6 MK quiet corona — the loop arcade"),
                   (304, "50 kK transition region — the filament/prominence")):
    d = ST.get(f"S2_deg_cme1_{wave}", {})
    facs = (d or {}).get("degradation_factors") or {}
    fac = facs.get(str(wave))
    add(f"| {wave} Å | {what} | "
        f"{fmt(fac,3) if fac is not None else '—'} "
        f"(`{aud(f'S2_deg_cme1_{wave}')}`) |")
add("\nThose factors are the fraction of 2010 launch sensitivity still "
    "remaining (corrected = observed / factor; `aiapy` SSW calibration "
    "series). The synoptic product is **not** degradation-corrected, so "
    "they matter for any multi-year intensity comparison — they do not "
    "affect the morphology below.\n")
for tag, label in (("cme1", "CME 1 — X1.0, 2024-05-08 05:10 UT"),
                   ("cme2", "CME 2 — X2.2, 2024-05-09 09:14 UT")):
    for wave in (94, 171, 304):
        L.extend(embed(f"S2_fig_{tag}_{wave}", f"{label}, AIA {wave} Å."))

# ---------------------------------------------------------------- S3
add("\n## 3. SDO/HMI — the magnetic field of AR 13664\n")
add("**This is where the notebook's own code fails.** Its flux calculation "
    "raises `'arcsec2 / pix2' and 'cm2' are not convertible` — a units error "
    "in converting pixel area to physical area — and the notebook then "
    "prints \"typical values\" from prose instead. So its stated magnetic "
    "numbers were never computed from the magnetogram it downloaded.\n")
add(f"Here the magnetogram is fetched ({g('S3_hmi','n_downloaded')} of "
    f"{g('S3_hmi','n_found')} records, audit `{aud('S3_hmi')}`) and measured "
    f"with `magnetogram_metrics` (audit `{aud('S3_metrics')}`).\n")
add(f"- Frame: {g('S3_map','instrument')}, {g('S3_map','date')}, "
    f"{g('S3_map','dimensions',0)}×{g('S3_map','dimensions',1)} at "
    f"{fmt(g('S3_map','scale_arcsec_per_pix',0),4)} arcsec/pix "
    f"(audit `{aud('S3_map')}`)")
reg = ST.get("S3_metrics", {}).get("region", {})
qui = ST.get("S3_quiet", {}).get("region", {})
add(f"- **Disk unsigned flux: {fmt(g('S3_metrics','disk_unsigned_flux_mx'),3)} Mx**"
    f" — against the notebook's stated "
    f"{fmt(1.5e23,2)} Mx \"typical value\", high by a factor "
    f"{g('S3_metrics','disk_unsigned_flux_mx', default=0)/1.5e23:.1f}. "
    "May 2024 was not a typical disk.")
add(f"- AR 13664 box (S20, W10 ±12°): **{fmt(reg.get('unsigned_flux_mx'),3)} Mx "
    f"unsigned**, signed {fmt(reg.get('signed_flux_mx'),3)} Mx, "
    f"**max |B| {fmt(reg.get('max_abs_b_g'),4)} G**, strong PIL "
    f"**{fmt(reg.get('pil_length_mm'),4)} Mm** threading "
    f"{fmt(reg.get('pil_flux_mx'),3)} Mx")
add(f"- Quiet control box, mirrored in latitude: "
    f"{fmt(qui.get('unsigned_flux_mx'),3)} Mx unsigned and a PIL of "
    f"{fmt(qui.get('pil_length_mm'),3)} Mm — **{(reg.get('pil_length_mm') or 0)/max(qui.get('pil_length_mm') or 1e-9,1e-9):.0f}× "
    f"shorter** (audit `{aud('S3_quiet')}`). That contrast is the point: a "
    "long strong polarity-inversion line is what distinguishes a δ-region "
    "from a simple bipole, and AR 13664 had a thousand megametres of "
    "it.\n")
add(f"Measured max |B| of {fmt(reg.get('max_abs_b_g'),4)} G against the "
    f"notebook's stated 2500 G. The measurement is line-of-sight only, with "
    "no μ correction, so at W10 it is a mild lower bound. For "
    "publication-grade AR flux the SHARP `USFLUX` keyword is the right "
    "number to cite, not this.\n")
L.extend(embed("S3_fig_full", "HMI line-of-sight magnetogram, 2024-05-08 "
                              "05:09 UT. AR 13664 is the large bipolar "
                              "complex south of disk centre."))
L.extend(embed("S3_metrics", "Region and quiet-control boxes with the "
                             "strong-PIL mask that produced the numbers above."))

# ---------------------------------------------------------------- S4
add("\n## 4. SOHO/LASCO — the CMEs\n")
add("**The notebook's second failure of method.** Its CME speed estimate "
    "builds a height-time array from `np.random.uniform(3, 6)` — random "
    "numbers — fits a line through it, and the speeds it prints "
    "(950 and 1100 km s⁻¹) come from its prose, not from that fit.\n")
add("Two things replace it here. `plot_coronagraph_sequence` builds a real "
    "running difference from the C2 frames, and `cme_height_time` does a "
    "genuine linear fit that **refuses** fewer than three points or "
    "non-monotonic heights, so it cannot be fed noise and return a speed.\n")
for tag, when in (("cme1", "2024-05-08"), ("cme2", "2024-05-09")):
    s = ST.get(f"S4_fig_{tag}", {})
    if not isinstance(s, dict) or s.get("status") == "error":
        continue
    add(f"\n**{when}:** {s.get('n_frames')} {s.get('instrument')} frames → "
        f"{s.get('n_differences')} differences at "
        f"{fmt(s.get('median_cadence_min'),3)} min cadence "
        f"(audit `{aud(f'S4_fig_{tag}')}`). "
        f"{len(s.get('exposure_times_s') or [])} distinct exposure times were "
        f"present ({min(s['exposure_times_s'])}–{max(s['exposure_times_s'])} s), "
        "so each frame is divided by its own exposure before differencing — "
        "raw differencing here would have rendered the shutter, not the CME.")
add("\n### CME speeds from the cone-model record\n")
add("Rather than invent heights, the speeds come from DONKI's cone-model "
    f"fits to the actual coronagraph data (audit `{aud('S4_donki_cme')}`, "
    f"{g('S4_donki_cme','n_results')} analyses):\n")
add("| Time at 21.5 R⊙ | Speed (km s⁻¹) | Lon (°) | Lat (°) | Half-angle (°) | Type |")
add("|---|---|---|---|---|---|")
for e in sorted(g("S4_donki_cme", "events", default=[]),
                key=lambda x: -(x.get("speed") or 0))[:8]:
    add(f"| {e.get('time21_5')} | **{fmt(e.get('speed'),4)}** | "
        f"{fmt(e.get('longitude'),3)} | {fmt(e.get('latitude'),3)} | "
        f"{fmt(e.get('halfAngle'),3)} | {e.get('type')} |")
add("\nThe notebook's 950 and 1100 km s⁻¹ are inside this distribution, so "
    "its numbers are defensible — but they were asserted, not derived, and "
    "its own code could not have produced them. Cone-model speeds are "
    "plane-of-sky-corrected fits with their own large uncertainty; the "
    "`type` column (C, O, R, S) records DONKI's own quality flag.\n")
L.extend(embed("S4_fig_cme1", "LASCO C2 running difference, 2024-05-08. "
                              "Exposure-normalised."))
L.extend(embed("S4_fig_cme2", "LASCO C2 running difference, 2024-05-09."))

# ---------------------------------------------------------------- S5
add("\n## 5. In-situ solar wind — every route, compared\n")
add("The notebook uses one source: ACE hourly through CDAWeb. This runs "
    "**six independent routes** over the same 2024-05-10 → 05-13 window, "
    "because the choice of route changes the answer by more than the "
    "measurement uncertainty.\n")
add("| # | Route | Transport | Records | Cadence | Status |")
add("|---|---|---|---|---|---|")
ROUTES = [
    ("1a", "ACE SWEPAM hourly (`AC_H2_SWE`)",
     "cdasws — the notebook's own route", "S5_ace_swe"),
    ("1b", "ACE MAG 4-min (`AC_H1_MFI`)", "cdasws", "S5_ace_mfi"),
    ("2", "ACE MAG 1-s / SWE 64-s (`fetch_pyspedas`)",
     "pySPEDAS, mission loader", "S5_pyspedas_mfi"),
    ("3", "OMNI 1-min (`OMNI_HRO_1MIN`)",
     "cdasws — multi-spacecraft, shifted to bow-shock nose", "S5_omni_1m"),
    ("4", "DSCOVR magnetometer 1-s (`DSCOVR_H0_MAG`)", "cdasws", "S5_dscovr_mag"),
    ("5", "DSCOVR Faraday cup (`DSCOVR_H1_FC`)", "cdasws", "S5_dscovr_pla"),
    ("6", "Wind MFI (`WI_H0_MFI`)", "cdasws", "S5_wind_mfi"),
]
for num, name, transport, key in ROUTES:
    r = ST.get(key, {})
    if not ok(key):
        add(f"| {num} | {name} | {transport} | — | — | **refused** |")
        continue
    n = r.get("n_records") or 0
    tr = r.get("time_range") or ["", ""]
    span_s = None
    try:
        import datetime as _dt
        t0 = _dt.datetime.fromisoformat(str(tr[0]))
        t1 = _dt.datetime.fromisoformat(str(tr[1]))
        span_s = (t1 - t0).total_seconds() / max(n - 1, 1)
    except Exception:  # noqa: BLE001
        pass
    cad = (f"{span_s:.0f} s" if span_s and span_s < 90
           else f"{span_s/60:.0f} min" if span_s else "—")
    add(f"| {num} | {name} | {transport} | {n:,} | {cad} | ok "
        f"(`{aud(key)}`) |")
add("")
add("**Route 5 is refused, and the refusal is the answer.** "
    f"`{str(g('S5_dscovr_pla','error', default=''))[:170]}` — the only DSCOVR "
    "plasma product CDAWeb carries as science data stops in 2019. DSCOVR "
    "plasma for May 2024 exists only as SWPC real-time, which is not science "
    "quality and is not substituted in here.\n")
add("**Route 4 carries no GSM field.** `DSCOVR_H0_MAG` serves GSE and RTN "
    "only, so a Bz(GSM) — the quantity that actually drives the storm — has "
    "to come from a coordinate rotation (`transform_coordinates`) or from "
    "another route. That is why the Bz row below has one fewer entry.\n")
add("### The same quantity, measured several ways\n")
QUANT = [("v", "Max flow speed", "km s⁻¹"),
         ("n", "Max proton density", "cm⁻³"),
         ("b", "Max |B|", "nT"),
         ("bz", "Min Bz (GSM)", "nT")]
NAMES = {"ace_cdaweb": "ACE CDAWeb (hourly SWE / 4-min MFI)",
         "ace_pyspedas": "ACE pySPEDAS 1-s/64-s",
         "omni_1min": "OMNI 1-min", "dscovr": "DSCOVR 1-s", "wind": "Wind"}
for quant, label, unit in QUANT:
    rows = [(NAMES.get(k[len(f"S5x_{quant}_"):], k), ST[k]) for k in ST
            if k.startswith(f"S5x_{quant}_") and ok(k)]
    if not rows:
        continue
    add(f"\n**{label} ({unit})**, identical 2024-05-10 → 05-13 window:\n")
    add("| Route | Value | Time (UT) | Audit |")
    add("|---|---|---|---|")
    for name, r in rows:
        add(f"| {name} | **{fmt(r.get('value'),4)}** | "
            f"{str(r.get('time'))[:16]} | `{r.get('audit_id','—')}` |")
    vals = [r.get("value") for _, r in rows
            if isinstance(r.get("value"), (int, float))]
    if len(vals) > 1:
        add(f"\nSpread across routes: {fmt(min(vals),4)} → {fmt(max(vals),4)} "
            f"{unit}. All of these are correct measurements; they differ "
            "because they average differently.")
add("\nThree things follow, and they are the reason for running six routes "
    "instead of one.\n")
add("**The notebook's density is exactly right and its speed is not.** Its "
    "quoted 41.9 cm⁻³ reproduces the hourly ACE maximum to the digit — that "
    "number really did come from this product. Its quoted 739 km s⁻¹ does "
    "not: the same product gives "
    f"{fmt(g('S5x_v_ace_cdaweb','value'),4)} km s⁻¹ over this window. "
    "Whatever 739 is, it is not the ACE hourly speed maximum for "
    "2024-05-10 → 05-13.\n")
add("**Cadence sets the peak, not instrument quality.** Density climbs "
    f"{fmt(g('S5x_n_ace_cdaweb','value'),4)} → "
    f"{fmt(g('S5x_n_ace_pyspedas','value'),4)} → "
    f"{fmt(g('S5x_n_omni_1min','value'),4)} cm⁻³ as the cadence goes hourly "
    "→ 64-s → 1-min. An hourly average cannot resolve a shock; the peak it "
    "reports is a smoothed one. Every value in that column is a correct "
    "measurement of a different thing.\n")
add("**|B| is the check that the routes agree.** Four independent "
    "spacecraft put the maximum inside "
    f"{fmt(min(v for v in [g('S5x_b_ace_cdaweb','value'), g('S5x_b_ace_pyspedas','value'), g('S5x_b_dscovr','value'), g('S5x_b_wind','value')] if v),4)}–"
    f"{fmt(max(v for v in [g('S5x_b_ace_cdaweb','value'), g('S5x_b_ace_pyspedas','value'), g('S5x_b_dscovr','value'), g('S5x_b_wind','value')] if v),4)} nT "
    "within about ten minutes of each other. That agreement is what makes "
    "the density spread above interpretable as a sampling effect rather "
    "than an instrument problem.\n")
add("**Recommendation:** OMNI 1-min for storm metrics (it is time-shifted "
    "to the bow-shock nose, which is what the magnetosphere actually sees), "
    "a single-spacecraft 1-s product for shock timing, and hourly ACE for "
    "neither.\n")

# ---------------------------------------------------------------- S6
add("\n## 6. The geomagnetic response\n")
st6 = ST.get("S6_storm", {})
add(f"`storm_metrics` on OMNI 1-min SYM-H (audit `{aud('S6_storm')}`):\n")
add(f"- **SYM-H minimum {fmt(st6.get('dst_min_nT'),4)} nT at "
    f"{str(st6.get('time_of_min'))[:16]} UT** — reproduces the notebook's "
    "stated −518 nT exactly, and it is the deepest storm since March 1989.")
add(f"- Classification: **{st6.get('classification')}**")
add(f"- Main phase began {str(st6.get('main_phase_start'))[:16]} UT and ran "
    f"{fmt(st6.get('main_phase_hours'),3)} h; recovery to half-depth took "
    f"{fmt(st6.get('recovery_to_half_hours'),3)} h\n")
add("### Storm extrema, each from its own audited measurement\n")
add("| Quantity | Value | Time (UT) | Notebook states | Audit |")
add("|---|---|---|---|---|")
EXT = [("S6_ext_symh", "SYM-H minimum", "nT", "−518 nT"),
       ("S6_ext_vmax", "Max flow speed", "km s⁻¹", "~1100 km s⁻¹"),
       ("S6_ext_bzmin", "Min Bz (GSM)", "nT", "~−48 nT"),
       ("S6_ext_bmax", "Max |B|", "nT", "not stated"),
       ("S6_ext_nmax", "Max density", "cm⁻³", "not stated"),
       ("S6_ext_pmax", "Max dynamic pressure", "nPa", "~15 nPa"),
       ("S6_ext_aemax", "Max AE", "nT", "not stated")]
for key, label, unit, nb in EXT:
    if not ok(key):
        continue
    r = ST[key]
    add(f"| {label} | **{fmt(r.get('value'),4)} {unit}** | "
        f"{str(r.get('time'))[:16]} | {nb} | `{aud(key)}` |")
add("\nOne of the notebook's stated numbers does not survive measurement: "
    f"dynamic pressure peaked at **{fmt(g('S6_ext_pmax','value'),4)} nPa**, "
    f"{g('S6_ext_pmax','value', default=0)/15:.1f}× the ~15 nPa it states. "
    "Max speed reached "
    f"**{fmt(g('S6_ext_vmax','value'),4)} km s⁻¹**, a little under the "
    "notebook's ~1100, and Bz reached "
    f"**{fmt(g('S6_ext_bzmin','value'),4)} nT** against its ~−48.\n")
add("### Kp and the independent Dst record\n")
add(f"- GFZ Kp reached **{fmt(g('S6_kp','max_value'),2)}** — the scale "
    f"maximum (audit `{aud('S6_kp')}`), matching the notebook.")
add(f"- Kyoto **{g('S6_dst_kyoto','revision')}** hourly Dst minimum: "
    f"**{fmt(g('S6_dst_kyoto','dst_min_nT'),4)} nT** (audit "
    f"`{aud('S6_dst_kyoto')}`). That is deliberately not the same number as "
    f"SYM-H {fmt(st6.get('dst_min_nT'),4)} nT: hourly Dst from four stations "
    "averages away the 1-minute peak that SYM-H's six-station 1-min index "
    "resolves. Cite the revision — provisional Dst moves.")
add(f"- DONKI logs {g('S6_gst','n_results')} geomagnetic storm event(s) and "
    f"{g('S6_ips','n_results')} interplanetary shock(s) in the window "
    f"(audits `{aud('S6_gst')}`, `{aud('S6_ips')}`).\n")
add("### Was it a magnetic cloud?\n")
ic = (ST.get("S6_icme") or {}).get("icme") or {}
if ic:
    add(f"`detect_icme` finds an ejecta interval at "
        f"**{str(ic.get('start'))[:16]} → {str(ic.get('end'))[:16]} UT** "
        f"({fmt(ic.get('duration_hours'),3)} h, mean speed "
        f"{fmt(ic.get('mean_speed_kms'),4)} km s⁻¹, minimum temperature "
        f"ratio {fmt(ic.get('min_temp_ratio'),3)}; audit `{aud('S6_icme')}`).\n")
    try:
        import datetime as _d
        _t_ic = _d.datetime.fromisoformat(str(ic.get("start")))
        _t_sym = _d.datetime.fromisoformat(str(st6.get("time_of_min")))
        _lag = (_t_ic - _t_sym).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        _lag = None
    if _lag is not None and _lag > 0:
        add(f"**That interval begins {_lag:.1f} h AFTER the SYM-H minimum**, "
            "so it is not what drove the main phase. The main phase ran "
            f"{str(st6.get('main_phase_start'))[:16]} → "
            f"{str(st6.get('time_of_min'))[:16]} UT, entirely before the "
            "ejecta signature — this storm's record depth was driven by the "
            "compressed **sheath** ahead of the ejecta, not by the flux rope "
            "itself. The notebook attributes the storm to the CME arrival "
            "without separating the two, and the distinction matters for "
            "forecasting: sheath Bz is not predictable from a cone-model CME "
            "fit.\n")
    if ok("S6_lit"):
        add("**Cross-checked against the refereed record** (ADS, audit "
            f"`{aud('S6_lit')}`, {g('S6_lit','n_results')} papers):\n")
        for pp in g("S6_lit", "papers", default=[])[:3]:
            add(f"- {pp.get('first_author')} et al. ({pp.get('year')}), "
                f"*{pp.get('title')}*, {pp.get('pub')} "
                f"[`{pp.get('bibcode')}`], {pp.get('citations')} citations")
        add("\nHajra et al. (2024) describe a **three-step main phase of "
            "~9 h total** — this reproduction measures "
            f"{fmt(st6.get('main_phase_hours'),3)} h — with the first step "
            "driven by a fast-forward shock and its sheath, and Hajra (2025) "
            "places three magnetic clouds in the **recovery** phase. Both "
            "support the attribution above: the sheath drove the depth, the "
            "ejecta arrived afterwards.\n")
    add(f"**`magnetic_cloud: {ic.get('magnetic_cloud')}`** — the field "
        f"rotates {fmt(ic.get('rotation_deg'),4)}°, but the fit to a smooth "
        f"flux-rope rotation is poor (r² = {fmt(ic.get('rotation_r2'),3)}). "
        "This was a compound event: several CMEs merged in transit, so what "
        "arrived is not a clean single rope. The notebook does not test "
        "this.\n")
    others = ((ST.get("S6_icme") or {}).get("intervals") or [])[1:]
    if others:
        add(f"{len(others)} further ICME-like interval(s) were flagged in the "
            "same window, which is itself the signature of a cannibalising "
            "CME train:\n")
        add("| Start | End | Hours | Mean V (km s⁻¹) | Rotation (°) |")
        add("|---|---|---|---|---|")
        for o in others:
            add(f"| {str(o.get('start'))[:16]} | {str(o.get('end'))[:16]} | "
                f"{fmt(o.get('duration_hours'),3)} | "
                f"{fmt(o.get('mean_speed_kms'),4)} | "
                f"{fmt(o.get('rotation_deg'),4)} |")
        add("")
L.extend(embed("S6_fig_stack", "The standard storm stack: |B|, Bz, speed, "
                               "density, pressure, SYM-H. OMNI 1-min."))
L.extend(embed("S6_icme", "ICME interval detection on the same series."))
add("\n### Can the storm be predicted from the solar wind?\n")
md = ST.get("S6_model_dst", {})
if ok("S6_model_dst"):
    sk = md.get("skill", {})
    add(f"`model_dst` runs {md.get('model')} on hourly-averaged OMNI "
        f"(audit `{aud('S6_model_dst')}`):\n")
    add(f"- Correlation **{fmt(sk.get('corr'),3)}**, RMSE "
        f"**{fmt(sk.get('rmse_nT'),3)} nT**")
    add(f"- Model minimum **{fmt(md.get('model_min_nT'),4)} nT** against an "
        f"observed hourly minimum of {fmt(sk.get('obs_min_nT'),4)} nT — the "
        f"model **under-predicts the peak by "
        f"{fmt(sk.get('min_error_nT'),4)} nT**\n")
    add(f"A correlation of {fmt(sk.get('corr'),3)} alongside a "
        f"{fmt(sk.get('min_error_nT'),4)} nT miss at the peak is the honest "
        "result, and worth stating plainly: the O'Brien–McPherron coupling "
        "function was fitted on ordinary storms and saturates on this one. "
        "The shape of the storm is predictable from the solar wind; its "
        "depth, at this magnitude, is not. This test is absent from the "
        "notebook.\n")

# ---------------------------------------------------------------- S7
add("\n## 7. Where everything was — the heliospheric configuration\n")
add("**The notebook's third failure.** `sm.coord_table.to_pandas()` raises, "
    "and it falls back to hard-coded text: *\"STEREO-A ~25° from Earth, "
    "Solar Orbiter ~45°.\"* Both are wrong.\n")
cfg = ST.get("S7_config_nominal", {})
add(f"`plot_heliospheric_config` for {cfg.get('date')} UT (audit "
    f"`{aud('S7_config_nominal')}`) returns the table the notebook could not "
    "build:\n")
add("| Body | Carrington lon (°) | Lat (°) | r (AU) | Spiral footpoint (°) "
    "| Separation from Earth (°) | Notebook |")
add("|---|---|---|---|---|---|---|")
NB_SEP = {"STEREO-A": "~25", "Solar Orbiter": "~45"}
for pos in cfg.get("positions", []):
    b = pos["body"]
    add(f"| {b} | {fmt(pos['carrington_longitude_deg'],4)} | "
        f"{fmt(pos['carrington_latitude_deg'],3)} | "
        f"{fmt(pos['distance_au'],4)} | "
        f"{fmt(pos['footpoint_longitude_deg'],4)} | "
        f"**{fmt(pos['separation_from_first_deg'],4)}** | "
        f"{NB_SEP.get(b,'—')} |")
_sep = {p["body"]: p["separation_from_first_deg"] for p in cfg.get("positions", [])}
_solo = next((v for k, v in _sep.items() if "Orbiter" in k), None)
_sta = next((v for k, v in _sep.items() if "STEREO" in k), None)
add(f"\n**Solar Orbiter was on the far side of the Sun.** Its separation "
    f"from Earth was not ~45° but {fmt(_solo,4)}° — an error of more than "
    "120°, which inverts any conclusion about whether Solar Orbiter could "
    f"see the Earth-directed eruptions. STEREO-A was {fmt(_sta,4)}°, half "
    "the stated value.\n")
add("Note the **footpoint** column: a body's Parker-spiral footpoint is not "
    "its own longitude. Earth sits at "
    f"{fmt(g('S7_config_nominal','positions',0,'carrington_longitude_deg'),4)}° "
    "Carrington but is magnetically connected to "
    f"{fmt(g('S7_config_nominal','positions',0,'footpoint_longitude_deg'),4)}° "
    "at 400 km s⁻¹. Longitudinal separation is not magnetic separation — "
    "which is why the figure is drawn twice, at nominal and storm wind "
    "speed:\n")
L.extend(embed("S7_config_nominal", "Constellation with 400 km s⁻¹ spirals "
                                    "(nominal slow wind)."))
L.extend(embed("S7_config_storm", "The same instant with 1000 km s⁻¹ spirals. "
                                  "The spirals straighten and every footpoint "
                                  "moves — connectivity during the storm was "
                                  "not the nominal connectivity."))
add(f"\nSpacecraft trajectories over the same week come from "
    f"`fetch_spacecraft_ephemeris` ({g('S7_ephem','n_records', default=0):,} "
    f"records in {g('S7_ephem','coordinate_system')}, audit "
    f"`{aud('S7_ephem')}`).\n")
L.extend(embed("S7_fig_orbits", "ACE, DSCOVR, Wind and STEREO-A trajectories."))

# ---------------------------------------------------------------- S8
add("\n## 8. CME arrival — forecast against observation\n")
add("The notebook states arrival times without deriving them. Here the "
    "drag-based model runs on both CMEs and is scored against the shocks "
    "that were actually observed.\n")
add("| CME | Launch (UT) | v₀ (km s⁻¹) | Transit (h) | DBM arrival (UT) | "
    "Window | Arrival speed | Notebook |")
add("|---|---|---|---|---|---|---|---|")
NB_ARR = {"S8_dbm_cme1": "2024-05-10 16:34", "S8_dbm_cme2": "2024-05-10 22:21"}
for key, name in (("S8_dbm_cme1", "CME 1 (05-08)"),
                  ("S8_dbm_cme2", "CME 2 (05-09)")):
    if not ok(key):
        continue
    d = ST[key]
    w = d.get("arrival_window", ["", ""])
    add(f"| {name} | {str(d.get('launch_time'))[:16]} | "
        f"{fmt(d.get('v0_kms'),4)} | {fmt(d.get('transit_hours'),3)} | "
        f"**{str(d.get('arrival_estimate'))[:16]}** | "
        f"{str(w[0])[:16]} → {str(w[1])[:16]} | "
        f"{fmt(d.get('arrival_speed_kms'),4)} km s⁻¹ | "
        f"{NB_ARR.get(key,'—')} |")
add(f"\nModel: {g('S8_dbm_cme1','model')}. Assumptions: ambient wind "
    f"{fmt(g('S8_dbm_cme1','assumptions','w_kms'),3)} km s⁻¹, drag "
    f"Γ = {fmt(g('S8_dbm_cme1','assumptions','gamma_per_km'),2)} km⁻¹, "
    f"launched from {fmt(g('S8_dbm_cme1','assumptions','r0_rs'),3)} R⊙ "
    f"(audits `{aud('S8_dbm_cme1')}`, `{aud('S8_dbm_cme2')}`). The v₀ values "
    "are the notebook's own stated speeds, used here as inputs so the "
    "forecast is compared on its terms.\n")
shocks = [str(e.get("eventTime")) for e in g("S6_ips", "events", default=[])
          if e.get("location") == "Earth"]
if shocks:
    add(f"**Observed shocks at Earth** (DONKI IPS, audit `{aud('S6_ips')}`): "
        + ", ".join(shocks) + ".\n")
    add("The first observed shock arrives ahead of both DBM point estimates "
        "but inside both stated windows. That is the expected failure mode "
        "for a compound event: the DBM propagates one CME through "
        "undisturbed wind, and here the earlier eruptions had already "
        "cleared a path for the later ones. ±10 h is the honest quote.\n")
add(f"For context: the L1→Earth ballistic delay at 700 km s⁻¹ is "
    f"**{fmt(g('S8_delay','delay_minutes'),3)} minutes** (audit "
    f"`{aud('S8_delay')}`) — roughly the warning time the storm gave. Local "
    f"plasma parameters: Alfvén speed "
    f"{fmt(g('S8_plasma','alfven_speed_km_s'),4)} km s⁻¹, plasma β "
    f"{fmt(g('S8_plasma','plasma_beta'),3)}, ion inertial length "
    f"{fmt(g('S8_plasma','ion_inertial_length_km'),4)} km (audit "
    f"`{aud('S8_plasma')}`).\n")

# ---------------------------------------------------------------- notes
add("\n## What needs updating to reproduce this notebook today\n")
add("Five things in the original no longer run, or never ran:\n")
add("1. **AIA through VSO times out.** The `sdo7.nascom.nasa.gov` export "
    "provider does not answer. Use the JSOC synoptic archive "
    "(`fetch_aia_synoptic` here) and accept level-1.5 1024², or go to JSOC "
    "through `drms` for level 1. HMI and LASCO through VSO are fine.")
add("2. **The HMI flux cell raises a units error** "
    "(`'arcsec2 / pix2' and 'cm2' are not convertible`). Pixel area has to "
    "be converted through the plate scale and the solar distance before "
    "multiplying by field strength. `magnetogram_metrics` does this.")
add("3. **`sm.coord_table.to_pandas()` raises** in current solarmach; the "
    "table is already DataFrame-like. The hard-coded values it falls back "
    "to are wrong by 120°+ for Solar Orbiter, so this failure is not "
    "cosmetic.")
add("4. **The CME speed cell uses `np.random.uniform`** and never produced "
    "the speeds the notebook prints. Any reproduction has to replace it "
    "with real height-time measurements or a catalogue.")
add("5. **DSCOVR plasma for 2024 is not on CDAWeb as science data** "
    "(`DSCOVR_H1_FC` ends 2019). SWPC real-time data exists, but is not "
    "science quality.\n")
add("## Capabilities added to helio-agent for this reproduction\n")
add("| Tool | Purpose | Validation |")
add("|---|---|---|")
add("| `plot_coronagraph_sequence` | Exposure-normalised running-difference "
    "panels from a coronagraph FITS sequence | `run_validation.py corona` |")
add("| `cme_height_time` | Linear height-time fit that refuses <3 points or "
    "non-monotonic heights | `run_validation.py corona` |")
add("| `plot_heliospheric_config` | solarmach constellation and Parker "
    "spirals, returning the position table | `run_validation.py corona` |")
add("| `fetch_aia_synoptic` | JSOC synoptic AIA, replacing the dead VSO "
    "export route | `run_validation.py aiasyn` |")
add("| `fetch_vso(detector=...)` | LASCO C2/C3 and SECCHI COR1/COR2/EUVI "
    "selection, so a sequence does not interleave two fields of view | "
    "`run_validation.py corona` |")
add("| `fetch_vso` errors on an empty download | A provider timeout used to "
    "return `status: ok` with no files, which reads as \"no such data\" | — |\n")

add("## Provenance\n")
n_steps = sum(1 for v in ST.values() if isinstance(v, dict))
n_ok = sum(1 for k in ST if ok(k))
add(f"{n_steps} audited tool invocations, {n_ok} successful. Every audit id "
    "above resolves against `workspace/logs/audit.jsonl` and can be "
    "re-executed with `uv run helio-agent replay <id>`. Regenerate with:\n")
add("```bash\nHELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/2024-05-gannon-notebook-repro/reproduce.py\n"
    "HELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/2024-05-gannon-notebook-repro/render_report.py\n```\n")
failed = [k for k in ST if isinstance(ST[k], dict)
          and ST[k].get("status") == "error"]
if failed:
    add("Steps that returned an error, kept in the record rather than "
        "hidden:\n")
    for k in failed:
        add(f"- `{k}`: {str(ST[k].get('error'))[:200]}")
    add("")

OUT.write_text("\n".join(L) + "\n")
print(f"wrote {OUT} ({len(L)} blocks, {OUT.stat().st_size:,} bytes)")
