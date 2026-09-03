"""The standing monitor exposes source health and persists state atomically."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from helio_agent import cli, monitor


class ToolFeed:
    def __init__(self):
        self.failures = set()

    def fail(self, tool):
        self.failures.add(tool)

    def __call__(self, tool, **kwargs):
        if tool in self.failures:
            return {"status": "error", "error": f"{tool} unavailable"}
        if tool == "get_noaa_realtime" and kwargs["product"] == "kp":
            return {"status": "ok", "data": {
                "noaa-planetary-k-index.json": {
                    "latest_records": [{"Kp": 3.0}],
                }
            }}
        if tool == "get_noaa_realtime" and kwargs["product"] == "xray":
            return {"status": "ok", "data": {
                "xrays-1-day.json": {
                    "latest_records": [{"energy": "0.1-0.8nm", "flux": 1e-6}],
                }
            }}
        if tool == "search_donki":
            return {"status": "ok", "events": []}
        raise AssertionError(f"unexpected tool call: {tool} {kwargs}")


@pytest.fixture
def monitor_env(tmp_path, monkeypatch):
    feed = ToolFeed()
    monkeypatch.setattr(monitor, "STATE_FILE", tmp_path / "monitor_state.json")
    monkeypatch.setattr(monitor, "run_tool", feed)
    monkeypatch.setattr(
        monitor, "_now",
        lambda: datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc))
    return feed


def test_required_event_failure_marks_cycle_error(monitor_env):
    monitor_env.fail("search_donki")
    out = monitor.cycle()
    assert out["status"] == "error"
    assert any(item["tool"] == "search_donki"
               for item in out["failed_sources"])
    state = json.loads(monitor.STATE_FILE.read_text())
    assert "last_successful_ingestion" not in state
    assert state["last_attempt"].startswith("2026-09-03T12:00:00")


def test_conditions_failure_marks_cycle_degraded(monitor_env):
    monitor_env.fail("get_noaa_realtime")
    out = monitor.cycle()
    assert out["status"] == "degraded"
    assert out["conditions"] == {"kp_latest": None, "xray_flux_wm2": None}
    assert len(out["failed_sources"]) == 2


def test_successful_cycle_is_ok(monitor_env):
    out = monitor.cycle()
    assert out["status"] == "ok"
    assert out["failed_sources"] == []
    state = json.loads(monitor.STATE_FILE.read_text())
    assert state["last_successful_ingestion"].startswith("2026-09-03T12:00:00")


def test_save_state_replaces_temporary_sibling(tmp_path, monkeypatch):
    state_file = tmp_path / "monitor_state.json"
    monkeypatch.setattr(monitor, "STATE_FILE", state_file)
    replaced = []
    real_replace = Path.replace

    def recording_replace(self, target):
        replaced.append((self, Path(target)))
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", recording_replace)
    monitor._save_state({"ledger": []})

    assert replaced == [(state_file.with_suffix(".tmp"), state_file)]
    assert json.loads(state_file.read_text()) == {"ledger": []}
    assert not state_file.with_suffix(".tmp").exists()


@pytest.mark.parametrize("status, expected", [
    ("ok", 0), ("degraded", 0), ("error", 1),
])
def test_monitor_cli_exit_reflects_health(status, expected, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "cycle", lambda: {"status": status})
    monkeypatch.setattr(sys, "argv", ["helio-agent", "monitor"])
    assert cli.main() == expected
    assert json.loads(capsys.readouterr().out)["status"] == status
