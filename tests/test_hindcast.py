"""Offline tests for hindcast_forecasts on a planted DONKI record.

The planted week has three CMEs: an Earth-directed fast one whose drag
window contains an Earth IPS shock (hit) and covers a G4 storm, a slow
Earth-directed one with no shock (false alarm), and a limb CME the cone
test must exclude. DONKI access is stubbed at helio_agent.tools.hindcast.run_tool.
"""

import pytest

from helio_agent.registry import run_tool
from helio_agent.tools import hindcast as hc

ANALYSES = [
    # fast, near disk center: two fits, the monitor takes the faster
    {"associatedCMEID": "2024-05-08T22:24:00-CME-001", "time21_5": "2024-05-08T23:30Z",
     "latitude": -10.0, "longitude": 5.0, "halfAngle": 45.0, "speed": 1200.0, "type": "S"},
    {"associatedCMEID": "2024-05-08T22:24:00-CME-001", "time21_5": "2024-05-08T23:45Z",
     "latitude": -10.0, "longitude": 5.0, "halfAngle": 40.0, "speed": 1000.0, "type": "C"},
    # slow, Earth-directed, no shock follows
    {"associatedCMEID": "2024-05-03T04:12:00-CME-001", "time21_5": "2024-05-03T06:00Z",
     "latitude": 5.0, "longitude": -20.0, "halfAngle": 25.0, "speed": 450.0, "type": "C"},
    # limb: excluded by the cone test
    {"associatedCMEID": "2024-05-05T10:00:00-CME-001", "time21_5": "2024-05-05T11:00Z",
     "latitude": 0.0, "longitude": 85.0, "halfAngle": 30.0, "speed": 1500.0, "type": "S"},
    # geometry unknown: the live rule cannot forecast it
    {"associatedCMEID": "2024-05-06T01:00:00-CME-001", "time21_5": "2024-05-06T02:00Z",
     "latitude": None, "longitude": None, "halfAngle": None, "speed": 900.0, "type": "C"},
]
IPS = [{"activityID": "2024-05-10T16:37:00-IPS-001", "eventTime": "2024-05-10T16:37Z",
        "location": "Earth", "instruments": []},
       {"activityID": "2024-05-11T00:00:00-IPS-002", "eventTime": "2024-05-11T00:00Z",
        "location": "STEREO A", "instruments": []}]
GST = [{"gstID": "2024-05-10T15:00:00-GST-001", "startTime": "2024-05-10T15:00Z",
        "allKpIndex": [{"kpIndex": 7.67}, {"kpIndex": 9.0}, {"kpIndex": 8.33}]},
       {"gstID": "2024-05-02T12:00:00-GST-001", "startTime": "2024-05-02T12:00Z",
        "allKpIndex": [{"kpIndex": 5.33}]}]


@pytest.fixture
def donki(monkeypatch):
    calls = []

    def fake(name, **kw):
        assert name == "search_donki"
        calls.append(kw)
        events = {"CMEAnalysis": ANALYSES, "IPS": IPS, "GST": GST}[kw["kind"]]
        return {"status": "ok", "n_results": len(events), "events": list(events)}

    monkeypatch.setattr(hc, "run_tool", fake)
    return calls


def _run(**kw):
    kw.setdefault("plot", False)
    return run_tool("hindcast_forecasts", start="2024-05-01", end="2024-05-12", **kw)


def test_class_for_kp_ladder():
    assert hc.class_for_kp(9.0) == "superstorm"
    assert hc.class_for_kp(8.33) == "severe"
    assert hc.class_for_kp(7.0) == "intense"
    assert hc.class_for_kp(5.67) == "moderate"
    assert hc.class_for_kp(4.0) == "below-moderate"


def test_confidence_tiers():
    assert hc.confidence_for(1200.0, 5.0) == "high"
    assert hc.confidence_for(1200.0, 50.0) == "moderate"
    assert hc.confidence_for(800.0, 10.0) == "moderate"
    assert hc.confidence_for(800.0, None) == "low"
    assert hc.confidence_for(450.0, 0.0) == "low"


def test_replays_the_live_rule(donki):
    out = _run()
    assert out["status"] == "ok"
    assert out["n_cmes"] == 4 and out["n_earth_directed"] == 2  # limb + unknown dropped
    fast = next(f for f in out["forecasts"] if f["v0_kms"] == 1200.0)
    assert fast["launch"] == "2024-05-08T23:30Z"  # the faster of the two fits
    assert fast["outcome"] == "hit" and fast["ips_id"].endswith("IPS-001")
    assert fast["confidence"] == "high"
    assert abs(fast["timing_error_hours"]) < 24
    slow = next(f for f in out["forecasts"] if f["v0_kms"] == 450.0)
    assert slow["outcome"] == "false_alarm" and slow["confidence"] == "low"
    assert out["n_hits"] == 1 and out["n_false_alarms"] == 1 and out["hit_rate"] == 0.5
    assert out["hit_mae_hours"] == abs(fast["timing_error_hours"])
    assert "1 hits, 1 false alarms" in out["note"]


def test_window_matches_the_monitor_tool(donki):
    """The hindcast window must be exactly what cme_arrival gives the monitor."""
    out = _run()
    fast = next(f for f in out["forecasts"] if f["v0_kms"] == 1200.0)
    live = run_tool("cme_arrival", v0_kms=1200.0, launch_time="2024-05-08T23:30Z")
    assert fast["arrival_estimate"] == live["arrival_estimate"]
    assert fast["window"] == live["arrival_window"]


def test_storm_recall_and_tiers(donki):
    out = _run()
    assert out["n_storms"] == 2 and out["n_storms_forecast"] == 1
    gannon = next(s for s in out["storms"] if s["gst_id"].startswith("2024-05-10"))
    assert gannon["observed_class"] == "superstorm" and gannon["max_kp"] == 9.0
    assert gannon["forecast"] and gannon["best_confidence"] == "high"
    assert gannon["matched_cme_id"] == "2024-05-08T22:24:00-CME-001"
    quiet = next(s for s in out["storms"] if s["gst_id"].startswith("2024-05-02"))
    assert not quiet["forecast"] and quiet["observed_class"] == "moderate"
    assert out["storm_recall"] == 0.5
    tiers = {r["confidence"]: r for r in out["confidence_rows"]}
    assert tiers["high"]["precision"] == 1.0 and tiers["high"]["n_storms_best"] == 1
    assert tiers["low"]["precision"] == 0.0 and tiers["moderate"]["precision"] is None


def test_speed_floor_and_cone_are_parameters(donki):
    assert _run(min_speed_kms=1000.0)["n_earth_directed"] == 1
    assert _run(earth_cone_deg=90.0)["n_earth_directed"] == 3


def test_grace_zero_can_lose_the_hit(donki):
    out = _run(grace_hours=0.0)
    fast = next(f for f in out["forecasts"] if f["v0_kms"] == 1200.0)
    live = run_tool("cme_arrival", v0_kms=1200.0, launch_time="2024-05-08T23:30Z")
    inside = live["arrival_window"][0] <= "2024-05-10 16:37" <= live["arrival_window"][1]
    assert (fast["outcome"] == "hit") == inside


def test_bad_window_refuses(donki):
    out = run_tool("hindcast_forecasts", start="2024-05-12", end="2024-05-01", plot=False)
    assert out["status"] == "error" and "after start" in out["error"]
    out = run_tool("hindcast_forecasts", start="2024-05-01", end="2024-05-12",
                   chunk_days=1, plot=False)
    assert out["status"] == "error" and "chunk_days" in out["error"]


def test_chunking_queries_donki_in_pieces(donki):
    _run(chunk_days=5)
    spans = [c for c in donki if c["kind"] == "CMEAnalysis"]
    assert len(spans) == 3 and spans[0]["start_date"] == "2024-05-01"
    assert spans[-1]["end_date"] == "2024-05-12"


def test_plot_and_table_written(donki, tmp_path, monkeypatch):
    monkeypatch.setattr("helio_agent.tools.hindcast.output_path", lambda n: tmp_path / n)
    out = _run(plot=True)
    assert (tmp_path / "hindcast.png").read_bytes().startswith(b"\x89PNG")
    table = (tmp_path / "hindcast.md").read_text()
    assert "# Forecast hindcast" in table and "| high | 1 | 1 | 100% |" in table
    assert "2024-05-10T15:00" in table.replace(" ", "T") or "2024-05-10 15:00" in table
    assert set(out["artifacts"]) == {str(tmp_path / "hindcast.png"), str(tmp_path / "hindcast.md")}
