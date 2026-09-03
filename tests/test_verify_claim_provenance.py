"""Claim verification requires a real audit record for the computed value."""

import json

import pytest

from helio_agent import audit
from helio_agent.registry import run_tool


@pytest.fixture(autouse=True)
def isolated_audit(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "_GIT_SHA", None)


def _verify(value, audit_id, *, claimed=None, claimed_units="min",
            computed_units="minutes"):
    return run_tool("verify_claim", claimed_value=value if claimed is None else claimed,
                    computed_value=value, claimed_units=claimed_units,
                    computed_units=computed_units,
                    computed_audit_id=audit_id)


def test_verify_claim_refuses_unknown_audit_id():
    out = _verify(1.0, "missing")
    assert out["status"] == "error"
    assert out["verdict"] == "refused"
    assert "missing" in out["error"]


def test_verify_claim_refuses_value_not_in_recorded_result():
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500.0)
    out = _verify(99.0, measured["audit_id"])
    assert out["status"] == "error"
    assert out["verdict"] == "refused"
    assert "recorded result" in out["error"]


def test_verify_claim_accepts_value_in_successful_audit():
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500.0)
    value = measured["delay_minutes"]
    out = _verify(value, measured["audit_id"])
    assert out["status"] == "ok"
    assert out["verdict"] == "match"
    assert out["computed_audit_id"] == measured["audit_id"]


def test_verify_claim_refuses_failed_audit():
    measured = run_tool("propagation_delay", solar_wind_speed_kms=-1.0)
    out = _verify(1.0, measured["audit_id"])
    assert out["status"] == "error"
    assert out["verdict"] == "refused"
    assert "not successful" in out["error"]


def test_verify_claim_refuses_legacy_audit_without_full_result():
    audit.AUDIT_FILE.write_text(json.dumps({
        "id": "legacy", "tool": "propagation_delay", "status": "ok",
        "args": {"solar_wind_speed_kms": 500.0},
    }) + "\n")
    out = _verify(50.0, "legacy")
    assert out["status"] == "error"
    assert out["verdict"] == "refused"
    assert "full result" in out["error"]


def test_verify_claim_rejects_boolean_as_numeric_provenance(monkeypatch):
    audit.AUDIT_FILE.write_text(json.dumps({
        "id": "boolean", "tool": "example", "status": "ok",
        "args": {}, "result": {"flag": True, "status": "ok"},
    }) + "\n")
    out = _verify(1.0, "boolean")
    assert out["verdict"] == "refused"
