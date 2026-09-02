"""Physics models: L1-driven Dst nowcast and drag-based CME arrival.

These are the simplest widely-used operational models, implemented from the
published papers and validated against real storms (see validation cases
'dstmodel' and 'cmearrival'). They are estimates with known error budgets —
report them with their uncertainties, never as point truths.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import data_path

AU_KM = 1.496e8
RS_KM = 6.957e5


@tool(family="measure")
def model_dst(file: str, v_column: str, bz_column: str,
              density_column: str | None = None,
              dst_column: str | None = None,
              initial_dst: float = 0.0, out_name: str | None = None) -> dict:
    """Ring-current Dst nowcast from L1 solar wind (O'Brien & McPherron 2000).

    dDst*/dt = Q - Dst*/tau, with injection Q = -4.4 (VBs - 0.49) nT/h for
    the rectified dawn-dusk field VBs = V x Bs (mV/m; Bs = southward Bz,
    else 0) above the 0.49 mV/m threshold, and decay time
    tau = 2.40 exp(9.74 / (4.69 + VBs)) hours. With a density column, the
    pressure correction Dst = Dst* + 7.26 sqrt(Pdyn) - 11 is applied.

    file: CSV with solar wind at 1 AU / L1 (propagation delay to the
    magnetopause is NOT applied here — shift_time first if driving from L1
    in real time). v_column km/s, bz_column nT (GSM), density_column 1/cm^3.
    dst_column: observed Dst for skill scores (corr, RMSE, min error).
    Integration cadence = the file's cadence (resample to >= 5min first;
    hourly is the fidelity the model was fit at).
    """
    import numpy as np
    import pandas as pd

    df = pd.read_csv(file, index_col="time", parse_dates=True)
    for c in (v_column, bz_column):
        if c not in df.columns:
            return {"status": "error",
                    "error": f"refusing: column {c!r} not in file; "
                             f"available: {list(df.columns)}"}
    v = df[v_column].astype(float)
    bz = df[bz_column].astype(float)
    n = df[density_column].astype(float) if density_column else None

    dt_h = (df.index[1] - df.index[0]) / pd.Timedelta(hours=1)
    if not 0.05 <= dt_h <= 1.5:
        return {"status": "error",
                "error": f"refusing: cadence {dt_h:.3f} h outside 3min-1.5h; "
                         "resample_series first (hourly recommended)"}

    bs = np.where(bz < 0, -bz, 0.0)                    # southward field, nT
    vbs = v.values * bs * 1e-3                          # mV/m
    vbs = np.where(np.isnan(vbs), 0.0, vbs)
    ec = 0.49
    q = np.where(vbs > ec, -4.4 * (vbs - ec), 0.0)      # nT/h
    tau = 2.40 * np.exp(9.74 / (4.69 + vbs))            # h

    dst_star = np.empty(len(df))
    dst_star[0] = initial_dst
    for i in range(1, len(df)):
        d = dst_star[i - 1]
        dst_star[i] = d + (q[i - 1] - d / tau[i - 1]) * dt_h

    if n is not None:
        pdyn = 1.6726e-6 * n.values * v.values ** 2     # nPa (protons)
        pdyn = np.where(np.isnan(pdyn), np.nanmedian(pdyn), pdyn)
        modeled = dst_star + 7.26 * np.sqrt(pdyn) - 11.0
    else:
        modeled = dst_star

    out = df.copy()
    out["dst_model"] = modeled
    fname = out_name or file.rsplit("/", 1)[-1].replace(".csv", "_dstmodel.csv")
    fpath = data_path(fname)
    out.to_csv(fpath, index_label="time")
    result = {"file": str(fpath), "n_records": len(out),
              "model": "O'Brien & McPherron (2000), pressure-corrected"
                       if n is not None else "O'Brien & McPherron (2000), Dst* only",
              "model_min_nT": round(float(np.nanmin(modeled)), 1),
              "time_of_model_min": str(out.index[int(np.nanargmin(modeled))]),
              "artifacts": [str(fpath)]}
    if dst_column and dst_column in df.columns:
        obs = df[dst_column].astype(float)
        mask = obs.notna()
        mo, ob = modeled[mask.values], obs[mask].values
        result["skill"] = {
            "corr": round(float(np.corrcoef(mo, ob)[0, 1]), 3),
            "rmse_nT": round(float(np.sqrt(np.mean((mo - ob) ** 2))), 1),
            "obs_min_nT": round(float(np.nanmin(ob)), 1),
            "min_error_nT": round(float(np.nanmin(mo) - np.nanmin(ob)), 1),
        }
    return result


@tool(family="measure")
def cme_arrival(v0_kms: float, launch_time: str,
                w_kms: float = 450.0, gamma_per_km: float = 0.2e-7,
                r0_rs: float = 21.5, target_au: float = 1.0) -> dict:
    """Drag-based CME arrival estimate (Vrsnak et al. 2013 DBM).

    dv/dt = -gamma (v - w)|v - w|: the CME relaxes toward the ambient wind
    speed w. Analytic solution integrated from r0 (default 21.5 Rs, the
    DONKI CMEAnalysis reference height) to target_au.

    v0_kms: CME speed at r0 (use DONKI CMEAnalysis 'speed' for type=C/S/O).
    w_kms: ambient solar wind speed (350-450 slow, 550-650 in a stream).
    gamma_per_km: drag parameter, typically 0.1e-7 (wide/massive CME) to
    1e-7 (narrow/low-mass). An ensemble over gamma x w gives the arrival
    window — typical real accuracy is +/- 10 h; never quote minutes.
    """
    import math

    import numpy as np
    import pandas as pd

    if v0_kms <= 0 or not 0.01e-7 <= gamma_per_km <= 5e-7:
        return {"status": "error",
                "error": "refusing: need v0>0 and gamma in [0.01e-7, 5e-7] /km"}

    def transit_hours(v0, w, gamma):
        dist = target_au * AU_KM - r0_rs * RS_KM
        sign = 1.0 if v0 >= w else -1.0
        # r(t) = r0 + w t + sign/gamma * ln(1 + sign*gamma*(v0-w)*t)
        def r_of(t):
            return w * t + sign / gamma * math.log(1 + sign * gamma * (v0 - w) * t)
        lo, hi = 0.0, 3600 * 24 * 30
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if r_of(mid) < dist:
                lo = mid
            else:
                hi = mid
        t = 0.5 * (lo + hi)
        v_arr = w + (v0 - w) / (1 + sign * gamma * (v0 - w) * t)
        return t / 3600.0, v_arr

    t_best, v_arr = transit_hours(v0_kms, w_kms, gamma_per_km)
    ensemble = []
    for g in (0.1e-7, 0.2e-7, 0.5e-7, 1.0e-7):
        for w in (w_kms - 75, w_kms, w_kms + 75):
            ensemble.append(transit_hours(v0_kms, max(w, 250), g)[0])
    launch = pd.Timestamp(launch_time)
    arrival = launch + pd.Timedelta(hours=t_best)
    return {"launch_time": str(launch), "v0_kms": v0_kms,
            "transit_hours": round(t_best, 1),
            "arrival_estimate": str(arrival),
            "arrival_window": [str(launch + pd.Timedelta(hours=min(ensemble))),
                               str(launch + pd.Timedelta(hours=max(ensemble)))],
            "arrival_speed_kms": round(float(v_arr), 0),
            "assumptions": {"w_kms": w_kms, "gamma_per_km": gamma_per_km,
                            "r0_rs": r0_rs},
            "model": "drag-based model (Vrsnak et al. 2013); "
                     "typical accuracy +/- 10 h"}
