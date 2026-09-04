"""Offline tests for the region-annotation helpers and refusal paths.

No network and no FITS: the projection itself is validated against analytic
spherical geometry in validation/run_validation.py (case `regions`). These
cover the parsing, the Mount Wilson code mapping, and every refusal.
"""

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.regions import _label, hale_greek, parse_location


@pytest.mark.parametrize("loc,expect", [
    ("N12E52", (12.0, -52.0)),
    ("S09W33", (-9.0, 33.0)),
    ("N08W79", (8.0, 79.0)),
    ("s10w120", (-10.0, 120.0)),
    ("  N00E00  ", (0.0, 0.0)),
    ("N27W073", (27.0, 73.0)),
])
def test_parse_location(loc, expect):
    assert parse_location(loc) == expect


@pytest.mark.parametrize("loc", ["", None, "N12", "X12E52", "N12Q52", "1252",
                                 "NNE52", "N12E52W3"])
def test_parse_location_rejects_junk(loc):
    assert parse_location(loc) is None


def test_hale_greek_maps_swpc_codes():
    assert hale_greek("BGD") == "βγδ"
    assert hale_greek("A") == "α"
    assert hale_greek("b") == "β"
    assert hale_greek(None) is None


def test_hale_greek_passes_unknown_codes_through_unchanged():
    """An unrecognised code is echoed, never guessed into a Greek letter."""
    assert hale_greek("ZZ") == "ZZ"


def test_label_modes():
    rec = {"region": 4524, "spot_class": "Hax", "mag_class": "A",
           "area_millionths": 80}
    assert _label(rec, "number") == "AR4524"
    assert _label(rec, "class") == "AR4524  Hax/α"
    assert "80µH" in _label(rec, "full")


def test_label_omits_class_when_swpc_reported_none():
    """SWPC nulls the classes for regions it stopped classifying; the label
    must fall back to the number rather than printing 'None/None'."""
    rec = {"region": 4518, "spot_class": None, "mag_class": None}
    assert _label(rec, "class") == "AR4518"
    assert "None" not in _label(rec, "full")


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(fits_file="/nonexistent/x.fits", regions=[{"region": 1, "location": "N00E00"}]),
     "FITS not found"),
    (dict(fits_file="/nonexistent/x.fits", label="bogus"), "label must be"),
])
def test_refusals_are_explicit(kwargs, fragment):
    r = run_tool("plot_solar_regions", **kwargs)
    assert r["status"] == "error"
    assert fragment in r["error"], r["error"]
