"""Paper reproduction manifests preserve methods, data identity, and audits."""

import copy
import json
from pathlib import Path

import pytest

from helio_agent import audit, reproduction, workspace
from helio_agent.registry import run_tool


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(audit, "_GIT_SHA", None)
    data = tmp_path / "data"
    output = tmp_path / "output"
    monkeypatch.setattr(
        reproduction, "data_path",
        lambda name: workspace._workspace_path(data, name))
    monkeypatch.setattr(
        reproduction, "output_path",
        lambda name: workspace._workspace_path(output, name))


@pytest.fixture
def valid_claim():
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500.0)
    value = measured["delay_minutes"]
    verified = run_tool(
        "verify_claim", claimed_value=value, computed_value=value,
        claimed_units="minutes", computed_units="minutes",
        tolerance_percent=1.0, claim_description="L1 propagation delay",
        computed_audit_id=measured["audit_id"])
    return {
        "id": "c1",
        "statement": "The L1 propagation delay is reproduced.",
        "capability": "ready",
        "claimed": {"value": value, "units": "minutes"},
        "data": {
            "dataset": "constant-speed example",
            "instrument": "none",
            "processing_level": "derived",
            "cadence": "not applicable",
            "revision": "1",
            "time_window": "instantaneous",
        },
        "recipe": [{
            "tool": "propagation_delay",
            "args": {"solar_wind_speed_kms": 500.0},
            "audit_id": measured["audit_id"],
        }],
        "computed": {
            "value": value,
            "units": "minutes",
            "tolerance_percent": 1.0,
            "verdict": "match",
            "verification_audit_id": verified["audit_id"],
        },
        "caveats": ["Illustrative deterministic input."],
    }


@pytest.fixture
def valid_manifest(valid_claim):
    return {
        "schema_version": 1,
        "paper": {"title": "Example", "doi": "10.1/example"},
        "claims": [copy.deepcopy(valid_claim)],
    }


def _write(tmp_path, name, manifest):
    path = tmp_path / name
    path.write_text(json.dumps(manifest))
    return path


def test_create_validate_and_render_manifest(valid_claim):
    made = run_tool(
        "create_reproduction_manifest",
        paper={"title": "Example", "doi": "10.1/example"},
        claims=[valid_claim], out_name="papers/example.json")
    assert made["status"] == "ok"
    assert Path(made["file"]).is_file()

    checked = run_tool("validate_reproduction_manifest", file=made["file"])
    assert checked["valid"] is True
    assert checked["errors"] == []

    rendered = run_tool(
        "render_reproduction_report", file=made["file"],
        out_name="papers/example.md")
    text = Path(rendered["file"]).read_text()
    assert "# Reproduction: Example" in text
    assert "Claim c1" in text and "match" in text
    assert valid_claim["recipe"][0]["audit_id"] in text


def test_validation_reports_all_manifest_errors(tmp_path):
    bad = {"schema_version": 1, "paper": {}, "claims": [
        {"id": "same", "capability": "unknown"},
        {"id": "same", "capability": "ready", "recipe": []},
    ]}
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, "bad.json", bad)))
    assert out["valid"] is False
    assert len(out["errors"]) >= 3
    assert out["errors"] == sorted(out["errors"], key=lambda e: (
        int(e.split("claims[")[1].split("]")[0]) if "claims[" in e else -1,
        e,
    ))


def test_validation_refuses_fake_recipe_audit(tmp_path, valid_manifest):
    valid_manifest["claims"][0]["recipe"][0]["audit_id"] = "missing"
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, "fake.json", valid_manifest)))
    assert out["valid"] is False
    assert any("missing" in error for error in out["errors"])


def test_validation_refuses_failed_recipe_audit(tmp_path, valid_manifest):
    failed = run_tool("propagation_delay", solar_wind_speed_kms=-1.0)
    step = valid_manifest["claims"][0]["recipe"][0]
    step.update(tool="propagation_delay", audit_id=failed["audit_id"])
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, "failed.json", valid_manifest)))
    assert any("was not successful" in error for error in out["errors"])


@pytest.mark.parametrize("capability", ["method_gap", "blocked"])
def test_non_ready_claims_can_explicitly_omit_computed_results(
        tmp_path, capability):
    manifest = {
        "schema_version": 1,
        "paper": {"title": "Example", "arxiv_id": "2601.00001"},
        "claims": [{
            "id": "c1", "statement": "Not currently reproducible",
            "capability": capability, "reason": "Required method unavailable",
            "caveats": [],
        }],
    }
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, f"{capability}.json", manifest)))
    assert out["valid"] is True


def test_duplicate_ids_and_invalid_verdict_are_reported(tmp_path, valid_manifest):
    valid_manifest["claims"].append(copy.deepcopy(valid_manifest["claims"][0]))
    valid_manifest["claims"][0]["computed"]["verdict"] = "maybe"
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, "duplicate.json", valid_manifest)))
    assert any("verdict" in error for error in out["errors"])
    assert any("duplicate" in error for error in out["errors"])


def test_verification_audit_must_agree_with_stored_verdict(
        tmp_path, valid_manifest):
    valid_manifest["claims"][0]["computed"]["verdict"] = "mismatch"
    out = run_tool(
        "validate_reproduction_manifest",
        file=str(_write(tmp_path, "disagree.json", valid_manifest)))
    assert any("does not agree" in error for error in out["errors"])


def test_json_and_markdown_rendering_are_deterministic(valid_claim):
    made = run_tool(
        "create_reproduction_manifest",
        paper={"title": "Example", "bibcode": "2026Example"},
        claims=[valid_claim], out_name="one.json")
    first_json = Path(made["file"]).read_bytes()
    made_again = run_tool(
        "create_reproduction_manifest",
        paper={"bibcode": "2026Example", "title": "Example"},
        claims=[valid_claim], out_name="two.json")
    assert first_json == Path(made_again["file"]).read_bytes()

    first = run_tool(
        "render_reproduction_report", file=made["file"], out_name="one.md")
    second = run_tool(
        "render_reproduction_report", file=made["file"], out_name="two.md")
    assert Path(first["file"]).read_bytes() == Path(second["file"]).read_bytes()


@pytest.mark.parametrize("out_name", ["../escape.json", "/tmp/escape.json"])
def test_create_rejects_uncontained_output_names(valid_claim, out_name):
    out = run_tool(
        "create_reproduction_manifest",
        paper={"title": "Example", "doi": "10.1/example"},
        claims=[valid_claim], out_name=out_name)
    assert out["status"] == "error"
    assert "relative" in out["error"] or "outside workspace" in out["error"]
