"""SDO/AIA calibration: sensitivity degradation (aiapy).

AIA channels have lost sensitivity since 2010 — 304 A most severely (>90%).
Any quantitative use of AIA intensities across epochs MUST correct for this
or the comparison is silently wrong (see skills/missions/sdo.md).
"""

from __future__ import annotations

from helio_agent.registry import tool
from helio_agent.workspace import data_path

EUV_CHANNELS = (94, 131, 171, 193, 211, 304, 335)


@tool(family="reduce")
def aia_degradation(date: str, channels: list[int] | None = None) -> dict:
    """AIA sensitivity degradation factors at a date (aiapy, SSW calibration).

    Factor = fraction of launch (2010) sensitivity remaining; divide observed
    intensity by it to get corrected intensity. date: ISO. channels: EUV
    wavelengths in Angstrom (default: all seven).
    """
    import numpy as np
    import astropy.units as u
    from astropy.time import Time
    from aiapy.calibrate import degradation

    chans = channels or list(EUV_CHANNELS)
    bad = [c for c in chans if c not in EUV_CHANNELS]
    if bad:
        return {"status": "error",
                "error": f"refusing: {bad} are not AIA EUV channels {EUV_CHANNELS}"}
    factors = {}
    for ch in chans:
        d = degradation(ch * u.angstrom, Time(date))
        factors[str(ch)] = round(float(np.atleast_1d(d.value)[0]), 4)
    return {"date": date, "degradation_factors": factors,
            "meaning": "fraction of 2010 launch sensitivity remaining; "
                       "corrected = observed / factor",
            "source": "aiapy.calibrate.degradation (SSW calibration series)"}


@tool(family="reduce")
def correct_aia_map(fits_file: str, out_name: str | None = None) -> dict:
    """Apply the degradation correction to an AIA FITS file.

    Divides the image by the channel's degradation factor at its observation
    time and writes a corrected FITS. Use before any cross-epoch intensity
    comparison; pointless for single-epoch morphology.
    """
    import numpy as np
    import astropy.units as u
    from astropy.time import Time
    from aiapy.calibrate import degradation
    import sunpy.map

    m = sunpy.map.Map(fits_file)
    if (m.instrument or "").split()[0].upper() != "AIA":
        return {"status": "error",
                "error": f"refusing: {fits_file} is {m.instrument!r}, not AIA"}
    wave = int(m.wavelength.to_value(u.angstrom))
    if wave not in EUV_CHANNELS:
        return {"status": "error",
                "error": f"refusing: {wave} A is not an EUV channel (UV "
                         f"channels have no aiapy degradation series)"}
    d = float(np.atleast_1d(degradation(wave * u.angstrom, Time(m.date)).value)[0])
    corrected = sunpy.map.Map(m.data / d, m.meta)
    fname = out_name or fits_file.rsplit("/", 1)[-1].replace(".fits", "_degcorr.fits")
    fpath = data_path(fname)
    corrected.save(str(fpath), overwrite=True)
    return {"file": str(fpath), "channel_angstrom": wave,
            "degradation_factor": round(d, 4), "date": str(m.date),
            "artifacts": [str(fpath)]}
