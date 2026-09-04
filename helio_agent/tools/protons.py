"""GOES integral proton flux: the >=E MeV channels behind the NOAA S-scale.

Two archives, split by era, both from NOAA NCEI:

* **1986 - 2020-03-04, GOES 8-15** - the EPEAD/HEPAD ``cpflux`` product
  carries genuine *measured* integral channels (``ZPGT1``..``ZPGT100``, east
  and west detectors, contamination-corrected). This is science-quality and
  archival; nothing is derived.
* **2020 - present, GOES 16-19** - SEISS/SGPS L2 archives 13 *differential*
  proton channels (1.02 - 404 MeV) plus a single **>500 MeV** integral
  channel. There is **no archived >10 MeV integral flux for the GOES-R
  era**: SWPC computes the operational one and serves only the last 7 days.
  So this tool integrates the differential spectrum itself and marks the
  result ``derived: true``. Treat those numbers as reconstructed, not as the
  SWPC operational product.

The derivation fits a **piecewise power law** through the 13 channel fluxes
at their effective (geometric-mean) energies and integrates it analytically::

    f(E) = f_k (E/E_k)^-g_k   on [E_k, E_k+1],  g_k = -ln(f_k+1/f_k)/ln(E_k+1/E_k)
    J(>Et) = sum_k int f(E) dE  from max(E_k, Et) to E_k+1

A naive ``sum_i f_i * dE_i`` over the channel bands is wrong here: the SGPS
bands **overlap** (ch3/ch4 at 5.8-6.5 MeV, ch8/ch9/ch10 at 96-118 MeV) and
leave **gaps** (138-153, 229-267, 390-500 MeV), so it double-counts at low
energy and drops flux at high energy. Against SWPC's operational product
that rectangular sum runs ~1.25x high at >10 MeV and ~0.36x low at >100 MeV;
the power-law integral lands at ~0.95x and fills the gaps.

Two deliberate choices, both restated in the result's ``note``:

* **The >500 MeV channel is not folded into the thresholds.** It is emitted
  as its own measured column ``p_gt500``. Folding it in would roughly double
  quiet-time ``p_gt10`` (the GCR background there is ~0.19 pfu against a
  ~0.25 pfu total) and would not match how SWPC defines its operational
  channels.
* Integration stops at the highest effective energy (~327-390 MeV); nothing
  is extrapolated past the last measured point.

Accuracy, measured against SWPC's operational 7-day product at **quiet GCR
background** (the pessimistic case): ``p_gt1``..``p_gt10`` land within
roughly 15% of the operational values, while ``p_gt30`` and above run ~2-3x
low because at background those channels are dominated by >390 MeV galactic
cosmic rays that SGPS's differential channels do not sample. During an SEP
event the solar spectrum dominates and that deficit collapses -- but read
quiet-time ``p_gt30+`` as a lower bound, not as a measurement.

Gotchas
-------
* Legacy ``cpflux`` is **5-minute only** - there is no 1-minute variant.
  Asking for ``resolution='1min'`` before 2020-03-05 is an error, not a
  silent downgrade.
* Legacy files are netCDF-3 classic (xarray ``scipy`` engine); GOES-R files
  are netCDF-4/HDF5 (``h5netcdf``). Opening one with the other's engine
  fails with "file signature not found".
* Legacy quality flags are non-zero on bad samples; those become NaN here.
* ``p_gt1`` starts at the lowest channel's effective energy, so it misses
  flux below ~1.4 MeV; treat it as ">~1 MeV".
* Both eras carry two oppositely-looking telescopes. ``sensor='max'``
  (default) takes the larger of the two per sample, which is what SWPC does
  for alerting; ``'mean'``, ``'east'``/``'west'`` (legacy) and
  ``'unit0'``/``'unit1'`` (GOES-R) select one.
* A window straddling 2020-03-04 spans two different instruments and two
  different provenance classes, so it is refused - fetch each era separately.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from helio_agent.http import cached_get
from helio_agent.registry import tool
from helio_agent.workspace import data_path

_NCEI_LEGACY = ("https://www.ncei.noaa.gov/data/goes-space-environment-monitor"
                "/access/avg")
_NCEI_GOESR = ("https://data.ngdc.noaa.gov/platforms/solar-space-observing-"
               "satellites/goes")

# Last day of the GOES-15 EPEAD archive; GOES-R SGPS takes over after it.
_ERA_SPLIT = datetime(2020, 3, 4, tzinfo=timezone.utc)

# Integral thresholds in MeV, matching the legacy ZPGT* channel set.
_THRESHOLDS_MEV = (1, 5, 10, 30, 50, 60, 100)


def _parse(ts: str, what: str) -> datetime:
    s = ts.strip().replace("Z", "+00:00")
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _listing(url: str) -> list[str]:
    """Directory entry names from an NCEI Apache index page."""
    r = cached_get(url, timeout=90, allow_error=True, ttl_seconds=24 * 3600)
    if getattr(r, "status_code", 200) >= 400:
        return []
    return [h for h in re.findall(r'href="([^"]+)"', r.text)
            if not h.startswith(("http", "?", "/", "mailto"))]


def _months(a: datetime, b: datetime) -> list[tuple[int, int]]:
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _days(a: datetime, b: datetime) -> list[datetime]:
    d, out = a.replace(hour=0, minute=0, second=0, microsecond=0), []
    while d <= b:
        out.append(d)
        d += timedelta(days=1)
    return out


def _sat_number(name: str) -> int:
    m = re.search(r"(\d+)", name)
    return int(m.group(1)) if m else -1


# --------------------------------------------------------------------------
# legacy: GOES 8-15 EPEAD corrected integral proton flux
# --------------------------------------------------------------------------

def _legacy_files(a: datetime, b: datetime, satellite: str | None) -> tuple:
    """(files, satellite) for the cpflux months covering [a, b]."""
    files, sat = [], satellite
    for y, m in _months(a, b):
        base = f"{_NCEI_LEGACY}/{y}/{m:02d}/"
        sats = [s.strip("/") for s in _listing(base) if s.endswith("/")]
        if not sats:
            continue
        if sat is None:
            sat = max(sats, key=_sat_number)
        if sat not in sats:
            return ([], f"{sat} has no data for {y}-{m:02d}; available: "
                        f"{', '.join(sorted(sats))}")
        for f in _listing(f"{base}{sat}/netcdf/"):
            if "_epead_cpflux_5m_" in f and f.endswith(".nc"):
                files.append(f"{base}{sat}/netcdf/{f}")
    return (files, sat)


def _read_legacy(url: str, sensor: str):
    """DataFrame of pfu columns from one monthly cpflux file."""
    import numpy as np
    import pandas as pd
    import xarray as xr

    from io import BytesIO
    r = cached_get(url, timeout=300)
    r.raise_for_status()
    ds = xr.open_dataset(BytesIO(r.content), engine="scipy", decode_times=False)
    idx = pd.to_datetime(ds["time_tag"].values, unit="ms")
    cols = {}
    for mev in _THRESHOLDS_MEV:
        legs = {}
        for side, tag in (("east", "E"), ("west", "W")):
            v, q = f"ZPGT{mev}{tag}", f"ZPGT{mev}{tag}_QUAL_FLAG"
            if v not in ds.variables:
                continue
            arr = np.asarray(ds[v].values, dtype="float64")
            if q in ds.variables:
                arr = np.where(np.asarray(ds[q].values) != 0, np.nan, arr)
            arr = np.where(arr < 0, np.nan, arr)
            legs[side] = arr
        if not legs:
            continue
        cols[f"p_gt{mev}"] = _combine(legs, sensor, np)
    ds.close()
    return pd.DataFrame(cols, index=idx)


def _combine(legs: dict, sensor: str, np):
    """Reduce the two telescopes to one series. All-NaN samples stay NaN."""
    if sensor in legs:
        return legs[sensor]
    import warnings

    stack = np.vstack([legs[k] for k in legs])
    allnan = np.all(np.isnan(stack), axis=0)
    with warnings.catch_warnings():   # all-NaN samples are handled below
        warnings.simplefilter("ignore", RuntimeWarning)
        out = (np.nanmean(stack, axis=0) if sensor == "mean"
               else np.nanmax(stack, axis=0))   # 'max' = SWPC alerting practice
    return np.where(allnan, np.nan, out)


def _powerlaw_integral(energy, flux, e_threshold, np):
    """Integrate a piecewise power law through (energy, flux) above e_threshold.

    energy: (n_chan,) effective energies in keV, ascending.
    flux:   (n_time, n_chan) differential flux, protons/(cm^2 sr keV s).
    Returns (n_time,) pfu. Integration stops at the highest effective energy;
    nothing is extrapolated beyond the last measured point.
    """
    total = np.zeros(flux.shape[0])
    for k in range(len(energy) - 1):
        a, b = float(energy[k]), float(energy[k + 1])
        if not (b > a):
            continue
        lo = max(a, e_threshold)
        if b <= lo:
            continue
        f1 = np.maximum(flux[:, k], 1e-30)
        f2 = np.maximum(flux[:, k + 1], 1e-30)
        gamma = -np.log(f2 / f1) / np.log(b / a)
        f_lo = f1 * (lo / a) ** (-gamma)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            seg = np.where(
                np.abs(1.0 - gamma) < 1e-6,
                f_lo * lo * np.log(b / lo),
                f_lo * lo / (1.0 - gamma) * ((b / lo) ** (1.0 - gamma) - 1.0))
        total += np.nan_to_num(seg, nan=0.0, posinf=0.0, neginf=0.0)
    return total


# --------------------------------------------------------------------------
# GOES-R: derive integral channels from the SGPS differential spectrum
# --------------------------------------------------------------------------

def _goesr_files(a: datetime, b: datetime, satellite: str | None,
                 res_tag: str) -> tuple:
    sats = [satellite] if satellite else ["goes19", "goes18", "goes17", "goes16"]
    wanted = {d.strftime("%Y%m%d") for d in _days(a, b)}
    for sat in sats:
        found, seen = [], set()
        for y, m in _months(a, b):
            base = (f"{_NCEI_GOESR}/{sat}/l2/data/sgps-l2-avg{res_tag}/"
                    f"{y}/{m:02d}/")
            for f in _listing(base):
                mt = re.search(r"_d(\d{8})_", f)
                if f.endswith(".nc") and mt and mt.group(1) in wanted:
                    found.append(base + f)
                    seen.add(mt.group(1))
        if seen == wanted:
            return (sorted(found), sat, None)
        if satellite:
            missing = sorted(wanted - seen)
            return ([], sat, f"{sat} SGPS is missing {len(missing)} day(s): "
                             f"{', '.join(missing[:5])}")
    return ([], None, "no GOES-R satellite covers the whole window; try a "
                      "narrower range or name `satellite` explicitly")


def _read_goesr(url: str, sensor: str):
    """DataFrame of derived pfu columns from one daily SGPS file."""
    import numpy as np
    import pandas as pd
    import xarray as xr

    from io import BytesIO
    r = cached_get(url, timeout=300)
    r.raise_for_status()
    ds = xr.open_dataset(BytesIO(r.content), engine="h5netcdf")
    var = ds["AvgDiffProtonFlux"]
    flux = np.asarray(var.values, dtype="float64")
    vmin = float(var.attrs.get("valid_min", 0.0))
    vmax = float(var.attrs.get("valid_max", np.inf))
    flux = np.where((flux < vmin) | (flux > vmax), np.nan, flux)
    eff = np.asarray(ds["DiffProtonEffectiveEnergy"].values, dtype="float64")
    tail = np.asarray(ds["AvgIntProtonFlux"].values, dtype="float64")
    tail = np.where(tail < 0, np.nan, tail)
    idx = pd.to_datetime(ds["time"].values)
    n_units = flux.shape[1]
    ds.close()

    cols = {}
    for mev in _THRESHOLDS_MEV:
        legs = {}
        for u in range(n_units):
            order = np.argsort(eff[u])
            f_u = flux[:, u, :][:, order]
            j = _powerlaw_integral(eff[u][order], f_u, mev * 1000.0, np)
            legs[f"unit{u}"] = np.where(
                np.all(np.isnan(f_u), axis=1), np.nan, j)
        cols[f"p_gt{mev}"] = _combine(legs, sensor, np)
    # The >500 MeV integral channel is measured, not derived: keep it as its
    # own column rather than folding it into the thresholds above.
    cols["p_gt500"] = _combine(
        {f"unit{u}": tail[:, u] for u in range(n_units)}, sensor, np)
    return pd.DataFrame(cols, index=idx)


# --------------------------------------------------------------------------
# tool
# --------------------------------------------------------------------------

@tool(family="retrieve")
def fetch_goes_protons(start: str, end: str, resolution: str = "5min",
                       satellite: str | None = None,
                       sensor: str = "max") -> dict:
    """Fetch GOES integral proton flux (pfu) for the NOAA S-scale channels.

    Writes a CSV indexed by 'time' with columns p_gt1, p_gt5, p_gt10, p_gt30,
    p_gt50, p_gt60, p_gt100 in pfu (protons cm^-2 s^-1 sr^-1) -- the columns
    characterize_sep expects, e.g. flux_10mev_column='p_gt10'. GOES-R files
    also carry p_gt500, the measured >500 MeV integral channel.

    Two eras, and the result says which was used:

    * start before 2020-03-05 -> GOES 8-15 EPEAD 'cpflux', a **measured,
      archival** integral product (5-minute only; resolution='1min' is an
      error here, not a downgrade). derived=False.
    * start after -> GOES 16-19 SEISS/SGPS L2, whose archive has no >10 MeV
      integral channel, so a piecewise power law through the 13 differential
      channels is integrated above each threshold. derived=True; these are
      reconstructed values, not the SWPC operational product. Against SWPC's
      operational feed at quiet background, p_gt1..p_gt10 agree to ~15%
      while p_gt30 and above run 2-3x low (GCR above the SGPS differential
      range) -- read those as a lower bound outside an SEP event.

    resolution: '1min' or '5min' (GOES-R only offers both; legacy is 5min).
    satellite: 'goes13', 'goes16', ... Default picks the highest-numbered
      spacecraft that covers the whole window.
    sensor: 'max' (default, the larger of the two oppositely-looking
      telescopes per sample -- SWPC alerting practice), 'mean', 'east'/'west'
      (legacy detector labels), or 'unit0'/'unit1' (GOES-R -X/+X telescopes,
      in file order; see the file's sgps_mx/px_instrument_id attributes).

    A window straddling 2020-03-04 is refused: it would mix instruments and
    mix measured with derived values in one file.
    """
    import pandas as pd

    try:
        a, b = _parse(start, "start"), _parse(end, "end")
    except ValueError as exc:
        return {"status": "error", "error": f"bad timestamp: {exc}"}
    if b <= a:
        return {"status": "error", "error": "end must be after start"}
    if resolution not in ("1min", "5min"):
        return {"status": "error",
                "error": "resolution must be '1min' or '5min'"}
    if sensor not in ("max", "mean", "east", "west", "unit0", "unit1"):
        return {"status": "error",
                "error": "sensor must be max, mean, east, west, unit0 or unit1"}

    legacy = a <= _ERA_SPLIT
    if legacy and b > _ERA_SPLIT:
        return {"status": "error",
                "error": "window straddles 2020-03-04, where GOES-15 EPEAD "
                         "(measured) ends and GOES-R SGPS (derived) begins; "
                         "fetch the two eras separately"}

    if legacy:
        if resolution == "1min":
            return {"status": "error",
                    "error": "GOES 8-15 cpflux is archived at 5-minute "
                             "cadence only; use resolution='5min'"}
        if sensor in ("unit0", "unit1"):
            return {"status": "error",
                    "error": "unit0/unit1 name the GOES-R telescopes; for "
                             "GOES 8-15 use sensor='east', 'west', 'max' "
                             "or 'mean'"}
        files, sat = _legacy_files(a, b, satellite)
        if not files:
            return {"status": "error",
                    "error": sat if isinstance(sat, str) and " " in str(sat)
                    else f"no EPEAD cpflux files for {start[:10]}..{end[:10]}"}
        frames = [_read_legacy(u, sensor) for u in files]
        source = f"NOAA NCEI GOES/EPEAD cpflux 5m ({sat})"
        derived, note = False, ("measured, contamination-corrected integral "
                                "channels; quality-flagged samples dropped")
    else:
        if sensor in ("east", "west"):
            return {"status": "error",
                    "error": "east/west name the GOES 8-15 detectors; for "
                             "GOES-R use sensor='unit0', 'unit1', 'max' "
                             "or 'mean'"}
        res_tag = "1m" if resolution == "1min" else "5m"
        files, sat, err = _goesr_files(a, b, satellite, res_tag)
        if not files:
            return {"status": "error", "error": err}
        frames = [_read_goesr(u, sensor) for u in files]
        source = f"NOAA NCEI GOES-R SEISS/SGPS L2 avg{res_tag} ({sat})"
        derived = True
        note = ("DERIVED: piecewise power law through the 13 SGPS "
                "differential channels, integrated above each threshold. Not "
                "the SWPC operational product. p_gt500 is the measured >500 "
                "MeV channel and is NOT folded into the other columns. "
                "p_gt1 misses flux below the lowest effective energy "
                "(~1.4 MeV). At quiet background p_gt30 and above run 2-3x "
                "low because GCR above ~390 MeV is unsampled by the "
                "differential channels; during an SEP event that deficit "
                "collapses.")

    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df[(df.index >= pd.Timestamp(a).tz_localize(None)) &
            (df.index <= pd.Timestamp(b).tz_localize(None))]
    if df.empty:
        return {"status": "error",
                "error": f"{source} returned no samples inside the window"}

    fname = re.sub(r"[^A-Za-z0-9_.-]+", "-",
                   f"GOES_protons_{sat}_{start[:10]}_{end[:10]}") + ".csv"
    fpath = data_path(fname)
    df.to_csv(fpath, index_label="time")
    return {"file": str(fpath), "n_records": len(df),
            "columns": list(df.columns), "satellite": sat,
            "resolution": resolution, "sensor": sensor,
            "source": source, "derived": derived, "note": note,
            "units": {c: "pfu" for c in df.columns},
            "n_files": len(files), "artifacts": [str(fpath)]}
