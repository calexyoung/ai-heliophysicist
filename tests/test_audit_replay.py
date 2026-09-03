"""Audit replay compares exact inputs, results, and artifacts."""

import json
from pathlib import Path

import pytest

from helio_agent import audit, registry


@pytest.fixture
def audit_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "_GIT_SHA", None)
    names = []

    def register(name, func):
        registry.tool(family="measure", name=name)(func)
        names.append(name)
        return name

    yield register
    for name in names:
        registry._REGISTRY.pop(name, None)


def _entries():
    return [json.loads(line) for line in audit.AUDIT_FILE.read_text().splitlines()]


def test_replay_detects_changed_nonartifact_result(audit_registry):
    state = {"value": 1}

    def changing_value():
        value = state["value"]
        state["value"] += 1
        return {"value": value}

    name = audit_registry("_test_changing_value", changing_value)
    first = registry.run_tool(name)
    replayed = registry.replay(first["audit_id"])

    assert replayed["verdict"] == "mismatch"
    assert "result" in replayed["mismatch_dimensions"]


def test_replay_detects_changed_input(audit_registry, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("time,x\n2024-01-01,1\n")

    def read_value(file: str):
        return {"value": Path(file).read_text()}

    name = audit_registry("_test_read_value", read_value)
    first = registry.run_tool(name, file=str(source))
    source.write_text("time,x\n2024-01-01,2\n")
    replayed = registry.replay(first["audit_id"])

    assert replayed["verdict"] == "mismatch"
    assert "inputs" in replayed["mismatch_dimensions"]


def test_replay_detects_changed_artifact(audit_registry, tmp_path):
    target = tmp_path / "result.txt"
    state = {"value": "first"}

    def write_result():
        target.write_text(state["value"])
        state["value"] = "second"
        return {"file": str(target), "artifacts": [str(target)]}

    name = audit_registry("_test_write_result", write_result)
    first = registry.run_tool(name)
    replayed = registry.replay(first["audit_id"])

    assert replayed["verdict"] == "mismatch"
    assert "artifacts" in replayed["mismatch_dimensions"]
    assert str(target) in replayed["artifacts_mismatched"]


def test_replay_detects_new_artifact(audit_registry, tmp_path):
    first_path = tmp_path / "first.txt"
    second_path = tmp_path / "second.txt"
    state = {"replay": False}

    def write_results():
        first_path.write_text("stable")
        artifacts = [str(first_path)]
        if state["replay"]:
            second_path.write_text("new")
            artifacts.append(str(second_path))
        state["replay"] = True
        return {"artifacts": artifacts}

    name = audit_registry("_test_new_artifact", write_results)
    first = registry.run_tool(name)
    replayed = registry.replay(first["audit_id"])

    assert replayed["verdict"] == "mismatch"
    assert "artifacts" in replayed["mismatch_dimensions"]


def test_audit_stores_canonical_result_without_audit_id(audit_registry):
    def stable_value():
        return {"z": 2, "a": {"b": 1}}

    name = audit_registry("_test_stable_value", stable_value)
    result = registry.run_tool(name)
    entry = _entries()[0]

    assert result["audit_id"] == entry["id"]
    assert entry["result"] == {"a": {"b": 1}, "status": "ok", "z": 2}
    assert "audit_id" not in entry["result"]
    assert entry["input_sha256"] == {}


def test_legacy_status_only_entry_is_unverifiable(audit_registry):
    audit.AUDIT_FILE.write_text(json.dumps({
        "id": "legacy",
        "tool": "propagation_delay",
        "args": {"solar_wind_speed_kms": 500.0},
        "status": "ok",
        "artifact_sha256": {},
    }) + "\n")

    replayed = registry.replay("legacy")

    assert replayed["verdict"] == "unverifiable"
    assert "result" in replayed["unverifiable_dimensions"]
