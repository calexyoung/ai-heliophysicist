"""Offline tests for magnetogram_metrics on synthetic HMI-like maps.

Mirrors helio-agent's test_magnetogram: an 800 G bipole at disk center
with a vertical polarity-inversion line between the patches.
"""

import pytest

from helio_agent.registry import run_tool

sunpy_map = pytest.importorskip("sunpy.map")


def _plant(path, *, pos=(90, 100), neg=(100, 110), instrument="HMI", bunit="Gauss"):
    import astropy.units as u
    import numpy as np
    from astropy.coordinates import SkyCoord
    from sunpy.coordinates import Helioprojective

    data = np.zeros((200, 200))
    data[95:105, pos[0]:pos[1]] = 800.0
    data[95:105, neg[0]:neg[1]] = -800.0
    ref = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime="2024-05-08T01:01:30",
                   observer="earth", frame=Helioprojective)
    header = sunpy_map.make_fitswcs_header(
        data, ref, reference_pixel=[99.5, 99.5] * u.pix, scale=[2, 2] * u.arcsec / u.pix,
        instrument=instrument, telescope="SDO", unit=u.Unit("Gauss") if bunit == "Gauss" else None)
    header["BUNIT"] = bunit
    sunpy_map.Map(data, header).save(str(path), overwrite=True)
    return str(path)


def _run(file, **kw):
    kw.setdefault("plot", False)
    return run_tool("magnetogram_metrics", fits_file=file, **kw)


def test_measures_planted_bipole(tmp_path):
    out = _run(_plant(tmp_path / "hmi.fits"), lat_deg=0.0, lon_deg=0.0, half_deg=8.0)
    assert out["status"] == "ok"
    r = out["region"]
    assert r is not None
    # 200 pixels of |B| = 800 G: flux follows directly from the pixel size
    expected = 200 * 800.0 * (out["pixel_km"] * 1e5) ** 2
    assert out["disk_unsigned_flux_mx"] == pytest.approx(expected, rel=0.01)
    assert r["unsigned_flux_mx"] == pytest.approx(expected, rel=0.01)  # all flux in the box
    assert abs(r["signed_flux_mx"]) < 1e-6 * r["unsigned_flux_mx"]  # balanced bipole
    assert r["max_abs_b_g"] == 800.0
    assert r["pil_length_mm"] > 0 and r["pil_flux_mx"] > 0  # patches touch on a line
    assert r["n_pixels"] == 200
    assert 1400 < out["pixel_km"] < 1500  # 2 arcsec at 1 AU
    assert "strong PIL" in out["note"]


def test_separated_polarities_have_no_pil(tmp_path):
    out = _run(_plant(tmp_path / "sep.fits", pos=(60, 70), neg=(130, 140)),
               lat_deg=0.0, lon_deg=0.0, half_deg=15.0)
    r = out["region"]
    assert r["pil_length_mm"] == 0.0 and r["pil_flux_mx"] == 0.0
    assert r["unsigned_flux_mx"] > 0


def test_box_away_from_the_bipole_is_empty(tmp_path):
    # the planted map spans only +/-200 arcsec (~12 deg), so keep the box inside it
    out = _run(_plant(tmp_path / "off.fits"), lat_deg=0.0, lon_deg=8.0, half_deg=2.0)
    assert out["region"]["n_pixels"] == 0 and out["region"]["unsigned_flux_mx"] == 0.0


def test_full_disk_only(tmp_path):
    out = _run(_plant(tmp_path / "disk.fits"))
    assert out["region"] is None and out["disk_unsigned_flux_mx"] > 0
    assert "region" not in out["note"]


def test_refusals(tmp_path):
    out = _run("/nonexistent/missing.fits")
    assert out["status"] == "error" and "not found" in out["error"]
    out = _run(_plant(tmp_path / "aia.fits", instrument="XYZ"))
    assert out["status"] == "error" and "not an HMI" in out["error"]
    out = _run(_plant(tmp_path / "ic.fits", bunit="DN/s"))
    assert out["status"] == "error" and "not Gauss" in out["error"]
    out = _run(_plant(tmp_path / "half.fits"), lat_deg=0.0)
    assert out["status"] == "error" and "both" in out["error"]
    out = _run(_plant(tmp_path / "limb.fits"), lat_deg=0.0, lon_deg=89.0, half_deg=5.0)
    assert out["status"] == "error" and ("limb" in out["error"] or "outside" in out["error"])


def test_plot_written(tmp_path, monkeypatch):
    monkeypatch.setattr("helio_agent.tools.magnetogram.output_path", lambda n: tmp_path / n)
    out = _run(_plant(tmp_path / "p.fits"), lat_deg=0.0, lon_deg=0.0, plot=True)
    assert (tmp_path / "magnetogram.png").read_bytes().startswith(b"\x89PNG")
    assert out["artifacts"] == [out["file"]]
