"""pySPEDAS-backed tools: mission-aware loaders for in-situ space physics data.

pySPEDAS wraps each mission's own load logic (calibration selections, variable
naming, probe handling) for 30+ projects — MMS, THEMIS, ERG, Cluster, PSP,
Solar Orbiter, and more. Prefer it over raw fetch_cdaweb_data when a mission
loader exists (see skills/tools/pyspedas_pytplot.md); the outputs land in the
same workspace CSV format as every other retrieve tool.
"""

from __future__ import annotations

import os

from helio_agent.registry import tool
from helio_agent.workspace import data_path


def _pyspedas():
    # Keep pySPEDAS's own file cache inside the persistent workspace.
    os.environ.setdefault("SPEDAS_DATA_DIR", str(data_path("pyspedas")))
    import pyspedas
    return pyspedas


def _project(pyspedas, mission: str):
    projects = getattr(pyspedas, "projects", pyspedas)
    mod = getattr(projects, mission.lower(), None) or getattr(pyspedas, mission.lower(), None)
    if mod is None:
        raise KeyError(f"pySPEDAS has no project {mission!r}; "
                       "see list_pyspedas_missions")
    return mod


@tool(family="discover")
def list_pyspedas_missions() -> dict:
    """List mission projects supported by pySPEDAS (usable with fetch_pyspedas)."""
    pyspedas = _pyspedas()
    projects = getattr(pyspedas, "projects", pyspedas)
    names = sorted(n for n in dir(projects)
                   if not n.startswith("_") and hasattr(getattr(projects, n), "__path__"))
    return {"n_results": len(names), "missions": names}


@tool(family="discover")
def list_pyspedas_loaders(mission: str) -> dict:
    """List the instrument load routines a pySPEDAS mission project provides.

    mission: e.g. 'mms', 'themis', 'ace', 'wind', 'psp', 'solo', 'erg', 'cluster'.
    """
    pyspedas = _pyspedas()
    mod = _project(pyspedas, mission)
    loaders = sorted(n for n in dir(mod)
                     if not n.startswith("_") and callable(getattr(mod, n)))
    return {"mission": mission, "n_results": len(loaders), "loaders": loaders}


@tool(family="retrieve")
def fetch_pyspedas(mission: str, instrument: str, start: str, end: str,
                   probe: str | None = None, datatype: str | None = None,
                   variables: list[str] | None = None,
                   max_columns: int = 24) -> dict:
    """Load data through a pySPEDAS mission loader and save it as a workspace CSV.

    mission/instrument: project + load routine, e.g. ('mms','fgm'),
    ('themis','fgm'), ('ace','mfi'), ('psp','fields'). Discover names with
    list_pyspedas_missions / list_pyspedas_loaders.
    probe: for multi-probe missions ('1'-'4' MMS, 'a'-'e' THEMIS).
    datatype: loader-specific product selection (see the loader's docstring).
    variables: keep only these tplot variables (default: all loaded, up to
    max_columns flattened columns — spectrogram-like 2-D variables are skipped).

    Uses each mission's own calibration/variable logic — prefer this over raw
    CDAWeb pulls for MMS, THEMIS, ERG, Cluster. Level-2 products only unless
    the mission skill says otherwise.
    """
    import numpy as np
    import pandas as pd

    pyspedas = _pyspedas()
    get_data = pyspedas.get_data  # pytplot lives inside pyspedas since 2.x
    mod = _project(pyspedas, mission)
    loader = getattr(mod, instrument, None)
    if loader is None:
        return {"status": "error",
                "error": f"no loader {instrument!r} in project {mission!r}; "
                         f"see list_pyspedas_loaders"}
    kwargs: dict = {"trange": [start, end]}
    if probe is not None:
        kwargs["probe"] = probe
    if datatype is not None:
        kwargs["datatype"] = datatype
    tvars = loader(**kwargs)
    if not tvars:
        return {"status": "error",
                "error": "loader returned no tplot variables; check time range, "
                         "probe, and datatype against the mission skill"}
    if variables:
        missing = [v for v in variables if v not in tvars]
        if missing:
            return {"status": "error",
                    "error": f"variables not loaded: {missing}; loaded: {list(tvars)}"}
        tvars = variables

    frames: dict[str, pd.Series] = {}
    skipped: list[str] = []
    for var in tvars:
        if len(frames) >= max_columns:
            skipped.append(var)
            continue
        d = get_data(var)
        if d is None or not hasattr(d, "y"):
            skipped.append(var)
            continue
        y = np.asarray(d.y)
        if not np.issubdtype(y.dtype, np.number):
            skipped.append(var)
            continue
        idx = pd.to_datetime(np.asarray(d.times), unit="s")
        if y.ndim == 1:
            frames[var] = pd.Series(y, index=idx)
        elif y.ndim == 2 and y.shape[1] <= 6:
            for i in range(y.shape[1]):
                frames[f"{var}_{i}"] = pd.Series(y[:, i], index=idx)
        else:
            skipped.append(var)  # spectrogram-like; needs a dedicated tool
    if not frames:
        return {"status": "error",
                "error": f"no scalar/vector variables convertible; skipped {skipped}"}
    df = pd.DataFrame(frames).sort_index()
    units = {}
    for var in tvars:
        try:
            meta = get_data(var, metadata=True) or {}
            units[var] = str(meta.get("plot_options", {}).get("yaxis_opt", {})
                             .get("axis_label", ""))
        except Exception:  # noqa: BLE001 - units are best-effort metadata
            pass
    import re
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-",
                  f"{mission}_{instrument}{'_' + probe if probe else ''}_{start[:10]}")
    fpath = data_path(slug + ".csv")
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "units": units, "skipped_variables": skipped,
            "time_range": [str(df.index[0]), str(df.index[-1])],
            "artifacts": [str(fpath)]}
