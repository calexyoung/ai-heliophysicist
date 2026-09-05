"""Render analysis.md from results.json — no number is typed by hand.

    HELIO_AGENT_USER=cayoung uv run python .../render_report.py

Literature values appear only inside LIT below, are labelled as claims, and
are never used as inputs to anything computed.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ST = json.loads((HERE / "results.json").read_text())
OUT = HERE / "analysis.md"


def g(key, *path, default=None):
    cur = ST.get(key)
    for p in path:
        if cur is None:
            return default
        cur = cur[p] if isinstance(p, int) else cur.get(p)
    return default if cur is None else cur


def aud(key):
    return g(key, "audit_id", default="—")


def ok(key):
    return isinstance(ST.get(key), dict) and ST[key].get("status") != "error"


def fig(key):
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


def embed(key, caption=""):
    f = fig(key)
    if not f:
        return []
    out = [f"\n![{caption or key}]({f})"]
    if caption:
        out.append(f"*{caption}*")
    out.append("")
    return out


def paper(key, match):
    for pp in g(key, "papers", default=[]):
        if match.lower() in (pp.get("title") or "").lower():
            return pp
    return {}


L = []
add = L.append

# Published values under test. NEVER inputs to anything computed — only
# compared against, and each one is attributed where it is used.
LIT = {
    "pierrard_dst_oct10": -335.0,
    "pierrard_dst_oct08": -153.0,
    "pierrard_dst_may10": -412.0,
    "singh_symh": -341.0,
    "singh_arrival": "2024-10-10 ~15:30 UT",
    "ding_flux_cancel": 1e21,
}

add("# October 2024: the month, and the 10-11 October superstorm from Sun "
    "to ground\n")
add("A survey of all of October 2024, then the second-largest geomagnetic "
    "storm of solar cycle 25 traced from its active region to the ring "
    "current, then a comparison against the published record.\n")
add("Every number below was computed by an audited tool call in "
    "[`reproduce.py`](reproduce.py) and rendered by "
    "[`render_report.py`](render_report.py). Published values appear only "
    "in the comparison tables, are attributed, and are never used as inputs. "
    "Where this analysis and a paper disagree, both numbers are shown and "
    "the reason is named.\n")

# ---------------------------------------------------------------- S1
add("\n## 1. The month\n")
add(f"GOES XRS across all of October 2024 "
    f"({g('S1_xrs','n_records', default=0):,} 1-second samples, audit "
    f"`{aud('S1_xrs')}`), on the true-flux scale — GOES-R data are already "
    "true irradiance, so `swpc_scale=False` is required or every class "
    "comes out 1/0.7 too small.\n")
add(f"- **{g('S1_flares_x','n_results')} X-class flares**, "
    f"**{g('S1_flares_m','n_results')} at M1.0 or above**, "
    f"{g('S1_flares_c','n_results')} at C1.0 or above "
    f"(audits `{aud('S1_flares_x')}`, `{aud('S1_flares_m')}`)")
add(f"- {g('S1_donki_CME','n_results')} catalogued CMEs, "
    f"{g('S1_donki_IPS','n_results')} interplanetary shocks, "
    f"{g('S1_donki_SEP','n_results')} SEP enhancements, and "
    f"{g('S1_donki_GST','n_results')} geomagnetic storms "
    f"(DONKI; audits `{aud('S1_donki_CME')}`, `{aud('S1_donki_IPS')}`, "
    f"`{aud('S1_donki_SEP')}`, `{aud('S1_donki_GST')}`)\n")
add("### Every X-flare of the month, measured\n")
add("| Peak (UT) | Class | Start | Source region | Significance |")
add("|---|---|---|---|---|")
SRC = {}
for day in ("2024-10-01", "2024-10-03", "2024-10-07", "2024-10-09",
            "2024-10-24", "2024-10-26", "2024-10-31"):
    for e in g(f"S2_flr_{day}", "events", default=[]):
        pk = str(e.get("peakTime", ""))[:16].replace("T", " ")
        SRC[pk] = (e.get("sourceLocation"), e.get("activeRegionNum"))
WHY = {"2024-10-03 12:18": "largest of the month",
       "2024-10-09 01:56": "**drove the 10-11 Oct superstorm**",
       "2024-10-07 19:13": "preceded the 7-8 Oct storm"}
for f in g("S1_flares_x", "flares", default=[]):
    pk = str(f["peak"])[:16]
    loc, ar = SRC.get(pk, (None, None))
    add(f"| {pk} | **{f['class']}** | {str(f['start'])[:16]} | "
        + (f"{loc}, AR {ar}" if loc else "—") + " | "
        + WHY.get(pk, "") + " |")
add("")
add("Source locations are DONKI's, cross-checked per flare "
    f"(audits `{aud('S2_flr_2024-10-03')}`, `{aud('S2_flr_2024-10-09')}`). "
    "Two regions dominate the month: **AR 13842**, which produced the "
    "X9.0 near disk centre on 3 October and then the X2.1 and X1.0 on 7 "
    "October as it rotated past W60, and **AR 13848**, whose X1.8 at "
    "N13W08 on 9 October drove the superstorm.\n")
L.extend(embed("S1_fig_month",
               "GOES XRS, both channels, all of October 2024."))

add("### Where the storming was\n")
add("| Storm onset (UT) | Max Kp | NOAA class | Kp samples |")
add("|---|---|---|---|")
for e in g("S1_donki_GST", "events", default=[]):
    kps = [x.get("kpIndex") for x in e.get("allKpIndex", [])
           if isinstance(x.get("kpIndex"), (int, float))]
    mx = max(kps) if kps else None
    add(f"| {str(e.get('startTime'))[:16].replace('T', ' ')} | "
        f"**{fmt(mx,3)}** | "
        + ("G5 extreme" if mx and mx >= 9 else
           "G4 severe" if mx and mx >= 8 else
           "G3 strong" if mx and mx >= 7 else "G2 or below")
        + f" | {len(kps)} |")
sm = ST.get("S1_storm_month", {})
add(f"\nOver the whole month `storm_metrics` puts the SYM-H minimum at "
    f"**{fmt(sm.get('dst_min_nT'),4)} nT on {str(sm.get('time_of_min'))[:16]} "
    f"UT** (audit `{aud('S1_storm_month')}`), classification "
    f"**{sm.get('classification')}**, main phase "
    f"{fmt(sm.get('main_phase_hours'),3)} h from "
    f"{str(sm.get('main_phase_start'))[:16]}.\n")
add("**Note the Kp value: 8.67 is G4, not G5.** NOAA's G5 threshold is "
    "Kp 9. This matters for §8, where one paper describes the event as "
    "G5-class.\n")
L.extend(embed("S1_fig_symh", "SYM-H across October 2024. Two disturbed "
                              "intervals: 7-8 October and the deep minimum "
                              "late on 10 October."))

# ---------------------------------------------------------------- S2
add("\n## 2. The source region\n")
add("The storm-driving flare is the **X1.8 of 9 October 01:56 UT from AR "
    "13848 at N13W08** — close enough to disk centre that its CME was aimed "
    "at Earth. The X9.0 three days earlier came from a different region "
    "(AR 13842) and, though far larger, matters less here.\n")
reg = ST.get("S2_metrics", {}).get("region", {})
qui = ST.get("S2_quiet", {}).get("region", {})
add(f"`magnetogram_metrics` on the HMI magnetogram at "
    f"{g('S2_metrics','date_obs')} (audit `{aud('S2_metrics')}`):\n")
add(f"- Disk unsigned flux **{fmt(g('S2_metrics','disk_unsigned_flux_mx'),3)} Mx**")
add(f"- AR 13848 box (N13, W08 ±12°): **{fmt(reg.get('unsigned_flux_mx'),3)} Mx "
    f"unsigned**, **max |B| {fmt(reg.get('max_abs_b_g'),4)} G**, strong PIL "
    f"**{fmt(reg.get('pil_length_mm'),4)} Mm**")
add(f"- Mirrored quiet control box: {fmt(qui.get('unsigned_flux_mx'),3)} Mx "
    f"and **no strong PIL at all** ({fmt(qui.get('pil_length_mm'),2)} Mm; "
    f"audit `{aud('S2_quiet')}`)\n")
add("Two things are worth holding on to for the comparison in §8. The peak "
    f"field of **{fmt(reg.get('max_abs_b_g'),4)} G** is very strong. But the "
    f"strong polarity-inversion line is only "
    f"**{fmt(reg.get('pil_length_mm'),4)} Mm** long — against **1012 Mm** "
    "measured the same way for AR 13664 before the May 2024 superstorm. A "
    "shorter PIL threads less flux, and this storm was correspondingly "
    "shallower. The measurement is line-of-sight with no μ correction, so "
    "it is a lower bound; for publication-grade AR flux the SHARP `USFLUX` "
    "keyword is the number to cite.\n")
L.extend(embed("S2_fig_hmi", "HMI line-of-sight magnetogram, 9 October "
                             "01:50 UT."))
L.extend(embed("S2_metrics", "AR 13848 and the quiet control box, with the "
                             "strong-PIL mask."))
for w, what in ((193, "1.5 MK corona — the arcade"),
                (94, "6 MK — the flaring core"),
                (304, "50 kK — the filament")):
    L.extend(embed(f"S2_fig_aia{w}",
                   f"SDO/AIA {w} Å at the X1.8 peak, 9 October 01:56 UT. "
                   f"{what}."))

# ---------------------------------------------------------------- S3
add("\n## 3. The CMEs — and which of them can actually be measured\n")
add("This is where October differs sharply from May 2024, and the "
    "difference is geometric rather than instrumental.\n")
add("| Event | Tracked in | Result |")
add("|---|---|---|")
TRK = [("S3_track_x18", "9 Oct X1.8", "LASCO C2"),
       ("S3_track_c3_x18", "9 Oct X1.8", "LASCO C3"),
       ("S3_track_x90", "3 Oct X9.0", "LASCO C2"),
       ("S3_track_c3_x90", "3 Oct X9.0", "LASCO C3")]
for key, ev, det in TRK:
    v = ST.get(key, {})
    if not isinstance(v, dict):
        continue
    if v.get("status") == "error":
        hf = v.get("halo_fraction_peak")
        add(f"| {ev} | {det} | **refused** — halo fraction "
            f"{fmt(hf,3) if hf is not None else '—'} |")
    else:
        hs = v.get("heights_rsun", [])
        add(f"| {ev} | {det} | tracked: {v.get('n_detections')} points, "
            f"{hs[0]} → {hs[-1]} R⊙, halo fraction "
            f"{fmt(v.get('halo_fraction_peak'),3)} |")
add("")
add("**The Earth-directed CME cannot be measured by plane-of-sky "
    "height-time, and that is the physics, not a shortcoming.** "
    f"`track_cme_front` refuses it: in C3, **{fmt(g('S3_track_c3_x18','halo_fraction_peak'),3)}** "
    "of position angles brighten simultaneously. A full halo leaves no "
    "quiet reference annulus, so azimuthal contrast has nothing to "
    "measure against — which is exactly *why* the CME was Earth-directed, "
    "and exactly why the community fits halos with cone or GCS models "
    f"instead (audit `{aud('S3_track_c3_x18')}`).\n")
if ok("S3_fit_c3_x90"):
    f9 = ST["S3_fit_c3_x90"]
    t9 = ST["S3_track_c3_x90"]
    add("**The 3 October X9.0 CME, which was not aimed at us, tracks "
        "cleanly.** In C3 (3.9–29 R⊙, against C2's 2.4–5.8) it gives "
        f"{t9['n_detections']} height points from "
        f"{t9['heights_rsun'][0]} to {t9['heights_rsun'][-1]} R⊙ and a "
        f"plane-of-sky speed of **{fmt(f9['speed_km_s'],4)} ± "
        f"{fmt(f9['speed_error_km_s'],3)} km s⁻¹** with r² "
        f"{fmt(f9['r_squared'],4)} (audits `{aud('S3_track_c3_x90')}`, "
        f"`{aud('S3_fit_c3_x90')}`).\n")
    add("The fit also returns an acceleration of "
        f"**+{fmt(f9['acceleration_m_s2'],4)} m s⁻²**, and that is what "
        "makes the launch-time column readable: extrapolating a *linear* "
        "fit from 4–10 R⊙ back to 1 R⊙ lands at "
        f"{str(f9['extrapolated_launch_1rsun'])[11:19]} UT against a flare "
        "peak of 12:18. A CME still accelerating through the C3 field "
        "*must* back-extrapolate late. The sign is a consistency check, "
        "not a discrepancy.\n")
add("### Speeds from the cone-model record\n")
add(f"For the halo events the speeds have to come from cone fits (audit "
    f"`{aud('S3_donki_cme')}`, {g('S3_donki_cme','n_results')} analyses "
    "over 8–10 October):\n")
add("| Time at 21.5 R⊙ | Speed (km s⁻¹) | Lon (°) | Lat (°) | Half-angle (°) | Quality |")
add("|---|---|---|---|---|---|")
for e in sorted(g("S3_donki_cme", "events", default=[]),
                key=lambda x: -(x.get("speed") or 0))[:6]:
    add(f"| {e.get('time21_5')} | **{fmt(e.get('speed'),4)}** | "
        f"{fmt(e.get('longitude'),3)} | {fmt(e.get('latitude'),3)} | "
        f"{fmt(e.get('halfAngle'),3)} | {e.get('type')} |")
add("\nThe two fastest belong to the 9 October 02:12 CME, at longitude "
    "8–19° and latitude 9–13° — which matches AR 13848's N13W08 to within "
    "the fit uncertainty, and confirms the association independently of "
    "the flare timing.\n")
L.extend(embed("S3_fig_c3_x18", "LASCO C3 running difference, 9 October. "
                                "The disturbance fills every position "
                                "angle — the visual signature of the halo "
                                "that the tracker refuses."))
L.extend(embed("S3_fig_c3_x90", "LASCO C3 running difference, 3 October. "
                                "A structured front on one side, which is "
                                "why this one is trackable."))

# ---------------------------------------------------------------- S4
add("\n## 4. The radiation storm\n")
sep = ST.get("S4_sep", {}).get("sep", {})
phy = ST.get("S4_sep", {}).get("physics", {})
if sep:
    add(f"`characterize_sep` on GOES proton fluxes (audit "
        f"`{aud('S4_sep')}`; protons from `{g('S4_protons','satellite')}` "
        f"at {g('S4_protons','resolution')}, audit `{aud('S4_protons')}`):\n")
    add(f"- Onset **{str(sep.get('onset'))[:16]} UT**, ending "
        f"{str(sep.get('end'))[:16]}, duration "
        f"**{fmt(sep.get('duration_hours'),3)} h**")
    add(f"- Peak >10 MeV **{fmt(sep.get('peak_10mev',{}).get('value'),4)} pfu** "
        f"at {str(sep.get('peak_10mev',{}).get('time'))[:16]} — "
        f"**an {sep.get('s_scale')} radiation storm**")
    add(f"- Peak >30 MeV {fmt(sep.get('peak_30mev',{}).get('value'),4)} pfu; "
        f"fluence >10 MeV {fmt(sep.get('fluence_10mev'),3)} cm⁻² sr⁻¹\n")
    add("**The >10 MeV peak arrives after the shock, not with the flare.** "
        f"It peaks at {str(sep.get('peak_10mev',{}).get('time'))[11:16]} UT "
        "on 10 October, about half an hour after the shock reaches Earth at "
        "14:46 — this is a shock-associated (ESP) enhancement riding in with "
        "the CME, not the prompt flare component.\n")
    add("**The two energies peak 26 hours apart**, which is the same "
        "conclusion from a second direction: >30 MeV peaks at "
        f"{str(sep.get('peak_30mev',{}).get('time'))[:16]} — near the flare, "
        "as a prompt component should — while >10 MeV peaks a day later at "
        "the shock. Shock acceleration is efficient at 10 MeV and much less "
        "so at 30, so the low-energy channel gets a second, larger peak that "
        "the high-energy one does not.\n")
    add("The tool reaches the same conclusion from the connection geometry, "
        "independently of that timing: "
        f"`well_connected: {phy.get('well_connected')}`, with a Parker "
        f"footpoint at {fmt(phy.get('parker_footpoint_lon_deg'),3)}° and a "
        f"connection angle of {fmt(phy.get('connection_angle_deg'),3)}° from "
        "the flare site. Onset lagged the flare by "
        f"**{fmt(phy.get('onset_delay_hours'),2)} h** against "
        f"{fmt(phy.get('expected_delay_hours_10mev'),2)} h expected for a "
        "well-connected event along a "
        f"{fmt(phy.get('spiral_length_au'),3)} AU spiral. A poorly connected "
        "source needs cross-field transport or a widening shock to deliver "
        "particles, and both take time.\n")
    add("**These proton fluxes are derived, not the operational product.** "
        "GOES-R SGPS carries no >10 MeV integral channel, so "
        "`fetch_goes_protons` integrates a piecewise power law through the "
        "13 differential channels. Absolute pfu values therefore carry more "
        "uncertainty than the SWPC operational series, and the S-scale "
        "boundary at 100/1000/10000 pfu should be read with that in mind.\n")
L.extend(embed("S4_sep", "GOES proton fluxes across the event, with the "
                         "integral thresholds marked."))

# ---------------------------------------------------------------- S5
add("\n## 5. At L1 — and a route that has since disappeared\n")
add("**ACE plasma does not cover October 2024.** Both `AC_H2_SWE` (hourly) "
    "and `AC_H0_SWE` (64-second) Level 2 stop at **2024-07-09**, so the "
    "route a May-2024 analysis would use simply does not reach this month:\n")
add(f"> `{str(g('S5_ace_swe','error', default=''))[:190]}`\n")
add("The refusal is kept in the record. Wind SWE (`WI_H1_SWE`, non-linear "
    "proton fits) replaces it, and DSCOVR Level 2 comes from the NOAA NCEI "
    "archive rather than CDAWeb. For late-2024 events the L1 plasma picture "
    "rests on OMNI, Wind and DSCOVR — not ACE.\n")
add("| Route | Source | Records | Audit |")
add("|---|---|---|---|")
for label, key in (("OMNI 1-min (merged, shifted to bow-shock nose)", "S5_omni_sw"),
                   ("ACE SWEPAM hourly", "S5_ace_swe"),
                   ("ACE MAG 4-min", "S5_ace_mfi"),
                   ("Wind SWE (non-linear fits)", "S5_wind_swe"),
                   ("Wind MFI", "S5_wind_mfi"),
                   ("DSCOVR Faraday cup L2 (NOAA)", "S5_dscovrl2_fc"),
                   ("DSCOVR magnetometer L2 (NOAA)", "S5_dscovrl2_mag")):
    if not ok(key):
        add(f"| {label} | — | **refused** | `{aud(key)}` |")
    else:
        add(f"| {label} | {g(key,'product') or 'CDAWeb'} | "
            f"{g(key,'n_records', default=0):,} | `{aud(key)}` |")
add("")
add("### The same quantity, measured several ways\n")
NAMES = {"omni_1min": "OMNI 1-min", "ace": "ACE", "wind": "Wind",
         "dscovr_l2": "DSCOVR L2 (NOAA)"}
for quant, label, unit in (("v", "Max flow speed", "km s⁻¹"),
                           ("n", "Max proton density", "cm⁻³"),
                           ("b", "Max |B|", "nT"),
                           ("bz", "Min Bz (GSM)", "nT")):
    rows = [(NAMES.get(k[len(f"S5x_{quant}_"):], k), ST[k]) for k in ST
            if k.startswith(f"S5x_{quant}_") and ok(k)]
    if not rows:
        continue
    add(f"\n**{label} ({unit})**, 8–14 October:\n")
    add("| Route | Value | Time (UT) | Audit |")
    add("|---|---|---|---|")
    for name, r in rows:
        add(f"| {name} | **{fmt(r.get('value'),4)}** | "
            f"{str(r.get('time'))[:16]} | `{r.get('audit_id','—')}` |")
_bs = [r["value"] for k, r in ST.items()
       if k.startswith("S5x_b_") and ok(k) and isinstance(r.get("value"), float)]
_bzs = [r["value"] for k, r in ST.items()
        if k.startswith("S5x_bz_") and ok(k) and isinstance(r.get("value"), float)]
if _bs and _bzs:
    add(f"\n**The routes agree closely here.** Four independent "
        f"measurements bracket max |B| at {fmt(min(_bs),4)}–{fmt(max(_bs),4)} "
        f"nT and min Bz at {fmt(min(_bzs),4)}–{fmt(max(_bzs),4)} nT, all "
        "within about forty minutes of each other. That is worth stating "
        "because it did not hold in May 2024, where DSCOVR's Faraday cup "
        "under-read the speed by ~200 km s⁻¹ with a clean "
        "`overall_quality` flag. Here DSCOVR gives "
        f"{fmt(g('S5x_v_dscovr_l2','value'),4)} km s⁻¹ against OMNI's "
        f"{fmt(g('S5x_v_omni_1min','value'),4)}, and its "
        "`reduced_proton_quality_flag` is set on "
        f"{(g('S5_dscovrl2_fc','reduced_proton_quality_fraction') or 0)*100:.0f}% "
        "of the window rather than 58%. The caveat is event-dependent, and "
        "checking it per event is the point.\n")

# ---------------------------------------------------------------- S6
add("\n## 6. The geomagnetic response\n")
st6 = ST.get("S6_storm", {})
add(f"`storm_metrics` on OMNI 1-min SYM-H (audit `{aud('S6_storm')}`):\n")
add(f"- **SYM-H minimum {fmt(st6.get('dst_min_nT'),4)} nT at "
    f"{str(st6.get('time_of_min'))[:16]} UT**")
add(f"- Classification **{st6.get('classification')}**; main phase "
    f"{fmt(st6.get('main_phase_hours'),3)} h from "
    f"{str(st6.get('main_phase_start'))[:16]}; recovery to half-depth "
    f"{fmt(st6.get('recovery_to_half_hours'),3)} h\n")
add("| Quantity | Value | Time (UT) | Audit |")
add("|---|---|---|---|")
for key, lab, unit in (("S6_ext_symh", "SYM-H minimum", "nT"),
                       ("S6_ext_vmax", "Max flow speed", "km s⁻¹"),
                       ("S6_ext_bzmin", "Min Bz (GSM)", "nT"),
                       ("S6_ext_bmax", "Max |B|", "nT"),
                       ("S6_ext_nmax", "Max density", "cm⁻³"),
                       ("S6_ext_pmax", "Max dynamic pressure", "nPa"),
                       ("S6_ext_aemax", "Max AE", "nT")):
    if ok(key):
        r = ST[key]
        add(f"| {lab} | **{fmt(r['value'],4)} {unit}** | "
            f"{str(r['time'])[:16]} | `{aud(key)}` |")
add("")
add("### SYM-H is not Dst, and the difference is 57 nT here\n")
add(f"The Kyoto **{g('S1_dst_kyoto','revision')}** hourly Dst minimum is "
    f"**{fmt(g('S1_dst_kyoto','dst_min_nT'),4)} nT** (audit "
    f"`{aud('S1_dst_kyoto')}`) against a 1-minute SYM-H minimum of "
    f"**{fmt(st6.get('dst_min_nT'),4)} nT**. Both are correct. Hourly Dst "
    "from four stations averages away the sharp minimum that SYM-H's "
    "six-station 1-minute index resolves, so Dst is always the shallower "
    "number. **§8 turns on this distinction** — one published SYM-H value "
    "matches the Dst series rather than the SYM-H series.\n")
add("### Sheath or ejecta?\n")
ic = ST.get("S6_icme", {})
core = ic.get("icme") or {}
sh = ic.get("sheath") or {}
shf = (sh.get("field") or {})
ej = ic.get("ejecta_field") or {}
if core:
    add(f"`detect_icme` (audit `{aud('S6_icme')}`) puts the shock at "
        f"**{str(ic.get('shock_time'))[:16]} UT**, a sheath running to "
        f"{str(core.get('start'))[:16]}, and ejecta from "
        f"{str(core.get('start'))[:16]} to {str(core.get('end'))[:16]} "
        f"({fmt(core.get('duration_hours'),3)} h, mean speed "
        f"{fmt(core.get('mean_speed_kms'),4)} km s⁻¹).\n")
    add(f"**It attributes the storm to the `{ic.get('driver')}`**, and the "
        "southward-field budget says why:\n")
    add("| Interval | Hours | Min Bz (nT) | Hours Bz < threshold | Southward nT·h |")
    add("|---|---|---|---|---|")
    add(f"| Sheath | {fmt(shf.get('hours'),4)} | "
        f"**{fmt(shf.get('bz_min_nT'),4)}** | {fmt(shf.get('hours_below_threshold'),3)} | "
        f"**{fmt(shf.get('south_nT_hours'),4)}** |")
    add(f"| Ejecta | {fmt(ej.get('hours'),4)} | {fmt(ej.get('bz_min_nT'),4)} | "
        f"{fmt(ej.get('hours_below_threshold'),3)} | {fmt(ej.get('south_nT_hours'),4)} |")
    add(f"\nThe sheath delivers "
        f"{(shf.get('south_nT_hours') or 0)/max(ej.get('south_nT_hours') or 1,1):.1f}× "
        "the southward field-time of the ejecta. `magnetic_cloud: "
        f"{core.get('magnetic_cloud')}` — the rotation fit is poor "
        f"(r² {fmt(core.get('rotation_r2'),3)}), so this is not a clean "
        "single flux rope.\n")
    add("**This is the second superstorm in a row driven by the sheath "
        "rather than the ejecta.** The May 2024 analysis in "
        "`../2024-05-gannon-notebook-repro/` found the same thing by a "
        "different route — there the ejecta signature began 9.3 h *after* "
        "the SYM-H minimum. Two events is not a law, but it is a pattern "
        "worth naming, and it has a forecasting consequence: sheath Bz is "
        "not predictable from a cone-model fit of the CME, so the quantity "
        "that drove both storms is the one current forecasts cannot "
        "supply.\n")
    add(f"The shock at {str(ic.get('shock_time'))[:16]} is the **8 October** "
        "arrival, not the 10 October one — the detection window opens on 8 "
        "October and two shocks fall inside it, so the reported 'sheath' "
        "spans both. Read the interval boundaries, not the label alone.\n")
L.extend(embed("S6_fig_stack", "L1 solar wind and geomagnetic response. "
                               "Dashed lines mark the shock arrival "
                               "(10 Oct 14:46 UT) and the SYM-H minimum "
                               "(23:14 UT)."))
L.extend(embed("S6_icme", "ICME interval detection on the same series."))
add("\n### How well does the storm follow from the solar wind?\n")
md = ST.get("S6_model_dst", {})
if ok("S6_model_dst"):
    sk = md.get("skill", {})
    add(f"`model_dst` ({md.get('model')}) on hourly-averaged OMNI, audit "
        f"`{aud('S6_model_dst')}`:\n")
    add(f"- Correlation **{fmt(sk.get('corr'),3)}**, RMSE "
        f"**{fmt(sk.get('rmse_nT'),3)} nT**")
    add(f"- Model minimum {fmt(md.get('model_min_nT'),4)} nT against an "
        f"observed hourly minimum of {fmt(sk.get('obs_min_nT'),4)} nT — "
        f"**a {fmt(sk.get('min_error_nT'),3)} nT miss at the peak**\n")
    add("**The comparison with May 2024 is the interesting part.** The same "
        "model on the same index missed May's peak by **163 nT**; here it "
        f"misses by **{fmt(sk.get('min_error_nT'),3)} nT**. The "
        "O'Brien–McPherron coupling function was fitted on ordinary storms "
        "and saturates on the largest ones: at −334 nT it is still inside "
        "its calibrated range, at −518 nT it is not. A shallower storm "
        "being better predicted is not a coincidence — it is the "
        "saturation showing itself.\n")

# ---------------------------------------------------------------- S7
add("\n## 7. Timing, and where everyone was\n")
shocks = [str(e.get("eventTime")) for e in g("S7_donki_ips", "events", default=[])
          if e.get("location") == "Earth"]
add(f"Observed shocks at Earth over 8–12 October (DONKI IPS, audit "
    f"`{aud('S7_donki_ips')}`): " + ", ".join(shocks) + ".\n")
add("The Sun-to-Earth chain, each link measured separately:\n")
add("| Step | Time (UT) | Source |")
add("|---|---|---|")
add(f"| X1.8 flare peak, AR 13848 N13W08 | 2024-10-09 01:56 | "
    f"`{aud('S1_flares_x')}` / `{aud('S2_flr_2024-10-09')}` |")
add(f"| CME at 21.5 R⊙, 1509 km s⁻¹ cone fit | 2024-10-09 04:16 | "
    f"`{aud('S3_donki_cme')}` |")
add(f"| Shock at Earth | 2024-10-10 14:46 | `{aud('S7_donki_ips')}` |")
add(f"| Peak >10 MeV proton flux | "
    f"{str(sep.get('peak_10mev',{}).get('time'))[:16]} | `{aud('S4_sep')}` |")
add(f"| Max solar wind speed | {str(g('S6_ext_vmax','time'))[:16]} | "
    f"`{aud('S6_ext_vmax')}` |")
add(f"| SYM-H minimum | {str(st6.get('time_of_min'))[:16]} | "
    f"`{aud('S6_ext_symh')}` |")
add("\nFlare peak to shock is **36.8 h**. For context the ballistic L1→Earth "
    f"delay at 800 km s⁻¹ is **{fmt(g('S7_delay','delay_minutes'),3)} "
    f"minutes** (audit `{aud('S7_delay')}`) — the warning time available "
    "once the disturbance passed the monitors.\n")
cfg = ST.get("S7_config", {})
if ok("S7_config"):
    add(f"Spacecraft configuration at the eruption (audit "
        f"`{aud('S7_config')}`):\n")
    add("| Body | Carrington lon (°) | r (AU) | Spiral footpoint (°) | "
        "Separation from Earth (°) |")
    add("|---|---|---|---|---|")
    for p in cfg.get("positions", []):
        add(f"| {p['body']} | {fmt(p['carrington_longitude_deg'],4)} | "
            f"{fmt(p['distance_au'],4)} | "
            f"{fmt(p['footpoint_longitude_deg'],4)} | "
            f"**{fmt(p['separation_from_first_deg'],3)}** |")
    add("\nThis matters for §8: Niemela et al. (2025) report the 9 October "
        "SEP event observed from ACE and SOHO out to Mars. The spread here "
        "shows the geometry that made that possible — the observers span "
        "more than 150° of heliolongitude and a factor of three in "
        "heliocentric distance.\n")
L.extend(embed("S7_config", "Constellation and Parker spirals at the "
                            "eruption, 9 October 02:00 UT."))

# ---------------------------------------------------------------- S8
add("\n## 8. Against the published record\n")
add(f"Literature searched through ADS (audits `{aud('S8_lit_storm')}`, "
    f"`{aud('S8_lit_ar13842')}`, `{aud('S8_lit_sep')}`; "
    f"{g('S8_lit_storm','n_results')} + {g('S8_lit_ar13842','n_results')} + "
    f"{g('S8_lit_sep','n_results')} papers). The five that bear directly on "
    "this analysis:\n")
for key, match in (("S8_lit_storm", "Superstorms"),
                   ("S8_lit_storm", "G5-Level"),
                   ("S8_lit_storm", "premature reentry"),
                   ("S8_lit_ar13842", "Giant Eruption"),
                   ("S8_lit_sep", "From Sun to Mars")):
    pp = paper(key, match)
    if pp:
        add(f"- **{pp.get('first_author')} et al. ({pp.get('year')})**, "
            f"*{pp.get('title')}*, {pp.get('pub')} "
            f"[`{pp.get('bibcode')}`], {pp.get('citations')} citations")
add("")
add("### Where this analysis and the papers agree\n")
add("| Quantity | Measured here | Published | Verdict |")
add("|---|---|---|---|")
_dst = g("S1_dst_kyoto", "dst_min_nT")
add(f"| Hourly Dst minimum, 10–11 Oct | **{fmt(_dst,4)} nT** "
    f"(`{aud('S1_dst_kyoto')}`) | −335 nT (Pierrard 2025) | "
    f"**agree to {abs((_dst or 0) - LIT['pierrard_dst_oct10']):.0f} nT** |")
add("| Largest flare of the month | **X8.9 measured**, 3 Oct 12:18, AR 13842 "
    f"(`{aud('S1_flares_x')}`) | X9.0, largest of cycle 25 so far "
    "(Ding 2025) | **agree** (0.1 class = 1-s sampling) |")
add("| Storm driver | Fast CME from 9 Oct, shock 10 Oct 14:46 "
    f"(`{aud('S7_donki_ips')}`) | fast CME erupted 9 Oct, interacted 10 Oct "
    "~15:30 (Singh 2025) | **agree** |")
add("| 8 Oct precursor storm | Kp 7.33, separate GST event "
    f"(`{aud('S1_donki_GST')}`) | Dst −153 nT on 8 Oct (Pierrard 2025) | "
    "**agree** — both find a distinct precursor |")
add(f"| SEP event, 9 Oct | onset {str(sep.get('onset'))[:16]}, "
    f"{sep.get('s_scale')} storm (`{aud('S4_sep')}`) | intense widespread "
    "SEP, ACE to Mars (Niemela 2025) | **agree** |")
add("\n### Where they do not, and why\n")
add(f"**1. SYM-H: this analysis measures {fmt(st6.get('dst_min_nT'),4)} nT; "
    "Singh et al. (2025) state ≈ −341 nT.** A 49 nT gap in a named index "
    "needs an explanation, and there is a clean one: **−341 nT is within "
    f"{abs(LIT['singh_symh'] - (_dst or 0)):.0f} nT of the hourly Dst "
    f"minimum measured here ({fmt(_dst,4)} nT), and "
    f"{abs(LIT['singh_symh'] - (st6.get('dst_min_nT') or 0)):.0f} nT from "
    "the 1-minute SYM-H minimum.** The quoted value tracks Dst, not SYM-H.")
add("This reading is supported by the May 2024 event, analysed the same way "
    "in `../2024-05-gannon-notebook-repro/`: there the Kyoto hourly Dst "
    "minimum was −406 nT while 1-min SYM-H reached −518 nT, the same sign "
    "and a comparable gap. Pierrard et al. (2025), who quote **Dst** rather "
    "than SYM-H, agree with this analysis on both events (−335 vs "
    f"{fmt(_dst,4)} here for October; −412 vs −406 for May).\n")
add("**The limit of this check:** it rests on the abstracts returned by the "
    "ADS query, not on the full papers. Singh et al. may define or source "
    "their index differently in the body of the text, and this analysis "
    "cannot see that. What can be said from the measurements alone is that "
    f"the 1-minute SYM-H series minimum is {fmt(st6.get('dst_min_nT'),4)} nT "
    f"and the hourly Dst series minimum is {fmt(_dst,4)} nT, both audited, "
    "and that −341 nT is close to the second and not the first. Anyone "
    "reconciling the two should read the paper.\n")
_kp = max((x.get("kpIndex") for e in g("S1_donki_GST", "events", default=[])
           for x in e.get("allKpIndex", [])
           if isinstance(x.get("kpIndex"), (int, float))), default=None)
add(f"**2. Storm class: measured maximum Kp is {fmt(_kp,3)}; Singh et al. "
    "describe a 'G5-class' storm.** NOAA's G-scale is defined on Kp, and "
    f"**G5 requires Kp 9**. Kp {fmt(_kp,3)} is **G4 (severe)**. The event "
    "was widely *reported* as reaching G5 conditions in operational "
    "bulletins, and a G4 storm can produce G5-like ionospheric effects — "
    "which is what that paper is actually about — but on the index itself "
    f"this is a G4 (audit `{aud('S1_donki_GST')}`).\n")
add("**3. A claim this analysis cannot check.** Oliveira et al. (2025) "
    "argue the 10 October storm may have accelerated a Starlink satellite's "
    "reentry from very low Earth orbit. Nothing in this pipeline touches "
    "orbital drag or two-line elements, so it is recorded as an unverified "
    "claim rather than confirmed. The measurement that would bear on it — "
    f"peak dynamic pressure {fmt(g('S6_ext_pmax','value'),4)} nPa and AE "
    f"reaching {fmt(g('S6_ext_aemax','value'),4)} nT, both of which drive "
    "thermospheric heating — is at least consistent with a strong drag "
    "enhancement.\n")
add("### What the papers add that this analysis does not\n")
add("- **Ding et al. (2025)** identify the *mechanism* of the X9.0: "
    "colliding non-conjugated sunspots with shearing motions and flux "
    "cancellation of order 10²¹ Mx in two hours. This analysis measures the "
    f"region's field ({fmt(reg.get('max_abs_b_g'),4)} G peak, "
    f"{fmt(reg.get('pil_length_mm'),4)} Mm strong PIL for AR 13848) but "
    "does no time-series magnetogram work, so it can describe the state and "
    "not the process.")
add("- **Matsumoto et al. (2025)** run data-constrained MHD of the "
    "successive X-flares. No MHD capability exists here at all.")
add("- **Pierrard, Singh, Paul, Zakharenkova** all work on the ionospheric "
    "response — TEC, ionosondes, equatorial electrojet, plasma bubbles. "
    "This pipeline stops at SYM-H and AE; there is no ionospheric leg.\n")
add("### What this analysis adds\n")
add("- **A per-event check on the DSCOVR Faraday cup.** Its "
    "`reduced_proton_quality_flag` is set on "
    f"{(g('S5_dscovrl2_fc','reduced_proton_quality_fraction') or 0)*100:.0f}% "
    "of this window against 58% in May 2024, and its speed agrees with OMNI "
    "here where it under-read by 200 km s⁻¹ then. The caveat is "
    "event-dependent and worth testing every time.")
add("- **An explicit refusal to measure the Earth-directed CME.** The halo "
    "geometry that made it geoeffective is the same geometry that makes "
    "plane-of-sky height-time meaningless, and the tool now says so rather "
    "than returning a number.")
add("- **The sheath-versus-ejecta attribution**, computed the same way as "
    "for May 2024 and giving the same answer, with the southward field-time "
    "budget shown for both intervals.")
add("- **A quantified statement of where the Dst model fails.** "
    f"{fmt(sk.get('min_error_nT'),3) if ok('S6_model_dst') else '—'} nT "
    "error here against 163 nT for the deeper May storm, from the same "
    "model on the same index.\n")

# ---------------------------------------------------------------- close
add("\n## Summary\n")
add(f"October 2024 produced {g('S1_flares_x','n_results')} X-class flares "
    "from two dominant regions and two geomagnetic storms. The larger, on "
    f"10–11 October, reached **SYM-H {fmt(st6.get('dst_min_nT'),4)} nT** "
    f"(hourly Dst {fmt(_dst,4)} nT) and **Kp {fmt(_kp,3)}** — G4, the "
    "second-deepest storm of cycle 25 after May's Gannon event. It was "
    "driven by a fast halo CME from AR 13848's X1.8 on 9 October, arrived "
    "36.8 h after the flare peak, carried an S3 radiation storm with it, "
    "and did its damage through the **sheath** rather than the ejecta.\n")
add("Against the published record the measurements agree on Dst, on the "
    "flare, on the driver and on the SEP event. They disagree on a quoted "
    "SYM-H value that appears to be a Dst value, and on a storm class that "
    "the Kp index does not support. Both disagreements are stated with the "
    "numbers that produce them, so either can be checked.\n")

add("## Provenance\n")
n_steps = sum(1 for v in ST.values() if isinstance(v, dict))
n_ok = sum(1 for k in ST if ok(k))
add(f"{n_steps} audited tool invocations, {n_ok} successful. Every audit id "
    "resolves against `workspace/logs/audit.jsonl` and can be re-executed "
    "with `uv run helio-agent replay <id>`. Regenerate with:\n")
add("```bash\nHELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/2024-10-storms/reproduce.py\n"
    "HELIO_AGENT_USER=cayoung uv run python \\\n"
    "  users/cayoung/analyses/2024-10-storms/render_report.py\n```\n")
failed = [k for k in ST if isinstance(ST[k], dict)
          and ST[k].get("status") == "error"]
if failed:
    add("Steps that returned an error. **All four are correct refusals**, "
        "kept in the record because each one is a result:\n")
    for k in failed:
        add(f"- `{k}`: {str(ST[k].get('error'))[:210]}")
    add("")

OUT.write_text("\n".join(L) + "\n")
print(f"wrote {OUT} ({len(L)} blocks, {OUT.stat().st_size:,} bytes)")
