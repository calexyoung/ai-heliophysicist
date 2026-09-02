"""Reduce: turn retrieved files into clean, analysis-ready series and maps.

These tools operate on files under workspace/data produced by retrieve tools.
All are deterministic transforms; no science judgment is embedded.
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import data_path


def _load_csv(file: str):
    import pandas as pd
    return pd.read_csv(file, index_col="time", parse_dates=True)


@tool(family="reduce")
def describe_series(file: str) -> dict:
    """Summarize a workspace time-series CSV: coverage, gaps, NaN fraction, ranges."""
    import numpy as np
    df = _load_csv(file)
    dt = df.index.to_series().diff().dt.total_seconds().dropna()
    cadence = float(dt.median()) if len(dt) else None
    gaps = int((dt > 3 * cadence).sum()) if cadence else 0
    cols = {}
    for c in df.columns:
        s = df[c]
        if np.issubdtype(s.dtype, np.number):
            cols[c] = {"nan_frac": round(float(s.isna().mean()), 4),
                       "min": float(np.nanmin(s)) if s.notna().any() else None,
                       "max": float(np.nanmax(s)) if s.notna().any() else None,
                       "mean": float(np.nanmean(s)) if s.notna().any() else None}
    return {"n_records": len(df),
            "time_range": [str(df.index[0]), str(df.index[-1])],
            "median_cadence_s": cadence, "n_gaps": gaps, "columns": cols}


@tool(family="reduce")
def resample_series(file: str, cadence: str, method: str = "mean",
                    out_name: str | None = None) -> dict:
    """Resample a time-series CSV to a uniform cadence ('1min','5min','1h','1D').

    method: 'mean', 'median', 'max', 'min'. NaNs ignored within bins; empty
    bins stay NaN (never interpolated silently — interpolate_gaps is explicit).
    """
    df = _load_csv(file)
    out = getattr(df.resample(cadence), method)()
    fname = out_name or file.rsplit("/", 1)[-1].replace(".csv", f"_{cadence}.csv")
    fpath = data_path(fname)
    out.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(out), "artifacts": [str(fpath)]}


@tool(family="reduce")
def merge_series(files: list[str], how: str = "outer", out_name: str = "merged.csv") -> dict:
    """Join multiple time-series CSVs on their time index (outer join by default)."""
    dfs = [_load_csv(f) for f in files]
    df = dfs[0].join(dfs[1:], how=how)
    fpath = data_path(out_name)
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "artifacts": [str(fpath)]}


@tool(family="reduce")
def interpolate_gaps(file: str, max_gap: str = "2h", out_name: str | None = None) -> dict:
    """Linearly interpolate NaNs, but only across gaps shorter than max_gap.

    Longer gaps are left as NaN so that data absence stays visible.
    """
    import pandas as pd
    df = _load_csv(file)
    limit = int(pd.Timedelta(max_gap) / (df.index[1] - df.index[0])) if len(df) > 1 else 1
    out = df.interpolate(method="time", limit=max(limit, 1), limit_area="inside")
    fname = out_name or file.rsplit("/", 1)[-1].replace(".csv", "_interp.csv")
    fpath = data_path(fname)
    out.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "interp_limit_points": limit, "artifacts": [str(fpath)]}


@tool(family="reduce")
def compute_derived(file: str, expression: str, out_column: str,
                    out_name: str | None = None) -> dict:
    """Add a derived column via a pandas eval expression over existing columns.

    Example: expression='sqrt(BX_GSE**2 + BY_GSE**2 + BZ_GSE**2)', out_column='Bmag'.
    Only numeric expressions over the file's columns are allowed (pandas.eval,
    no python execution).
    """
    df = _load_csv(file)
    df[out_column] = df.eval(expression)
    fname = out_name or file.rsplit("/", 1)[-1]
    fpath = data_path(fname)
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "columns": list(df.columns), "artifacts": [str(fpath)]}


@tool(family="reduce")
def shift_time(file: str, shift: str, out_name: str | None = None) -> dict:
    """Shift a series' time index by a fixed offset (e.g. '45min' L1→magnetopause lag).

    Use measure.propagation_delay to compute a physically motivated shift first.
    """
    import pandas as pd
    df = _load_csv(file)
    df.index = df.index + pd.Timedelta(shift)
    fname = out_name or file.rsplit("/", 1)[-1].replace(".csv", "_shifted.csv")
    fpath = data_path(fname)
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "shift": shift, "artifacts": [str(fpath)]}


@tool(family="reduce")
def load_solar_map(fits_file: str) -> dict:
    """Load a solar FITS file as a sunpy Map and report its metadata (no plot).

    Returns observatory, instrument, wavelength, time, scale — use
    report.plot_solar_map to render it.
    """
    import sunpy.map
    m = sunpy.map.Map(fits_file)
    return {"file": fits_file, "observatory": m.observatory, "instrument": m.instrument,
            "detector": m.detector, "wavelength": str(m.wavelength),
            "date": str(m.date), "dimensions": [int(d.value) for d in m.dimensions],
            "scale_arcsec_per_pix": [float(m.scale.axis1.value), float(m.scale.axis2.value)]}
