"""Offline tests for the coronagraph tools.

The live LASCO path is exercised in validation (case `corona`). These cover
the height-time fit against an analytic answer and every refusal — no
network.
"""

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools.coronagraph import RSUN_KM


def _times(hours):
    return [f"2024-05-08T{6 + int(h):02d}:{int((h % 1) * 60):02d}:00Z"
            for h in hours]


def test_height_time_recovers_a_known_constant_speed():
    """A front at exactly 1000 km/s must fit to 1000 km/s."""
    v = 1000.0
    hours = [0.0, 0.5, 1.0, 1.5, 2.0]
    heights = [2.0 + v * (h * 3600) / RSUN_KM for h in hours]
    r = run_tool("cme_height_time", times=_times(hours),
                 heights_rsun=heights)
    assert r["status"] == "ok"
    assert r["speed_km_s"] == pytest.approx(v, rel=1e-6)
    assert r["r_squared"] == pytest.approx(1.0, abs=1e-9)
    assert r["speed_error_km_s"] == pytest.approx(0.0, abs=1e-3)


def test_height_time_reports_acceleration_when_present():
    hours = [0.0, 0.5, 1.0, 1.5, 2.0]
    heights = [2.0 + 3.0 * h + 0.5 * h ** 2 for h in hours]
    r = run_tool("cme_height_time", times=_times(hours), heights_rsun=heights)
    assert r["acceleration_m_s2"] is not None
    assert r["acceleration_m_s2"] > 0


def test_height_time_extrapolates_launch_before_first_point():
    import pandas as pd
    hours = [0.0, 1.0, 2.0]
    heights = [3.0, 6.0, 9.0]
    r = run_tool("cme_height_time", times=_times(hours), heights_rsun=heights)
    launch = pd.Timestamp(r["extrapolated_launch_1rsun"])
    assert launch < pd.Timestamp("2024-05-08T06:00:00Z")


def test_height_time_flags_plane_of_sky_as_a_lower_bound():
    r = run_tool("cme_height_time", times=_times([0.0, 1.0, 2.0]),
                 heights_rsun=[3.0, 6.0, 9.0])
    assert r["plane_of_sky"] is True
    assert "LOWER BOUND" in r["note"]


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(times=["2024-05-08T06:00:00Z"], heights_rsun=[3.0]), "at least 3"),
    (dict(times=["2024-05-08T06:00:00Z", "2024-05-08T07:00:00Z"],
          heights_rsun=[3.0]), "but"),
    (dict(times=_times([0.0, 1.0, 2.0]), heights_rsun=[6.0, 3.0, 9.0]),
     "monotonically increasing"),
])
def test_height_time_refusals(kwargs, fragment):
    r = run_tool("cme_height_time", **kwargs)
    assert r["status"] == "error"
    assert fragment in r["error"], r["error"]


def test_sequence_refuses_a_single_frame():
    r = run_tool("plot_coronagraph_sequence", files=["/nonexistent.fts"])
    assert r["status"] == "error"
    assert "at least 2" in r["error"]


def test_sequence_refuses_unreadable_files():
    r = run_tool("plot_coronagraph_sequence",
                 files=["/nonexistent_a.fts", "/nonexistent_b.fts"])
    assert r["status"] == "error"
    assert "could not read" in r["error"]


def test_config_refuses_mismatched_speed_list():
    r = run_tool("plot_heliospheric_config", date="2024-05-10 12:00:00",
                 bodies=["Earth", "STEREO-A"], body_speeds_kms=[400.0])
    assert r["status"] == "error"
    if "not installed" in r["error"]:
        # solarmach is an optional extra (`uv sync --extra extra`). A plain
        # `uv sync` removes it, which is easy to do accidentally during a
        # release. Skip rather than fail: the tool still refuses correctly,
        # just for a different reason than this test is checking.
        pytest.skip("solarmach not installed (optional extra)")
    assert "one per body" in r["error"]
