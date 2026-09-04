"""Offline tests for the GOES integral-proton reduction.

No network: these exercise the two numerical pieces (`_powerlaw_integral`,
`_combine`) against analytic answers, and the tool's refusal paths.

The power-law integral is the whole point of the GOES-R path -- the SGPS
differential bands overlap and leave gaps, so a rectangular sum over band
widths double-counts at low energy and drops flux at high energy. On an
exact power law the piecewise integral must be exact.
"""

import math

import numpy as np
import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.protons import _combine, _powerlaw_integral


def analytic(f0, e0, gamma, a, b):
    """Integral of f0 (E/e0)^-gamma from a to b."""
    if abs(1 - gamma) < 1e-12:
        return f0 * e0 * math.log(b / a)
    return f0 * e0 / (1 - gamma) * ((b / e0) ** (1 - gamma) - (a / e0) ** (1 - gamma))


@pytest.mark.parametrize("gamma", [1.0, 2.0, 3.5, 4.7])
def test_powerlaw_integral_is_exact_on_a_power_law(gamma):
    e0, f0 = 1000.0, 5.0
    energy = np.logspace(3, 5.6, 13)                       # 1 MeV .. ~400 MeV
    flux = (f0 * (energy / e0) ** -gamma)[None, :]
    got = _powerlaw_integral(energy, flux, energy[0], np)[0]
    assert got == pytest.approx(analytic(f0, e0, gamma, energy[0], energy[-1]),
                                rel=1e-8)


def test_powerlaw_integral_threshold_inside_a_bin():
    """A threshold between grid points integrates the partial bin, not the
    whole one -- the failure mode a rectangular sum has by construction."""
    gamma, e0, f0 = 3.0, 1000.0, 2.0
    energy = np.array([1000.0, 10000.0, 100000.0])
    flux = (f0 * (energy / e0) ** -gamma)[None, :]
    et = 4000.0
    got = _powerlaw_integral(energy, flux, et, np)[0]
    assert got == pytest.approx(analytic(f0, e0, gamma, et, energy[-1]), rel=1e-8)
    # and it is strictly less than integrating the full first bin
    full = _powerlaw_integral(energy, flux, energy[0], np)[0]
    assert got < full


def test_powerlaw_integral_above_range_is_zero():
    energy = np.array([1000.0, 10000.0])
    flux = np.array([[1.0, 0.1]])
    assert _powerlaw_integral(energy, flux, 20000.0, np)[0] == 0.0


def test_powerlaw_integral_tolerates_zero_and_nan_channels():
    energy = np.array([1000.0, 10000.0, 100000.0])
    flux = np.array([[1.0, 0.0, np.nan]])
    got = _powerlaw_integral(energy, flux, 1000.0, np)[0]
    assert np.isfinite(got) and got > 0


def test_combine_modes():
    legs = {"unit0": np.array([1.0, 5.0, np.nan]),
            "unit1": np.array([3.0, 2.0, np.nan])}
    assert _combine(legs, "max", np).tolist()[:2] == [3.0, 5.0]
    assert _combine(legs, "mean", np).tolist()[:2] == [2.0, 3.5]
    assert _combine(legs, "unit1", np).tolist()[:2] == [3.0, 2.0]
    # a sample both telescopes missed stays missing rather than becoming 0
    assert np.isnan(_combine(legs, "max", np)[2])


def test_combine_keeps_one_sided_samples():
    legs = {"unit0": np.array([np.nan, 4.0]), "unit1": np.array([7.0, np.nan])}
    assert _combine(legs, "max", np).tolist() == [7.0, 4.0]


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(start="2020-01-01T00:00:00Z", end="2020-06-01T00:00:00Z"), "straddles"),
    (dict(start="2017-09-09T00:00:00Z", end="2017-09-10T00:00:00Z",
          resolution="1min"), "5-minute"),
    (dict(start="2017-09-09T00:00:00Z", end="2017-09-10T00:00:00Z",
          sensor="unit0"), "GOES-R telescopes"),
    (dict(start="2024-05-10T00:00:00Z", end="2024-05-11T00:00:00Z",
          sensor="east"), "GOES 8-15 detectors"),
    (dict(start="2024-05-10T00:00:00Z", end="2024-05-11T00:00:00Z",
          resolution="30min"), "1min"),
    (dict(start="2024-05-10T00:00:00Z", end="2024-05-10T00:00:00Z"), "after start"),
    (dict(start="not-a-date", end="2024-05-11T00:00:00Z"), "bad timestamp"),
])
def test_refusals_are_explicit(kwargs, fragment):
    """Every refusal names the reason -- no silent substitution (contract 2)."""
    r = run_tool("fetch_goes_protons", **kwargs)
    assert r["status"] == "error"
    assert fragment in r["error"], r["error"]
