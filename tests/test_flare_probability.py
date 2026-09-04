"""Offline tests for the McIntosh flare-probability lookup.

The published rate cells are checked in validation/run_validation.py
(case `flareprob`). These cover the table's internal shape, the Poisson
maths, and every refusal — all without network.
"""

import math

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.flareprob import (_RATES, _ZURICH, poisson_probability,
                                         zurich_class)


def test_table_shape_is_complete():
    """Three levels, seven starting classes, seven ending columns each."""
    assert set(_RATES) == {"C", "M", "X"}
    for lvl, rows in _RATES.items():
        assert set(rows) == set(_ZURICH), lvl
        for start, row in rows.items():
            assert len(row) == len(_ZURICH), f"{lvl} {start}"


def test_empty_bins_are_identical_across_levels():
    """A bin with no groups has no rate at any flare level — if the C table
    says a transition was never observed, M and X must agree."""
    for start in _ZURICH:
        for i in range(len(_ZURICH)):
            missing = {lvl: _RATES[lvl][start][i] is None for lvl in ("C", "M", "X")}
            assert len(set(missing.values())) == 1, (start, _ZURICH[i], missing)


def test_rates_decrease_with_flare_magnitude():
    """A group cannot produce X flares faster than M, or M faster than C."""
    for start in _ZURICH:
        for i in range(len(_ZURICH)):
            if _RATES["C"][start][i] is None:
                continue
            c, m, x = (_RATES[lvl][start][i][0] for lvl in ("C", "M", "X"))
            assert c >= m >= x, (start, _ZURICH[i], c, m, x)


@pytest.mark.parametrize("cls,expect", [
    ("Hax", "H"), ("cao", "C"), ("Fkc", "F"), ("  dai ", "D"),
    ("Zxx", None), ("", None), (None, None), ("123", None),
])
def test_zurich_class(cls, expect):
    assert zurich_class(cls) == expect


def test_poisson_probability():
    assert poisson_probability(0.0, 24) == 0.0
    assert poisson_probability(0.68, 24) == pytest.approx(1 - math.exp(-0.68))
    assert poisson_probability(0.68, 48) == pytest.approx(1 - math.exp(-1.36))
    assert poisson_probability(-1.0, 24) == 0.0          # clipped, never negative
    # A huge rate saturates at exactly 1.0 in float64 and must never exceed it.
    assert poisson_probability(100.0, 24) == 1.0
    assert 0.0 <= poisson_probability(3.5, 24) <= 1.0


def test_penumbral_and_compactness_letters_do_not_change_the_answer():
    """Documented limitation: only the first letter is resolved, so these
    must agree exactly — the tool must not imply a precision it lacks."""
    a = run_tool("flare_probability", mcintosh_class="Hax")
    b = run_tool("flare_probability", mcintosh_class="Hsx")
    assert a["levels"] == b["levels"]


def test_window_scales_the_probability():
    day = run_tool("flare_probability", mcintosh_class="Dxx")
    two = run_tool("flare_probability", mcintosh_class="Dxx", window_hours=48)
    assert two["levels"]["C"]["probability"] > day["levels"]["C"]["probability"]


def test_evolution_changes_the_answer():
    """The paper's headline: growth into a class flares more than persistence."""
    grew = run_tool("flare_probability", mcintosh_class="Dxx", previous_class="Hxx")
    held = run_tool("flare_probability", mcintosh_class="Dxx", previous_class="Dxx")
    assert grew["levels"]["C"]["rate_per_24h"] > held["levels"]["C"]["rate_per_24h"]
    assert held["assumed_no_evolution"] is False


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(mcintosh_class="Zxx"), "Zurich"),
    (dict(mcintosh_class="Hax", previous_class="Q"), "previous_class"),
    (dict(mcintosh_class="Axx", previous_class="Exx"), "no groups"),
    (dict(mcintosh_class="Hax", window_hours=0), "window_hours"),
    (dict(mcintosh_class="Hax", window_hours=200), "window_hours"),
])
def test_refusals_are_explicit(kwargs, fragment):
    r = run_tool("flare_probability", **kwargs)
    assert r["status"] == "error"
    assert fragment in r["error"], r["error"]
