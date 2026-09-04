"""Offline tests for the McIntosh flare-probability lookup.

The published rate cells are checked in validation/run_validation.py
(case `flareprob`). These cover the table's internal shape, the Poisson
maths, and every refusal — all without network.
"""

import math

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.flareprob import (_COMPACT, _PENUMBRAL, _RATES_COM,
                                         _RATES_PEN, _RATES_ZUR, _ZURICH,
                                         poisson_probability, zurich_class)


@pytest.mark.parametrize("table,alphabet", [
    (_RATES_ZUR, _ZURICH), (_RATES_PEN, _PENUMBRAL), (_RATES_COM, _COMPACT),
])
def test_table_shape_is_complete(table, alphabet):
    """Three levels, one row per starting class, one column per ending class."""
    assert set(table) == {"C", "M", "X"}
    for lvl, rows in table.items():
        assert set(rows) == set(alphabet), lvl
        for start, row in rows.items():
            assert len(row) == len(alphabet), f"{lvl} {start}"


@pytest.mark.parametrize("table,alphabet", [
    (_RATES_ZUR, _ZURICH), (_RATES_PEN, _PENUMBRAL), (_RATES_COM, _COMPACT),
])
def test_empty_bins_are_identical_across_levels(table, alphabet):
    """A bin with no groups has no rate at any flare level — if the C table
    says a transition was never observed, M and X must agree."""
    for start in alphabet:
        for i in range(len(alphabet)):
            missing = {lvl: table[lvl][start][i] is None for lvl in ("C", "M", "X")}
            assert len(set(missing.values())) == 1, (start, alphabet[i], missing)


@pytest.mark.parametrize("table,alphabet", [
    (_RATES_ZUR, _ZURICH), (_RATES_PEN, _PENUMBRAL), (_RATES_COM, _COMPACT),
])
def test_rates_decrease_with_flare_magnitude(table, alphabet):
    """A group cannot produce X flares faster than M, or M faster than C."""
    for start in alphabet:
        for i in range(len(alphabet)):
            if table["C"][start][i] is None:
                continue
            c, m, x = (table[lvl][start][i][0] for lvl in ("C", "M", "X"))
            assert c >= m >= x, (start, alphabet[i], c, m, x)


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


def test_headline_probability_stays_the_zurich_value():
    """`probability` is documented as the Zurich figure; the other letters
    live in `components` and must not silently move the headline."""
    a = run_tool("flare_probability", mcintosh_class="Hax")
    b = run_tool("flare_probability", mcintosh_class="Hsx")
    assert a["levels"]["C"]["probability"] == b["levels"]["C"]["probability"]


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


def test_all_three_mcintosh_letters_are_read():
    """Hax and Hsx differ in the penumbral letter, and that letter has its own
    table — so they must no longer be identical (they were, when only the
    Zurich component was used)."""
    a = run_tool("flare_probability", mcintosh_class="Hax")
    s = run_tool("flare_probability", mcintosh_class="Hsx")
    ca, cs = a["levels"]["C"]["components"], s["levels"]["C"]["components"]
    assert ca["zurich"] == cs["zurich"]           # same first letter
    assert ca["compactness"] == cs["compactness"]  # same third letter
    assert ca["penumbral"] > cs["penumbral"]       # 'a' flares more than 's'
    assert a["levels"]["C"]["component_span"] != s["levels"]["C"]["component_span"]


def test_components_are_reported_not_multiplied():
    """Three marginal tables must never be combined into a product — that
    would imply independence the source does not establish."""
    r = run_tool("flare_probability", mcintosh_class="Fkc")
    c = r["levels"]["C"]
    prod = 1.0
    for v in c["components"].values():
        prod *= v
    assert abs(c["probability"] - prod) > 1e-6
    assert c["probability"] == c["components"]["zurich"]
    lo, hi = c["component_span"]
    assert lo <= c["probability"] <= hi


def test_component_span_brackets_every_available_component():
    r = run_tool("flare_probability", mcintosh_class="Cao")
    c = r["levels"]["C"]
    vals = [v for v in c["components"].values() if v is not None]
    assert c["component_span"] == [min(vals), max(vals)]


def test_short_class_still_works_with_missing_letters():
    """'H' alone has no penumbral or compactness letter; those come back
    unavailable with a reason rather than silently defaulting."""
    r = run_tool("flare_probability", mcintosh_class="H")
    assert r["status"] == "ok"
    cr = r["levels"]["C"]["component_rates"]
    assert cr["zurich"]["available"] is True
    assert cr["penumbral"]["available"] is False
    assert "no valid penumbral letter" in cr["penumbral"]["reason"]


def test_evolution_applies_per_component():
    """Each letter is looked up with its own previous letter."""
    r = run_tool("flare_probability", mcintosh_class="Dki", previous_class="Hsx")
    cr = r["levels"]["C"]["component_rates"]
    assert cr["zurich"]["previous"] == "H" and cr["zurich"]["letter"] == "D"
    assert cr["penumbral"]["previous"] == "S" and cr["penumbral"]["letter"] == "K"
    assert cr["compactness"]["previous"] == "X" and cr["compactness"]["letter"] == "I"
