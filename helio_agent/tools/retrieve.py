"""Retrieve: fetch actual mission data to the persistent workspace.

Every retrieval writes a file under workspace/data and returns its path plus a
summary. Downstream reduce/measure tools operate on those files, so a session
can be reconstructed entirely from disk + the audit trail.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import requests

from helio_agent.http import cached_get
from helio_agent.registry import tool
from helio_agent.workspace import data_path

_UA = {"User-Agent": "helio-agent/0.1 (AI Heliophysicist)"}


def _slug(*parts: str) -> str:
    s = "_".join(parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", s)


def _series_to_csv(df, path) -> None:
    df.to_csv(path, index_label="time")


def _cdaweb_coverage(dataset: str) -> tuple[str, str] | None:
    """(start, end) ISO coverage of a CDAWeb dataset, from the cached catalog.

    Returns None if the catalog lookup fails — coverage checking must never
    block a fetch on its own outage.
    """
    try:
        r = cached_get(
            "https://cdaweb.gsfc.nasa.gov/WS/cdasr/1/dataviews/sp_phys/datasets",
            params={"idPattern": dataset},
            headers={"Accept": "application/json"},
            timeout=60, ttl_seconds=24 * 3600)
        r.raise_for_status()
        for d in r.json().get("DatasetDescription", []):
            if d.get("Id") == dataset:
                ti = d.get("TimeInterval", {})
                if ti.get("Start") and ti.get("End"):
                    return (ti["Start"], ti["End"])
    except Exception:  # noqa: BLE001
        return None
    return None


@tool(family="retrieve")
def fetch_cdaweb_data(dataset: str, variables: list[str], start: str, end: str) -> dict:
    """Fetch time-series variables from a CDAWeb dataset into a CSV.

    dataset: CDAWeb ID, e.g. 'OMNI2_H0_MRG1HR', 'AC_H2_MFI', 'WI_H0_MFI'.
    variables: variable names from list_cdaweb_variables, e.g. ['DST1800'].
    start/end: ISO UTC times, e.g. '2003-10-28T00:00:00Z'.

    Fill values are replaced with NaN using the CDF FILLVAL attribute.
    """
    import numpy as np
    import pandas as pd
    from cdasws import CdasWs
    from cdasws.datarepresentation import DataRepresentation

    coverage = _cdaweb_coverage(dataset)
    if coverage is not None:
        c_start, c_end = coverage
        if end <= c_start or start >= c_end:
            return {"status": "error",
                    "error": f"refusing: requested window {start}..{end} is "
                             f"outside {dataset} coverage {c_start}..{c_end}; "
                             "pick a window inside coverage or a different "
                             "dataset (search_cdaweb_datasets)"}

    cdas = CdasWs()
    status, ds = cdas.get_data(dataset, variables, start, end,
                               dataRepresentation=DataRepresentation.XARRAY)
    if ds is None:
        return {"status": "error",
                "error": f"CDAWeb returned no data (http {status.get('http', {}).get('status_code')}); "
                         "check dataset ID, variable names, and time range"}
    frames = {}
    for var in variables:
        if var not in ds:
            continue
        da = ds[var]
        fill = da.attrs.get("FILLVAL")
        vals = da.values
        if fill is not None and np.issubdtype(np.asarray(vals).dtype, np.number):
            vals = np.where(np.isclose(vals.astype(float), float(fill)), np.nan, vals)
        time_coord = da.dims[0]
        idx = pd.DatetimeIndex(ds[time_coord].values)
        if vals.ndim == 1:
            frames[var] = pd.Series(vals, index=idx)
        else:
            for i in range(vals.shape[1]):
                frames[f"{var}_{i}"] = pd.Series(vals[:, i], index=idx)
    if not frames:
        return {"status": "error",
                "error": f"none of {variables} present in returned data; "
                         f"available: {list(ds.data_vars)}"}
    df = pd.DataFrame(frames)
    fname = _slug(dataset, start[:10], end[:10]) + ".csv"
    fpath = data_path(fname)
    _series_to_csv(df, fpath)
    units = {v: str(ds[v].attrs.get("UNITS", "")) for v in variables if v in ds}
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "units": units, "time_range": [str(df.index[0]), str(df.index[-1])],
            "artifacts": [str(fpath)]}


@tool(family="retrieve")
def fetch_omni(start: str, end: str, resolution: str = "1hour",
               variables: list[str] | None = None) -> dict:
    """Fetch OMNI near-Earth solar wind + activity indices (bow-shock-nose shifted).

    resolution: '1hour' (OMNI2_H0_MRG1HR) or '1min' (OMNI_HRO_1MIN).
    Default variables (1hour): B magnitude, Bz GSM, speed, density, Dst, Kp.
    """
    defaults = {
        "1hour": ["ABS_B1800", "BZ_GSM1800", "V1800", "N1800", "DST1800",
                  "KP1800", "Pressure1800"],
        "1min": ["F", "BZ_GSM", "flow_speed", "proton_density", "SYM_H", "Pressure"],
    }
    dataset = {"1hour": "OMNI2_H0_MRG1HR", "1min": "OMNI_HRO_1MIN"}.get(resolution)
    if dataset is None:
        return {"status": "error", "error": "resolution must be '1hour' or '1min'"}
    from helio_agent.registry import get_tool
    return get_tool("fetch_cdaweb_data").func(
        dataset=dataset, variables=variables or defaults[resolution],
        start=start, end=end)


@tool(family="retrieve")
def fetch_goes_xrs(start: str, end: str) -> dict:
    """Fetch GOES XRS 0.5-4 and 1-8 Angstrom X-ray flux (the flare irradiance record).

    Downloads science-quality XRS data via sunpy (NOAA archive) and writes a CSV
    with columns xrsa (0.5-4 A) and xrsb (1-8 A) in W/m^2.
    """
    import pandas as pd
    from sunpy.net import Fido, attrs as a
    from sunpy.timeseries import TimeSeries

    res = Fido.search(a.Time(start, end), a.Instrument("XRS"),
                      a.Resolution("flx1s") | a.Resolution("avg1m"))
    files = Fido.fetch(res, path=str(data_path("goes")) + "/{file}")
    if not files:
        return {"status": "error", "error": "no GOES XRS files found for that range"}
    ts = TimeSeries(files, concatenate=True)
    df = ts.to_dataframe()[["xrsa", "xrsb"]]
    df = df[(df.index >= pd.Timestamp(start).tz_localize(None)) &
            (df.index <= pd.Timestamp(end).tz_localize(None))]
    fname = _slug("GOES_XRS", start[:10], end[:10]) + ".csv"
    fpath = data_path(fname)
    _series_to_csv(df, fpath)
    return {"file": str(fpath), "n_records": len(df),
            "columns": list(df.columns), "units": {"xrsa": "W/m^2", "xrsb": "W/m^2"},
            "artifacts": [str(fpath)]}


@tool(family="retrieve")
def fetch_vso(start: str, end: str, instrument: str,
              wavelength_angstrom: float | None = None,
              max_files: int = 4, physobs: str | None = None,
              detector: str | None = None) -> dict:
    """Download solar data files (FITS) from the VSO into the workspace.

    Deliberately capped at max_files to avoid accidental bulk downloads;
    raise the cap explicitly for larger pulls.

    physobs: VSO physical-observable filter for instruments that serve
    several products, e.g. HMI: 'LOS_magnetic_field' (magnetogram),
    'intensity' (continuum), 'LOS_velocity' (Dopplergram). Without it an
    HMI query returns whichever product the archive lists first.

    detector: required for instruments with several detectors — LASCO is
    'C2' (2-6 Rsun) or 'C3' (3.7-30 Rsun); SECCHI is 'COR1'/'COR2'/'EUVI'.
    Without it a LASCO query mixes detectors and a coronagraph sequence
    built from the result will interleave two fields of view.
    """
    import astropy.units as u
    from sunpy.net import Fido, attrs as a

    query = [a.Time(start, end), a.Instrument(instrument)]
    if wavelength_angstrom is not None:
        query.append(a.Wavelength(wavelength_angstrom * u.angstrom))
    if physobs is not None:
        query.append(a.Physobs(physobs))
    if detector is not None:
        query.append(a.Detector(detector))
    res = Fido.search(*query)
    total = sum(len(t) for t in res)
    if total == 0:
        return {"status": "error", "error": "VSO search returned no records"}
    files = Fido.fetch(res[0, :max_files], path=str(data_path("vso")) + "/{file}")
    if len(files) == 0:
        # A search that matched but downloaded nothing is a failed retrieval,
        # not an empty one. Returning status ok with files: [] here made a
        # provider timeout look like "no data exists".
        return {"status": "error", "n_found": total, "n_downloaded": 0,
                "error": (f"VSO matched {total} record(s) but downloaded 0 "
                          "files; the provider refused or timed out. For AIA "
                          "the sdo7.nascom.nasa.gov export route is often "
                          "unusable — use fetch_aia_synoptic instead.")}
    return {"n_found": total, "n_downloaded": len(files),
            "files": [str(f) for f in files], "artifacts": [str(f) for f in files]}


_AIA_SYNOPTIC = "http://jsoc1.stanford.edu/data/aia/synoptic"
_AIA_SYNOPTIC_WAVES = (94, 131, 171, 193, 211, 304, 335, 1600, 1700, 4500)


@tool(family="retrieve")
def fetch_aia_synoptic(date: str, wavelength_angstrom: int = 171,
                       n_frames: int = 1, cadence_minutes: int = 2) -> dict:
    """Fetch AIA images from the JSOC synoptic archive (1024x1024, 2-min).

    date: ISO time of the first frame, e.g. '2024-05-08T05:10:00'. The
    archive is on a strict 2-minute grid, so the request is floored to the
    nearest even minute.

    These are level-1.5 SDO/AIA synoptic FITS: full disk, plate-scale
    ~2.4 arcsec/pix instead of the native 0.6, already registered and
    rotated to solar north. They are the right product for context imaging
    and morphology, and the wrong one for anything needing native
    resolution or the exact level-1 calibration chain (fine loop widths,
    photometry at the pixel level) — for those use fetch_vso, which serves
    the full-resolution level-1 records.

    This route exists because the VSO AIA export (sdo7.nascom.nasa.gov
    drms_export.cgi) routinely times out; the synoptic archive is plain
    static HTTP and answers in seconds.
    """
    import astropy.units as u  # noqa: F401  (kept for symmetry with fetch_vso)
    from datetime import timedelta

    wave = int(wavelength_angstrom)
    if wave not in _AIA_SYNOPTIC_WAVES:
        return {"status": "error",
                "error": (f"AIA synoptic archive has no {wave} A channel; "
                          f"available: {list(_AIA_SYNOPTIC_WAVES)}")}
    if n_frames < 1:
        return {"status": "error", "error": "n_frames must be >= 1"}
    if cadence_minutes % 2:
        return {"status": "error",
                "error": ("synoptic archive is on a 2-minute grid; "
                          "cadence_minutes must be even")}
    try:
        t0 = datetime.fromisoformat(date.replace("Z", "+00:00"))
    except ValueError as exc:
        return {"status": "error", "error": f"unparseable date: {exc}"}
    if t0.tzinfo is not None:
        t0 = t0.astimezone(timezone.utc).replace(tzinfo=None)
    t0 = t0.replace(minute=t0.minute - t0.minute % 2, second=0, microsecond=0)

    out_dir = data_path("aia_synoptic")
    out_dir.mkdir(parents=True, exist_ok=True)
    files, missing = [], []
    for i in range(int(n_frames)):
        t = t0 + timedelta(minutes=i * int(cadence_minutes))
        name = f"AIA{t:%Y%m%d_%H%M}_{wave:04d}.fits"
        url = (f"{_AIA_SYNOPTIC}/{t:%Y/%m/%d}/H{t.hour:02d}00/{name}")
        dest = out_dir / name
        if not dest.exists():
            r = requests.get(url, headers=_UA, timeout=120)
            if r.status_code != 200 or not r.content.startswith(b"SIMPLE"):
                missing.append(f"{t:%Y-%m-%dT%H:%M} (http {r.status_code})")
                continue
            dest.write_bytes(r.content)
        files.append(str(dest))
    if not files:
        return {"status": "error",
                "error": (f"no AIA {wave} A synoptic frames at {t0:%Y-%m-%dT%H:%M} "
                          f"+{n_frames} x {cadence_minutes} min: {missing}")}
    return {"n_requested": int(n_frames), "n_downloaded": len(files),
            "wavelength_angstrom": wave, "missing": missing,
            "level": "1.5 synoptic (1024x1024, ~2.4 arcsec/pix)",
            "files": files, "artifacts": files}


_AIA_L1_SERIES = {"euv": "aia.lev1_euv_12s", "uv": "aia.lev1_uv_24s",
                  "vis": "aia.lev1_vis_1h"}
_AIA_L1_BAND = {94: "euv", 131: "euv", 171: "euv", 193: "euv", 211: "euv",
                304: "euv", 335: "euv", 1600: "uv", 1700: "uv", 4500: "vis"}


@tool(family="retrieve")
def fetch_aia_level1(date: str, wavelength_angstrom: int = 171,
                     n_frames: int = 1, jsoc_email: str | None = None) -> dict:
    """Fetch full-resolution AIA level-1 FITS straight from JSOC via drms.

    4096x4096 at ~0.6 arcsec/pix — the native product, against the
    1024x1024 / ~2.4 arcsec/pix of `fetch_aia_synoptic`. Use this when the
    science needs native resolution or the level-1 calibration chain (loop
    widths, pixel photometry, precise flare morphology); use the synoptic
    route for context imaging, where it is ~10x smaller and much faster.

    Level 1 is NOT level 1.5: it is neither registered to solar north nor
    plate-scale normalised (CROTA2 is small but nonzero). Run
    `aiapy.calibrate.register` before comparing channels pixel to pixel, and
    `correct_aia_map` for the degradation correction.

    **Requires a JSOC-registered email address.** JSOC gates its export
    endpoint on one; register at http://jsoc.stanford.edu/ajax/register_email.html
    Pass it as `jsoc_email` or set `JSOC_EMAIL` in the project .env. Without
    it the tool refuses rather than silently falling back to a lower-
    resolution product.

    Uses method 'url_quick' with protocol 'as-is', which serves files already
    on disk at JSOC and returns immediately; a request that JSOC would have
    to stage is reported as such rather than waited on.
    """
    import os
    from datetime import timedelta

    email = (jsoc_email or os.environ.get("JSOC_EMAIL", "")).strip()
    if not email:
        return {"status": "error",
                "error": ("JSOC export needs a registered email; pass "
                          "jsoc_email or set JSOC_EMAIL in .env. Register at "
                          "http://jsoc.stanford.edu/ajax/register_email.html . "
                          "For context imagery without an account, use "
                          "fetch_aia_synoptic (level 1.5, 1024x1024).")}
    wave = int(wavelength_angstrom)
    band = _AIA_L1_BAND.get(wave)
    if band is None:
        return {"status": "error",
                "error": (f"no AIA level-1 series for {wave} A; available: "
                          f"{sorted(_AIA_L1_BAND)}")}
    if n_frames < 1:
        return {"status": "error", "error": "n_frames must be >= 1"}
    try:
        t0 = datetime.fromisoformat(date.replace("Z", "+00:00"))
    except ValueError as exc:
        return {"status": "error", "error": f"unparseable date: {exc}"}
    if t0.tzinfo is not None:
        t0 = t0.astimezone(timezone.utc).replace(tzinfo=None)

    cadence_s = {"euv": 12, "uv": 24, "vis": 3600}[band]
    span_s = cadence_s * int(n_frames)
    query = (f"{_AIA_L1_SERIES[band]}[{t0:%Y-%m-%dT%H:%M:%S}Z/{span_s}s]"
             f"[{wave}]{{image}}")

    import drms
    client = drms.Client(email=email)
    try:
        req = client.export(query, method="url_quick", protocol="as-is")
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": f"JSOC export refused: {exc}",
                "query": query}
    if req.status != 0 or len(req.urls) == 0:
        return {"status": "error", "query": query,
                "error": (f"JSOC returned status {req.status} with "
                          f"{len(req.urls)} url(s); 'as-is' only serves files "
                          "already staged at JSOC. Retry, or use "
                          "fetch_aia_synoptic.")}

    out_dir = data_path("aia_level1")
    out_dir.mkdir(parents=True, exist_ok=True)
    files, records = [], []
    for _, row in req.urls.iterrows():
        rec = str(row["record"])
        stamp = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\]", rec)
        name = _slug("AIA_lev1",
                     (stamp.group(1).replace(":", "").replace("-", "")
                      if stamp else f"{t0:%Y%m%dT%H%M%S}"),
                     f"{wave:04d}") + ".fits"
        dest = out_dir / name
        if not dest.exists():
            r = requests.get(str(row["url"]), headers=_UA, timeout=300)
            if r.status_code != 200 or not r.content.startswith(b"SIMPLE"):
                continue
            dest.write_bytes(r.content)
        files.append(str(dest))
        records.append(rec)
    if not files:
        return {"status": "error", "query": query,
                "error": "JSOC listed records but no FITS could be downloaded"}
    return {"n_requested": int(n_frames), "n_downloaded": len(files),
            "wavelength_angstrom": wave, "series": _AIA_L1_SERIES[band],
            "query": query, "records": records,
            "level": "1 (4096x4096, ~0.6 arcsec/pix; NOT registered — run "
                     "aiapy.calibrate.register for level 1.5)",
            "files": files, "artifacts": files}


_NOAA_SW = "https://archive.data.noaa.gov/satellite-spaceweather"
_DSCOVR_L2 = {
    "faraday_cup": ("DSCOVR/DSCOVR/FC/f1m", "f1m"),
    "magnetometer": ("DSCOVR/DSCOVR/MAG/m1m", "m1m"),
}


def _noaa_list(prefix: str) -> list[str]:
    """Keys under an archive.data.noaa.gov prefix (S3 path-style listing)."""
    import xml.etree.ElementTree as ET

    keys, token = [], None
    for _ in range(20):
        params = {"list-type": "2", "prefix": prefix, "max-keys": "1000"}
        if token:
            params["continuation-token"] = token
        r = cached_get(f"{_NOAA_SW}/", params=params, timeout=90)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
        keys += [e.text for e in root.findall(".//s3:Contents/s3:Key", ns)
                 if e.text]
        trunc = root.find("s3:IsTruncated", ns)
        token_el = root.find("s3:NextContinuationToken", ns)
        if trunc is None or trunc.text != "true" or token_el is None:
            break
        token = token_el.text
    return keys


@tool(family="retrieve")
def fetch_dscovr_l2(start: str, end: str, product: str = "faraday_cup",
                    variables: list[str] | None = None,
                    keep_suspect: bool = False) -> dict:
    """Fetch DSCOVR Level-2 science data from the NOAA NCEI archive.

    **This is the science-quality DSCOVR route, and it is not CDAWeb.**
    CDAWeb's only DSCOVR plasma product (`DSCOVR_H1_FC`) stops in June 2019,
    and its magnetometer product (`DSCOVR_H0_MAG`) carries GSE and RTN but
    no GSM — so neither can answer "what was Bz at L1 during a 2024 storm".
    NOAA's own archive carries both, Level 2, through the present.

    product:
      'faraday_cup'  — proton and alpha speed, density, temperature, and
                       velocity vectors in GSE and GSM (1-minute averages).
      'magnetometer' — bt, b{x,y,z} in GSE **and GSM**, with angles.

    variables: subset to keep. Default is the physically useful set for the
    product; pass names explicitly for anything else (the files also carry
    ~60 per-sample quality flags).

    keep_suspect: each sample carries `overall_quality` (0 normal, 1
    suspect, 2 error). Error samples are always dropped. Suspect samples are
    dropped too unless this is set — a storm is exactly when marginal
    samples appear, and silently averaging them in is how a saturated
    instrument reads as a measurement.

    Files are daily netCDF, gzipped, ~50 kB each. Where a day has been
    reprocessed the archive holds several, distinguished by their `p`
    timestamp; the newest is used and the others are reported.

    **The Faraday cup has a stated valid range** (`valid_min`/`valid_max` in
    the header, e.g. 189-1111 km/s for proton speed) and does struggle in
    extreme flux. Cross-check a storm peak against OMNI before quoting it.
    """
    import gzip
    from datetime import timedelta

    import pandas as pd

    if product not in _DSCOVR_L2:
        return {"status": "error",
                "error": (f"unknown product {product!r}; available: "
                          f"{sorted(_DSCOVR_L2)}")}
    prefix, tag = _DSCOVR_L2[product]
    try:
        t0 = datetime.fromisoformat(start.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError as exc:
        return {"status": "error", "error": f"unparseable time: {exc}"}
    for t in (t0, t1):
        if t.tzinfo is not None:
            t = t.astimezone(timezone.utc)
    t0 = t0.replace(tzinfo=None)
    t1 = t1.replace(tzinfo=None)
    if t1 <= t0:
        return {"status": "error", "error": "end must be after start"}

    default_vars = {
        "faraday_cup": ["proton_speed", "proton_density", "proton_temperature",
                        "proton_vx_gsm", "proton_vy_gsm", "proton_vz_gsm",
                        "alpha_density"],
        "magnetometer": ["bt", "bx_gsm", "by_gsm", "bz_gsm",
                         "bx_gse", "by_gse", "bz_gse"],
    }[product]
    wanted = list(variables) if variables else default_vars

    months = set()
    d = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    while d <= t1:
        months.add((d.year, d.month))
        d += timedelta(days=1)
    catalog: dict[str, list[str]] = {}
    for y, m in sorted(months):
        try:
            for k in _noaa_list(f"{prefix}/{y}/{m:02d}/"):
                base = k.rsplit("/", 1)[-1]
                if not base.startswith(f"oe_{tag}_dscovr_s"):
                    continue
                catalog.setdefault(base[len(f"oe_{tag}_dscovr_s"):][:8],
                                   []).append(k)
        except Exception as exc:  # noqa: BLE001
            return {"status": "error",
                    "error": f"NOAA archive listing failed for {y}-{m:02d}: {exc}"}
    if not catalog:
        return {"status": "error",
                "error": (f"no DSCOVR {product} files under {prefix} for "
                          f"{t0:%Y-%m} .. {t1:%Y-%m}; the archive starts in "
                          "2016")}

    out_dir = data_path("dscovr_l2")
    out_dir.mkdir(parents=True, exist_ok=True)
    frames, used, missing, superseded = [], [], [], 0
    d = t0.replace(hour=0, minute=0, second=0, microsecond=0)
    while d <= t1:
        day = f"{d:%Y%m%d}"
        cands = sorted(catalog.get(day, []))
        if not cands:
            missing.append(day)
            d += timedelta(days=1)
            continue
        superseded += len(cands) - 1
        key = cands[-1]                      # newest processing timestamp
        base = key.rsplit("/", 1)[-1]
        dest = out_dir / base[:-3]           # strip .gz
        if not dest.exists():
            r = requests.get(f"{_NOAA_SW}/{key}", headers=_UA, timeout=180)
            if r.status_code != 200:
                missing.append(f"{day} (http {r.status_code})")
                d += timedelta(days=1)
                continue
            dest.write_bytes(gzip.decompress(r.content))
        used.append(base)
        d += timedelta(days=1)

    if not used:
        return {"status": "error",
                "error": (f"no DSCOVR {product} file downloaded for "
                          f"{t0:%Y-%m-%d}..{t1:%Y-%m-%d}: {missing}")}

    import xarray as xr

    dropped_error = dropped_suspect = 0
    reduced_n = reduced_total = 0
    valid_ranges: dict[str, list] = {}
    for base in used:
        ds = xr.open_dataset(out_dir / base[:-3])
        have = [v for v in wanted if v in ds.variables]
        if not have:
            ds.close()
            return {"status": "error",
                    "error": (f"none of {wanted} are in the {product} file; "
                              f"available: {sorted(ds.data_vars)[:25]}")}
        df = ds[have].to_dataframe()
        for v in have:
            a = ds[v].attrs
            if "valid_min" in a and v not in valid_ranges:
                valid_ranges[v] = [float(a["valid_min"]), float(a["valid_max"])]
        # overall_quality is NOT sufficient on its own. During the May 2024
        # storm the Faraday cup reported ~470 km/s where every other L1
        # monitor reported ~1000, with overall_quality 0 throughout; the only
        # header signal was reduced_proton_quality_flag. Report its incidence
        # so a caller cannot miss it.
        if "reduced_proton_quality_flag" in ds.variables:
            rq = ds["reduced_proton_quality_flag"].to_series()
            reduced_n += int((rq == 1).sum())
            reduced_total += int(rq.size)
        if "overall_quality" in ds.variables:
            q = ds["overall_quality"].to_series()
            bad = q >= 2
            dropped_error += int(bad.sum())
            df = df[~bad.reindex(df.index, fill_value=False)]
            if not keep_suspect:
                susp = q == 1
                dropped_suspect += int(susp.sum())
                df = df[~susp.reindex(df.index, fill_value=False)]
        ds.close()
        frames.append(df)

    out = pd.concat(frames).sort_index()
    out.index = pd.to_datetime(out.index)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_convert("UTC").tz_localize(None)
    out = out.loc[(out.index >= t0) & (out.index <= t1)]
    if out.empty:
        return {"status": "error",
                "error": ("every sample in the requested window was dropped "
                          "as error/suspect quality; pass keep_suspect=True "
                          "to inspect them")}
    fname = _slug("DSCOVR_L2", tag, f"{t0:%Y-%m-%d}", f"{t1:%Y-%m-%d}") + ".csv"
    path = data_path(fname)
    _series_to_csv(out, path)
    return {"file": str(path), "product": product,
            "processing_level": "Level 2 (NOAA NCEI archive)",
            "n_records": int(len(out)),
            "time_range": [str(out.index[0]), str(out.index[-1])],
            "columns": list(out.columns),
            "files_used": used, "days_missing": missing,
            "superseded_reprocessings_skipped": superseded,
            "dropped_error_samples": dropped_error,
            "dropped_suspect_samples": (dropped_suspect if not keep_suspect
                                        else 0),
            "kept_suspect": bool(keep_suspect),
            "reduced_proton_quality_fraction": (
                round(reduced_n / reduced_total, 3) if reduced_total else None),
            "valid_ranges": valid_ranges,
            "note": ("NOAA NCEI Level 2, not CDAWeb: CDAWeb's DSCOVR_H1_FC "
                     "plasma stops in 2019 and DSCOVR_H0_MAG carries no GSM. "
                     + (("WARNING: reduced_proton_quality_flag is set on "
                         f"{reduced_n / reduced_total:.0%} of samples. "
                         "overall_quality does NOT catch this — on the May "
                         "2024 storm the cup read ~470 km/s against ~1000 "
                         "elsewhere while reporting quality 0. Cross-check "
                         "the speed against OMNI before quoting it.")
                        if reduced_total and reduced_n / reduced_total > 0.1
                        else "Cross-check a storm peak against OMNI and "
                             "valid_ranges.")),
            "artifacts": [str(path)]}


@tool(family="retrieve")
def fetch_helioviewer_image(date: str, layers: str = "[SDO,AIA,AIA,171,1,100]",
                            width: int = 1024, height: int = 1024,
                            image_scale: float = 2.4) -> dict:
    """Fetch a context image of the Sun from Helioviewer (PNG).

    date: ISO time, e.g. '2017-09-06T12:02:00'.
    layers: Helioviewer layer string; common choices:
        '[SDO,AIA,AIA,171,1,100]', '[SDO,AIA,AIA,304,1,100]',
        '[SOHO,LASCO,C2,white-light,1,100]', '[SDO,HMI,HMI,magnetogram,1,100]'.
    image_scale: arcsec/pixel (2.4 shows full disk at 1024px; ~10 for LASCO C2 field).

    Context imagery only — browse-quality JPEG2000-derived, not for photometry.
    """
    params = {
        "date": date if date.endswith("Z") else date + "Z",
        "layers": layers, "imageScale": image_scale,
        "x0": 0, "y0": 0, "width": width, "height": height,
        "display": "true", "watermark": "false",
    }
    r = cached_get("https://api.helioviewer.org/v2/takeScreenshot/",
                     params=params, timeout=120)
    r.raise_for_status()
    if not r.content.startswith(b"\x89PNG"):
        return {"status": "error", "error": f"Helioviewer error: {r.text[:300]}"}
    fname = _slug("helioviewer", date[:19], layers.strip("[]").replace(",", "-")) + ".png"
    fpath = data_path(fname)
    fpath.write_bytes(r.content)
    return {"file": str(fpath), "bytes": len(r.content), "artifacts": [str(fpath)]}


@tool(family="retrieve")
def fetch_spacecraft_ephemeris(spacecraft: list[str], start: str, end: str,
                               coordinate_system: str = "Gse") -> dict:
    """Fetch spacecraft trajectories from SSCWeb into a CSV (km).

    spacecraft: SSCWeb IDs (lowercase), e.g. ['ace', 'dscovr', 'themisa', 'mms1', 'iss'].
    coordinate_system: Gse, Gsm, Geo, Gm, Sm, GeiTod, GeiJ2000.
    """
    import pandas as pd
    from sscws.coordinates import CoordinateSystem
    from sscws.sscws import SscWs

    ssc = SscWs()
    coord = getattr(CoordinateSystem, coordinate_system.upper(), None)
    if coord is None:
        coord = CoordinateSystem(coordinate_system)
    result = ssc.get_locations(spacecraft, [start, end])
    frames = []
    for sat in result.get("Data", []):
        coords = sat["Coordinates"][0]
        idx = pd.DatetimeIndex([t for t in sat["Time"]])
        df = pd.DataFrame({
            f"{sat['Id']}_x_km": coords["X"],
            f"{sat['Id']}_y_km": coords["Y"],
            f"{sat['Id']}_z_km": coords["Z"],
        }, index=idx)
        frames.append(df)
    if not frames:
        return {"status": "error", "error": "SSCWeb returned no location data; check IDs with list_spacecraft"}
    df = frames[0].join(frames[1:], how="outer") if len(frames) > 1 else frames[0]
    fname = _slug("ephemeris", "-".join(spacecraft), start[:10]) + ".csv"
    fpath = data_path(fname)
    _series_to_csv(df, fpath)
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "coordinate_system": coordinate_system, "units": "km",
            "artifacts": [str(fpath)]}


def _hapi_csv_fallback(server: str, dataset: str, parameters: str,
                       start: str, end: str):
    """Read a HAPI server's /data CSV directly, bypassing hapiclient.

    Needed because hapiclient builds its numpy dtype straight from the
    declared parameter types and crashes on anything outside the HAPI spec's
    `double` / `integer` / `string` / `isotime`. ISWA (CCMC) declares
    `float`, which is not a HAPI type, so hapiclient raises `IndexError:
    tuple index out of range` inside `_compute_dt` for those datasets — a
    server-side spec violation, not a bad request. The CSV itself is
    well-formed, so parsing it directly recovers the data.
    """
    import pandas as pd

    info = cached_get(f"{server.rstrip('/')}/info", params={"id": dataset},
                      timeout=60, ttl_seconds=3600)
    info.raise_for_status()
    meta = info.json()
    declared = [p["name"] for p in meta.get("parameters", [])]
    wanted = [p.strip() for p in parameters.split(",") if p.strip()]
    names = ([declared[0]] + [n for n in wanted if n != declared[0]]
             if wanted else declared)
    r = cached_get(f"{server.rstrip('/')}/data",
                   params={"id": dataset, "parameters": ",".join(names[1:]) or None,
                           "time.min": start, "time.max": end, "format": "csv"},
                   timeout=180)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text), header=None)
    df.columns = names[:len(df.columns)]
    return df, meta


@tool(family="retrieve")
def fetch_hapi(server: str, dataset: str, parameters: str, start: str, end: str) -> dict:
    """Fetch time series from any HAPI-compliant server into a CSV.

    server: e.g. 'https://cdaweb.gsfc.nasa.gov/hapi'.
    parameters: comma-separated parameter names ('' for all).
    Useful for sources not covered by a dedicated tool.

    Falls back to reading the server's /data CSV directly when hapiclient
    cannot build a dtype from the declared metadata — some servers (ISWA)
    declare a `float` type the HAPI spec does not define. The result's
    `reader` field says which path was used.
    """
    import pandas as pd

    reader = "hapiclient"
    try:
        from hapiclient import hapi
        data, meta = hapi(server, dataset, parameters, start, end)
        names = [p["name"] for p in meta["parameters"]]
        df = pd.DataFrame(data)
        df.columns = names[:len(df.columns)]
    except Exception as exc:  # noqa: BLE001
        try:
            df, meta = _hapi_csv_fallback(server, dataset, parameters, start, end)
            reader = f"direct-csv (hapiclient failed: {type(exc).__name__})"
        except Exception as exc2:  # noqa: BLE001
            return {"status": "error",
                    "error": f"HAPI fetch failed for {dataset}: hapiclient "
                             f"{type(exc).__name__}: {exc}; direct CSV "
                             f"{type(exc2).__name__}: {exc2}"}
    if df.empty:
        return {"status": "error",
                "error": f"{dataset} returned no rows for {start}..{end}"}
    tcol = df.columns[0]
    df[tcol] = pd.to_datetime(df[tcol].str.decode("utf-8", errors="ignore")
                              if df[tcol].dtype == object else df[tcol],
                              utc=True)
    df = df.set_index(tcol)
    # Workspace CSVs are naive UTC by convention (fetch_omni, fetch_vso, ...).
    # HAPI hands back offset timestamps, and a tz-aware index cannot be joined
    # to a naive one, so normalise here rather than leaving every downstream
    # merge to discover it.
    df.index = df.index.tz_convert("UTC").tz_localize(None)
    fname = _slug("hapi", dataset, start[:10]) + ".csv"
    fpath = data_path(fname)
    _series_to_csv(df, fpath)
    return {"file": str(fpath), "n_records": len(df), "columns": list(df.columns),
            "reader": reader, "artifacts": [str(fpath)]}


@tool(family="retrieve")
def save_json(name: str, payload: dict | list) -> dict:
    """Persist a JSON-able result (e.g. an event list) to the workspace for later steps."""
    fname = _slug(name) + ".json"
    fpath = data_path(fname)
    fpath.write_text(json.dumps(payload, indent=2, default=str))
    return {"file": str(fpath), "artifacts": [str(fpath)]}


@tool(family="retrieve")
def fetch_cdaweb_spectrogram(start: str, end: str, dataset: str = "WI_K0_WAV",
                             variable: str = "E_Average") -> dict:
    """Fetch a 2-D (time x channel) CDAWeb variable, keeping the channel axis.

    The generic fetch_cdaweb_data flattens 2-D variables into anonymous
    `<var>_<i>` columns; a dynamic spectrum is useless without its frequency
    (or energy) axis. This writes one column per channel named `c<value>`
    from the variable's DEPEND_1 coordinate (e.g. `c268` ... `c10090000` for
    WIND/WAVES frequencies in Hz), so downstream tools recover the axis from
    the header alone.

    Default: WIND/WAVES key parameters `WI_K0_WAV` / `E_Average` — dB above
    background at 76 log-spaced frequencies (250 Hz to 10 MHz; RAD1, RAD2 and
    TNR receivers merged), ~3-min cadence, 1994-present. Fill (-1e31) becomes
    NaN. Returns file, channel values and units alongside the record count.
    """
    import numpy as np
    import pandas as pd
    from cdasws import CdasWs
    from cdasws.datarepresentation import DataRepresentation

    coverage = _cdaweb_coverage(dataset)
    if coverage is not None:
        c_start, c_end = coverage
        if end <= c_start or start >= c_end:
            return {"status": "error",
                    "error": f"refusing: requested window {start}..{end} is outside "
                             f"{dataset} coverage {c_start}..{c_end}"}
    cdas = CdasWs()
    status, ds = cdas.get_data(dataset, [variable], start, end,
                               dataRepresentation=DataRepresentation.XARRAY)
    if ds is None or variable not in ds:
        return {"status": "error",
                "error": f"CDAWeb returned no {variable} for {dataset} "
                         f"(http {status.get('http', {}).get('status_code')}); check "
                         "dataset ID, variable name (list_cdaweb_variables) and time range"}
    da = ds[variable]
    if da.ndim != 2:
        return {"status": "error",
                "error": f"{variable} is {da.ndim}-D, not a time x channel spectrogram; "
                         "use fetch_cdaweb_data for 1-D series"}
    fill = da.attrs.get("FILLVAL")
    vals = da.values.astype(float)
    if fill is not None:
        vals = np.where(np.isclose(vals, float(fill)), np.nan, vals)
    vals = np.where(np.abs(vals) >= 1e30, np.nan, vals)
    chan_dim = da.dims[1]
    channels = [float(c) for c in ds[chan_dim].values]
    idx = pd.DatetimeIndex(ds[da.dims[0]].values)
    cols = [f"c{c:g}" for c in channels]
    df = pd.DataFrame(vals, index=idx, columns=cols)
    fname = _slug(dataset, variable, start[:10], end[:10]) + ".csv"
    fpath = data_path(fname)
    _series_to_csv(df, fpath)
    return {"file": str(fpath), "n_records": len(df), "n_channels": len(channels),
            "channels": channels,
            "channel_units": str(ds[chan_dim].attrs.get("UNITS", "")),
            "units": str(da.attrs.get("UNITS", "")),
            "time_range": [str(df.index[0]), str(df.index[-1])],
            "artifacts": [str(fpath)]}
