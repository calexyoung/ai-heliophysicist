"""Offline tests for the SWPC station-report consensus.

The live feed is exercised in validation/run_validation.py (case
`sunspots`). These pin the voting logic, which is where the honesty lives:
observatories disagree on 65% of region-days, and a tie must never be
silently resolved.
"""

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.sunspots import _zurich, consensus_from_reports


def rep(cls, obs, mag="B"):
    return {"spot_class": cls, "mag_class": mag, "observatory": obs}


@pytest.mark.parametrize("cls,expect", [
    ("Hax", "H"), ("cso", "C"), ("Fkc", "F"), ("Axx", "A"),
    ("Zxx", None), ("", None), (None, None), ("9ab", None),
])
def test_zurich(cls, expect):
    assert _zurich(cls) == expect


def test_unanimous_reports():
    c = consensus_from_reports("2026-09-04", 4521,
                               [rep("Hsx", "SVI"), rep("Hsx", "LEA")])
    assert c["zurich_consensus"] == "H"
    assert c["zurich_agreement"] == 1.0
    assert c["tie"] is False
    assert c["classes_disagree"] is False


def test_tie_refuses_to_pick():
    """The real 2026-09-04 AR4524 case: Cso vs Hax is C vs H, which is 18%
    against 5% for a C flare. Picking one would fabricate confidence."""
    c = consensus_from_reports("2026-09-04", 4524,
                               [rep("Cso", "SVI"), rep("Hax", "LEA", "A")])
    assert c["tie"] is True
    assert c["zurich_consensus"] is None
    assert c["zurich_votes"] == {"C": 1, "H": 1}
    assert c["zurich_agreement"] == 0.5


def test_majority_wins_without_a_tie():
    c = consensus_from_reports("2026-09-03", 4524,
                               [rep("Cso", "HOL"), rep("Hsx", "SVI"), rep("Hax", "LEA")])
    assert c["zurich_consensus"] == "H"
    assert c["zurich_agreement"] == pytest.approx(2 / 3, abs=1e-3)
    assert c["tie"] is False
    assert c["classes_disagree"] is True     # three distinct full classes


def test_same_zurich_different_full_class_is_still_agreement():
    """Hsx and Hax differ in the penumbral letter but not in the letter the
    flare rates use — that must read as Zurich agreement, class disagreement."""
    c = consensus_from_reports("2026-09-04", 4521,
                               [rep("Hsx", "SVI"), rep("Hax", "LEA")])
    assert c["zurich_consensus"] == "H"
    assert c["zurich_agreement"] == 1.0
    assert c["tie"] is False
    assert c["classes_disagree"] is True


def test_unclassifiable_reports_do_not_vote():
    c = consensus_from_reports("2026-09-04", 4599,
                               [rep("Hsx", "SVI"), rep("Zzz", "LEA")])
    assert c["zurich_votes"] == {"H": 1}
    assert c["zurich_consensus"] == "H"
    assert c["n_reports"] == 2               # both reports still counted


def test_observatories_are_preserved_for_audit():
    c = consensus_from_reports("2026-09-04", 4524,
                               [rep("Cso", "SVI"), rep("Hax", "LEA", "A")])
    assert c["by_observatory"] == {"SVI": "Cso", "LEA": "Hax"}
    assert c["mag_classes"] == ["A", "B"]


def test_out_of_window_date_refuses_with_coverage():
    r = run_tool("get_sunspot_reports", date="1999-01-01")
    assert r["status"] == "error"
    assert "rolling" in r["error"] and ".." in r["error"]
