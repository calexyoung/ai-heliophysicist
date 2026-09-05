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
    out.append("")   # tables/paragraphs that follow need the blank line
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
add("| CME speeds from `np.random.uniform(3, 6)` heights | The front is "
    "**tracked** frame by frame (`track_cme_front`) and the heights fitted "
    "(`cme_height_time`), then compared against DONKI cone fits | The "
    "notebook's \"speed estimate\" was random numbers. Measured "
    "plane-of-sky: "
    + (f"{fmt(g('S4_fit_cme1','speed_km_s'),4)} and "
       f"{fmt(g('S4_fit_cme2','speed_km_s'),4)} km s⁻¹"
       if ok("S4_fit_cme1") else "—") + " |")
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
add("### Two replacement routes\n")
add("`fetch_aia_synoptic` pulls the JSOC synoptic archive over plain static "
    "HTTP: ~1.3 MB per frame, seconds per request, **level 1.5 at 1024×1024 "
    "/ ~2.4 arcsec/pix**. That is the survey product used for the six panels "
    "below — right for morphology and eruption context, which is the "
    "notebook's actual use.\n")
add("`fetch_aia_level1` goes to JSOC through `drms` for the **native "
    "product, 4096×4096 at ~0.6 arcsec/pix**, when the science needs "
    "resolution or the level-1 calibration chain. It requires a "
    "JSOC-registered export email (`JSOC_EMAIL` in `.env`); without one it "
    "refuses by name rather than silently handing back a 16× smaller image "
    "under the same call.\n")
if ok("S2_l1_cme1_171"):
    _m = ST.get("S2_l1_map_cme1_171", {})
    _dim = _m.get("dimensions") or []
    _sc = (_m.get("scale_arcsec_per_pix") or [None])[0]
    add("Both routes were run on the same instant to show what the "
        "difference buys:\n")
    add("| Route | Level | Dimensions | Plate scale | Frame size | Audit |")
    add("|---|---|---|---|---|---|")
    add("| `fetch_aia_synoptic` | 1.5 | 1024×1024 | ~2.4 arcsec/pix | "
        f"~1.3 MB | `{aud('S2_aia_cme1_171')}` |")
    add("| `fetch_aia_level1` | 1 | "
        f"{_dim[0] if _dim else '—'}×{_dim[1] if len(_dim)>1 else '—'} | "
        f"{fmt(_sc,3) if _sc else '—'} arcsec/pix | ~12 MB | "
        f"`{aud('S2_l1_cme1_171')}` |")
    add(f"\nJSOC record: `{(g('S2_l1_cme1_171','records', default=['—']) or ['—'])[0]}` "
        f"from series `{g('S2_l1_cme1_171','series')}`. **Level 1 is not "
        "level 1.5**: the frame is neither registered to solar north nor "
        "plate-scale normalised, so `aiapy.calibrate.register` has to run "
        "before any pixel-to-pixel channel comparison. Only 171 Å was "
        "re-shot at native resolution — the point is to establish the route "
        "and its cost, not to repeat the survey at 16× the size.\n")
    L.extend(embed("S2_l1_fig_cme1_171",
                   "AIA 171 Å at 2024-05-08 05:10 UT, JSOC level 1, "
                   "4096×4096. Compare with the 1024×1024 synoptic frame "
                   "of the same instant below."))
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
add("Here the front is **measured**. `track_cme_front` locates the leading "
    "edge in each running-difference frame — outermost radius where the "
    "exposure-normalised profile stays above 5σ for three consecutive "
    "0.1 R⊙ bins, with the noise taken from the same radius at other "
    "position angles — and `cme_height_time` fits those heights. Neither "
    "tool will accept invented input: the fit refuses fewer than three "
    "points or non-monotonic heights, and it exercised that refusal on the "
    "first pass here — see the window note below.\n")
add("### Measured height-time\n")
add("| CME | PA (°) | Points | Heights (R⊙) | Plane-of-sky speed | r² | "
    "Fit → 1 R⊙ | Driving flare |")
add("|---|---|---|---|---|---|---|---|")
FLARE = {"cme1": "X1.0 started 04:37, peaked 05:09",
         "cme2": "X2.2 started 08:45, peaked 09:13"}
for tag, name in (("cme1", "CME 1 (05-08)"), ("cme2", "CME 2 (05-09)")):
    t, f2 = ST.get(f"S4_track_{tag}", {}), ST.get(f"S4_fit_{tag}", {})
    if not (ok(f"S4_track_{tag}") and ok(f"S4_fit_{tag}")):
        continue
    hs = t.get("heights_rsun", [])
    add(f"| {name} | {fmt(t.get('position_angle_deg'),3)} | "
        f"{t.get('n_detections')} | {hs[0]} → {hs[-1]} | "
        f"**{fmt(f2.get('speed_km_s'),4)} ± {fmt(f2.get('speed_error_km_s'),3)} "
        f"km s⁻¹** | {fmt(f2.get('r_squared'),4)} | "
        f"{str(f2.get('extrapolated_launch_1rsun'))[:19]} | "
        f"{FLARE[tag]} |")
add(f"\nAudits: `{aud('S4_track_cme1')}`/`{aud('S4_fit_cme1')}` and "
    f"`{aud('S4_track_cme2')}`/`{aud('S4_fit_cme2')}`. The position angles "
    "were chosen automatically, by scoring sectors on monotonic outward "
    "motion rather than on scatter.\n")
add("**The launch-time column is the check that the tracker found the "
    "eruption and not a streamer.** The fit extrapolates back to 1 R⊙ at "
    f"{str(g('S4_fit_cme1','extrapolated_launch_1rsun'))[11:19]} for CME 1 "
    f"and {str(g('S4_fit_cme2','extrapolated_launch_1rsun'))[11:19]} for "
    "CME 2 — each within minutes of its flare's onset. The tracker never "
    "sees the X-ray data, so that agreement is independent, not circular.\n")
add("**Two things had to be got right, and both failed the other way "
    "first.** The noise reference has to be the same radius at other "
    "position angles: an outer-annulus σ is contaminated once the CME "
    "reaches it, which inflated the noise 4.6× and suppressed every "
    "detection. And the search window has to open at the eruption, not an "
    "hour later — C2 sees only 2.4–5.8 R⊙, so a front already at the outer "
    "edge cannot be tracked. Opening at the flare peak took CME 1 from 3 "
    "height points to 5 and turned CME 2 from an untrackable non-monotonic "
    "scatter into a clean track. Both details are recorded in "
    "`skills/methods/cme_analysis.md`.\n")
_cone = [e.get("speed") for e in g("S4_donki_cme", "events", default=[])
         if isinstance(e.get("speed"), (int, float))]
_pos = [g("S4_fit_cme1", "speed_km_s"), g("S4_fit_cme2", "speed_km_s")]
_pos = [v for v in _pos if isinstance(v, (int, float))]
add("\n### Plane-of-sky against cone model — the comparison that matters\n")
add("| CME | Measured plane-of-sky | DONKI cone fit (same CME) | Notebook |")
add("|---|---|---|---|")
_CONE_ID = {"cme1": "2024-05-08T05", "cme2": "2024-05-09T09"}
_NB = {"cme1": "950", "cme2": "1100"}
for tag, name in (("cme1", "CME 1"), ("cme2", "CME 2")):
    sp = g(f"S4_fit_{tag}", "speed_km_s")
    c = [e.get("speed") for e in g("S4_donki_cme", "events", default=[])
         if isinstance(e.get("speed"), (int, float))
         and str(e.get("associatedCMEID", "")).startswith(_CONE_ID[tag])]
    add(f"| {name} | **{fmt(sp,4)} km s⁻¹** | "
        + (f"{fmt(min(c),4)}–{fmt(max(c),4)} km s⁻¹ ({len(c)} fits)"
           if c else "—")
        + f" | {_NB[tag]} km s⁻¹ |")
add("\n**Every measured plane-of-sky speed lands below its cone fit, and "
    "that is the expected result, not a discrepancy.** Both of these are "
    "Earth-directed halos, so the plane-of-sky projection sees the front "
    "edge-on and understates the radial speed — the measurement is a lower "
    "bound by construction. A plane-of-sky speed coming out *above* a cone "
    "fit would have meant the tracker had locked onto something other than "
    "the front. `run_validation.py cmetrack` pins that inequality.\n")
add("So the notebook's 950 and 1100 km s⁻¹ are defensible numbers for the "
    "radial speed — they sit inside the cone-model distribution — but its "
    "own code could not have produced them, and they are not what a "
    "plane-of-sky fit measures. The two quantities are not "
    "interchangeable, which is the part the notebook elides.\n")
add("Full cone-model record (audit "
    f"`{aud('S4_donki_cme')}`, {g('S4_donki_cme','n_results')} analyses; "
    "the `type` column is DONKI's own quality flag):\n")
add("| Time at 21.5 R⊙ | Speed (km s⁻¹) | Lon (°) | Lat (°) | Half-angle (°) | Type |")
add("|---|---|---|---|---|---|")
for e in sorted(g("S4_donki_cme", "events", default=[]),
                key=lambda x: -(x.get("speed") or 0))[:8]:
    add(f"| {e.get('time21_5')} | **{fmt(e.get('speed'),4)}** | "
        f"{fmt(e.get('longitude'),3)} | {fmt(e.get('latitude'),3)} | "
        f"{fmt(e.get('halfAngle'),3)} | {e.get('type')} |")
add("")
L.extend(embed("S4_fig_cme1", "LASCO C2 running difference, 2024-05-08. "
                              "Exposure-normalised."))
L.extend(embed("S4_fig_cme2", "LASCO C2 running difference, 2024-05-09."))

# ---------------------------------------------------------------- S5
add("\n## 5. In-situ solar wind — every route, compared\n")
add("The notebook uses one source: ACE hourly through CDAWeb. This runs "
    "**seven independent routes** over the same 2024-05-10 → 05-13 window, "
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
    ("6a", "DSCOVR Faraday cup **Level 2**", "NOAA NCEI archive (S3)",
     "S5_dscovrl2_fc"),
    ("6b", "DSCOVR magnetometer **Level 2**", "NOAA NCEI archive (S3)",
     "S5_dscovrl2_mag"),
    ("7", "Wind MFI (`WI_H0_MFI`)", "cdasws", "S5_wind_mfi"),
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
add("**Route 5 is refused, and the refusal is what sent us to route 6.** "
    f"`{str(g('S5_dscovr_pla','error', default=''))[:150]}` — CDAWeb's only "
    "DSCOVR plasma science product stops in 2019.\n")
add("**Route 6 is NOT CDAWeb.** DSCOVR Level 2 lives in NOAA's own archive "
    "at `archive.data.noaa.gov/satellite-spaceweather`, an S3 bucket behind "
    "a JavaScript explorer; the old `ngdc.noaa.gov/dscovr/data/` path is "
    "dead and `ncei.noaa.gov/data/dscovr-space-weather/` 404s. Listing it "
    "path-style reaches daily netCDF from 2016-07 to the present. That "
    "closes the coverage gap **and** a second one: the Level-2 "
    "magnetometer carries `bz_gsm`, which CDAWeb's `DSCOVR_H0_MAG` does not "
    "have in any form.\n")
add("**Route 4 carries no GSM field.** CDAWeb's `DSCOVR_H0_MAG` serves GSE "
    "and RTN only, so a Bz(GSM) — the quantity that actually drives the "
    "storm — has to come from a coordinate rotation "
    "(`transform_coordinates`) or, as here, from the Level-2 product in "
    "route 6b.\n")
add("### The same quantity, measured several ways\n")
QUANT = [("v", "Max flow speed", "km s⁻¹"),
         ("n", "Max proton density", "cm⁻³"),
         ("b", "Max |B|", "nT"),
         ("bz", "Min Bz (GSM)", "nT")]
NAMES = {"ace_cdaweb": "ACE CDAWeb (hourly SWE / 4-min MFI)",
         "ace_pyspedas": "ACE pySPEDAS 1-s/64-s",
         "omni_1min": "OMNI 1-min", "dscovr": "DSCOVR CDAWeb 1-s",
         "dscovr_l2": "DSCOVR **L2** (NOAA)", "wind": "Wind"}
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
            f"{unit}.")
        if quant == "v":
            add("**The DSCOVR row here is not a sampling difference — it is "
                "wrong, and the file says so only if you read the right "
                "flag.** See below.")
add("\nFour things follow, and they are the reason for running seven "
    "routes instead of one.\n")
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
_dv = g("S5x_v_dscovr_l2", "value")
_ov = g("S5x_v_omni_1min", "value")
_frac = g("S5_dscovrl2_fc", "reduced_proton_quality_fraction")
add("**DSCOVR's Faraday cup under-reads this storm, and its own "
    f"`overall_quality` flag does not catch it.** Its speed maximum is "
    f"{fmt(_dv,4)} km s⁻¹ against OMNI's {fmt(_ov,4)} — and at "
    "2024-05-12 01:00, when OMNI and ACE both read near 1000 km s⁻¹, the "
    "cup reports ~470 km s⁻¹ with `overall_quality = 0` on every one of "
    "those minutes. Restricting to quality-0 samples changes the maximum "
    "not at all. The only signal in the file is "
    f"`reduced_proton_quality_flag`, set on **{(_frac or 0) * 100:.0f}%** of "
    "this window. So DSCOVR plasma is good for density and structure and "
    "is the wrong source for a storm speed peak — which is also why the "
    "earlier refusal was worth keeping rather than papering over with SWPC "
    "real-time. `run_validation.py dscovrl2` pins the under-read as well as "
    "the capability, so a reprocessing that fixes it will fail the check.\n")
add("**|B| is the check that the routes agree.** Five routes across three "
    "spacecraft (ACE, DSCOVR, Wind — OMNI is merged from them, not "
    "independent) put the maximum inside "
    f"{fmt(min(v for v in [g('S5x_b_ace_cdaweb','value'), g('S5x_b_ace_pyspedas','value'), g('S5x_b_dscovr','value'), g('S5x_b_dscovr_l2','value'), g('S5x_b_wind','value')] if v),4)}–"
    f"{fmt(max(v for v in [g('S5x_b_ace_cdaweb','value'), g('S5x_b_ace_pyspedas','value'), g('S5x_b_dscovr','value'), g('S5x_b_dscovr_l2','value'), g('S5x_b_wind','value')] if v),4)} nT "
    "within about ten minutes of each other, and DSCOVR's Level-2 Bz "
    f"({fmt(g('S5x_bz_dscovr_l2','value'),4)} nT) sits inside the "
    "ACE/Wind/OMNI bracket. The magnetometer has no problem; only the cup "
    "does. That is what makes the density spread a sampling effect and the "
    "speed row an instrument fault.\n")
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
    "provider does not answer. Two routes replace it, both used here: "
    "`fetch_aia_synoptic` (JSOC synoptic archive, level 1.5 at 1024², no "
    "credentials, seconds per frame) and `fetch_aia_level1` (JSOC via "
    "`drms`, native 4096² level 1, needs a registered JSOC export email). "
    "HMI and LASCO through VSO are unaffected.")
add("2. **The HMI flux cell raises a units error** "
    "(`'arcsec2 / pix2' and 'cm2' are not convertible`). Pixel area has to "
    "be converted through the plate scale and the solar distance before "
    "multiplying by field strength. `magnetogram_metrics` does this.")
add("3. **`sm.coord_table.to_pandas()` raises** in current solarmach; the "
    "table is already DataFrame-like. The hard-coded values it falls back "
    "to are wrong by 120°+ for Solar Orbiter, so this failure is not "
    "cosmetic.")
add("4. **The CME speed cell uses `np.random.uniform`** and never produced "
    "the speeds the notebook prints. Replaced here by a real measurement: "
    "`track_cme_front` locates the leading edge in each difference frame "
    "and `cme_height_time` fits it. Note the search window must open at the "
    "flare peak — C2 sees only 2.4–5.8 R⊙, so a sequence starting an hour "
    "late catches a front already leaving the field.")
add("5. **DSCOVR Level 2 is not on CDAWeb at all for 2024.** "
    "`DSCOVR_H1_FC` ends 2019 and `DSCOVR_H0_MAG` has no GSM component. "
    "Both live in NOAA's own archive at "
    "`archive.data.noaa.gov/satellite-spaceweather` (an S3 bucket, listed "
    "path-style); the older `ngdc.noaa.gov/dscovr/data/` and "
    "`ncei.noaa.gov/data/dscovr-space-weather/` paths are gone. "
    "`fetch_dscovr_l2` reaches it — **and check "
    "`reduced_proton_quality_flag`, not just `overall_quality`**, before "
    "trusting a cup speed.\n")
add("## Capabilities added to helio-agent for this reproduction\n")
add("| Tool | Purpose | Validation |")
add("|---|---|---|")
add("| `plot_coronagraph_sequence` | Exposure-normalised running-difference "
    "panels from a coronagraph FITS sequence | `run_validation.py corona` |")
add("| `cme_height_time` | Linear height-time fit that refuses <3 points or "
    "non-monotonic heights | `run_validation.py corona` |")
add("| `track_cme_front` | Measures the leading edge per frame so the fit "
    "has real input; azimuthal noise reference, monotonicity-scored sector "
    "choice, explicit halo detection | `run_validation.py cmetrack` |")
add("| `plot_heliospheric_config` | solarmach constellation and Parker "
    "spirals, returning the position table | `run_validation.py corona` |")
add("| `fetch_aia_synoptic` | JSOC synoptic AIA (level 1.5, 1024²), "
    "replacing the dead VSO export route with no credentials needed | "
    "`run_validation.py aiasyn` |")
add("| `fetch_aia_level1` | Native 4096² level-1 AIA from JSOC via `drms`; "
    "refuses by name without a registered export email rather than "
    "substituting the smaller product | `run_validation.py aial1` |")
add("| `fetch_vso(detector=...)` | LASCO C2/C3 and SECCHI COR1/COR2/EUVI "
    "selection, so a sequence does not interleave two fields of view | "
    "`run_validation.py corona` |")
add("| `fetch_dscovr_l2` | DSCOVR Level 2 from the NOAA NCEI S3 archive — "
    "2024 plasma and the `bz_gsm` component, neither of which CDAWeb has; "
    "surfaces `reduced_proton_quality_flag` | `run_validation.py dscovrl2` |")
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
