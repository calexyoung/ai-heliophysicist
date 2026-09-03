"""Versioned, audit-linked records for reproducing published claims."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from helio_agent import audit
from helio_agent.registry import tool
from helio_agent.workspace import data_path, output_path

SCHEMA_VERSION = 1
CAPABILITIES = {"ready", "method_gap", "blocked"}
VERDICTS = {"match", "mismatch", "refused", "unverified"}
DATA_FIELDS = (
    "dataset", "instrument", "processing_level", "cadence", "revision",
    "time_window",
)


def _present(mapping: dict, key: str) -> bool:
    return key in mapping and mapping[key] is not None and mapping[key] != ""


def _number(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def _same_number(left: Any, right: Any) -> bool:
    return (_number(left) and _number(right)
            and math.isclose(float(left), float(right),
                             rel_tol=1e-12, abs_tol=1e-12))


def _error_sort_key(error: str) -> tuple[int, str]:
    if error.startswith("claims["):
        try:
            return int(error[7:error.index("]")]), error
        except ValueError:
            pass
    return -1, error


def validate_manifest(manifest: dict) -> list[str]:
    """Return every schema/provenance violation in deterministic order."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest: must be an object"]
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: must equal {SCHEMA_VERSION}")

    paper = manifest.get("paper")
    if not isinstance(paper, dict):
        errors.append("paper: must be an object")
    else:
        if not _present(paper, "title"):
            errors.append("paper.title: is required")
        if not any(_present(paper, key) for key in
                   ("doi", "bibcode", "arxiv_id")):
            errors.append("paper: one of doi, bibcode, or arxiv_id is required")

    claims = manifest.get("claims")
    if not isinstance(claims, list):
        errors.append("claims: must be an ordered list")
        return sorted(errors, key=_error_sort_key)

    seen_ids: set[str] = set()
    for index, claim in enumerate(claims):
        base = f"claims[{index}]"
        if not isinstance(claim, dict):
            errors.append(f"{base}: must be an object")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id.strip():
            errors.append(f"{base}.id: is required")
        elif claim_id in seen_ids:
            errors.append(f"{base}.id: duplicate claim id {claim_id!r}")
        else:
            seen_ids.add(claim_id)
        if not _present(claim, "statement"):
            errors.append(f"{base}.statement: is required")
        capability = claim.get("capability")
        if capability not in CAPABILITIES:
            errors.append(
                f"{base}.capability: must be one of {sorted(CAPABILITIES)}")
            continue
        caveats = claim.get("caveats")
        if not isinstance(caveats, list) or not all(
                isinstance(item, str) for item in caveats):
            errors.append(f"{base}.caveats: must be a list of strings")

        if capability != "ready":
            if not _present(claim, "reason"):
                errors.append(f"{base}.reason: is required for {capability}")
            continue

        claimed = claim.get("claimed")
        if not isinstance(claimed, dict):
            errors.append(f"{base}.claimed: must be an object")
        else:
            if not _number(claimed.get("value")):
                errors.append(f"{base}.claimed.value: must be a finite number")
            if not _present(claimed, "units"):
                errors.append(f"{base}.claimed.units: is required")

        data = claim.get("data")
        if not isinstance(data, dict):
            errors.append(f"{base}.data: must be an object")
        else:
            for field in DATA_FIELDS:
                if not _present(data, field):
                    errors.append(f"{base}.data.{field}: is required")

        recipe = claim.get("recipe")
        recipe_audits: set[str] = set()
        if not isinstance(recipe, list) or not recipe:
            errors.append(f"{base}.recipe: must be a non-empty ordered list")
        else:
            for step_index, step in enumerate(recipe):
                step_path = f"{base}.recipe[{step_index}]"
                if not isinstance(step, dict):
                    errors.append(f"{step_path}: must be an object")
                    continue
                for field in ("tool", "args", "audit_id"):
                    if field not in step:
                        errors.append(f"{step_path}.{field}: is required")
                step_id = step.get("audit_id")
                if not isinstance(step_id, str) or not step_id:
                    continue
                recipe_audits.add(step_id)
                entry = audit.find_entry(step_id)
                if entry is None:
                    errors.append(
                        f"{step_path}.audit_id: audit {step_id!r} is missing")
                    continue
                if entry.get("status") != "ok":
                    errors.append(
                        f"{step_path}.audit_id: audit {step_id!r} was not successful")
                if step.get("tool") != entry.get("tool"):
                    errors.append(
                        f"{step_path}.tool: does not agree with audit {step_id!r}")
                if (isinstance(step.get("args"), dict)
                        and audit.canonical_result(step["args"])
                        != audit.canonical_result(entry.get("args", {}))):
                    errors.append(
                        f"{step_path}.args: do not agree with audit {step_id!r}")

        computed = claim.get("computed")
        if not isinstance(computed, dict):
            errors.append(f"{base}.computed: must be an object")
            continue
        if not _number(computed.get("value")):
            errors.append(f"{base}.computed.value: must be a finite number")
        if not _present(computed, "units"):
            errors.append(f"{base}.computed.units: is required")
        if not _number(computed.get("tolerance_percent")):
            errors.append(
                f"{base}.computed.tolerance_percent: must be a finite number")
        verdict = computed.get("verdict")
        if verdict not in VERDICTS:
            errors.append(
                f"{base}.computed.verdict: must be one of {sorted(VERDICTS)}")
        verification_id = computed.get("verification_audit_id")
        if not isinstance(verification_id, str) or not verification_id:
            errors.append(f"{base}.computed.verification_audit_id: is required")
            continue
        verification = audit.find_entry(verification_id)
        if verification is None:
            errors.append(
                f"{base}.computed.verification_audit_id: audit "
                f"{verification_id!r} is missing")
            continue
        if verification.get("status") != "ok":
            errors.append(
                f"{base}.computed.verification_audit_id: audit "
                f"{verification_id!r} was not successful")
        if verification.get("tool") != "verify_claim":
            errors.append(
                f"{base}.computed.verification_audit_id: audit "
                f"{verification_id!r} is not a verify_claim call")
        verification_args = verification.get("args", {})
        comparisons = (
            (f"{base}.claimed.value", claimed.get("value")
             if isinstance(claimed, dict) else None,
             verification_args.get("claimed_value"), True),
            (f"{base}.claimed.units", claimed.get("units")
             if isinstance(claimed, dict) else None,
             verification_args.get("claimed_units"), False),
            (f"{base}.computed.value", computed.get("value"),
             verification_args.get("computed_value"), True),
            (f"{base}.computed.units", computed.get("units"),
             verification_args.get("computed_units"), False),
            (f"{base}.computed.tolerance_percent",
             computed.get("tolerance_percent"),
             verification_args.get("tolerance_percent"), True),
        )
        for path, stored, recorded, numeric in comparisons:
            agrees = (_same_number(stored, recorded) if numeric
                      else stored == recorded)
            if not agrees:
                errors.append(
                    f"{path}: does not agree with audit {verification_id!r}")
        result = verification.get("result")
        if not isinstance(result, dict):
            errors.append(
                f"{base}.computed.verification_audit_id: audit "
                f"{verification_id!r} has no full result")
        else:
            if verdict in VERDICTS and result.get("verdict") != verdict:
                errors.append(
                    f"{base}.computed.verdict: does not agree with audit "
                    f"{verification_id!r}")
            source_id = result.get("computed_audit_id")
            if source_id not in recipe_audits:
                errors.append(
                    f"{base}.computed.verification_audit_id: source audit "
                    f"{source_id!r} is not present in the recipe")

    return sorted(errors, key=_error_sort_key)


def _read_manifest(file: str) -> dict:
    try:
        value = json.loads(Path(file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read reproduction manifest {file!r}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("reproduction manifest root must be an object")
    return value


@tool(family="report")
def create_reproduction_manifest(
        paper: dict, claims: list[dict],
        out_name: str = "reproduction.json") -> dict:
    """Create a deterministic, versioned manifest for reproduced paper claims.

    Ready claims must include complete data identity, an ordered audited tool
    recipe, and an audit-backed verify_claim result. Method gaps and blocked
    claims remain visible with an explicit reason instead of being omitted.
    """
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "paper": paper,
        "claims": claims,
    }
    errors = validate_manifest(manifest)
    if errors:
        return {"status": "error", "valid": False, "errors": errors,
                "error": "refusing: reproduction manifest is invalid"}
    path = data_path(out_name)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return {"valid": True, "errors": [], "file": str(path),
            "n_claims": len(claims), "artifacts": [str(path)]}


@tool(family="measure")
def validate_reproduction_manifest(file: str) -> dict:
    """Validate a reproduction manifest and all of its audit references."""
    manifest = _read_manifest(file)
    errors = validate_manifest(manifest)
    return {"valid": not errors, "errors": errors,
            "schema_version": manifest.get("schema_version"),
            "n_claims": len(manifest.get("claims", []))
            if isinstance(manifest.get("claims"), list) else 0}


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render(manifest: dict) -> str:
    paper = manifest["paper"]
    lines = [f"# Reproduction: {paper['title']}", ""]
    identifiers = [f"{key}: {paper[key]}" for key in
                   ("doi", "bibcode", "arxiv_id") if paper.get(key)]
    lines.extend(["**Paper:** " + "; ".join(identifiers), "",
                  "| Claim | Capability | Verdict |",
                  "|---|---|---|"])
    for claim in manifest["claims"]:
        verdict = claim.get("computed", {}).get("verdict", "unverified")
        lines.append(
            f"| {_cell(claim['id'])} | {_cell(claim['capability'])} | "
            f"{_cell(verdict)} |")
    lines.append("")
    for claim in manifest["claims"]:
        lines.extend([f"## Claim {_cell(claim['id'])}", "",
                      claim["statement"], "",
                      f"- Capability: `{claim['capability']}`"])
        if claim["capability"] == "ready":
            claimed, computed, data = (
                claim["claimed"], claim["computed"], claim["data"])
            lines.extend([
                f"- Claimed: `{claimed['value']} {claimed['units']}`",
                f"- Computed: `{computed['value']} {computed['units']}`",
                f"- Verdict: `{computed['verdict']}` at "
                f"`{computed['tolerance_percent']}%` tolerance",
                f"- Verification audit: "
                f"`{computed['verification_audit_id']}`", "",
                "### Data identity", "",
            ])
            for field in DATA_FIELDS:
                lines.append(f"- {field.replace('_', ' ').title()}: "
                             f"`{_cell(data[field])}`")
            lines.extend(["", "### Ordered recipe", ""])
            for index, step in enumerate(claim["recipe"], 1):
                args = json.dumps(step["args"], sort_keys=True,
                                  separators=(",", ":"))
                lines.append(
                    f"{index}. `{step['tool']}` with `{args}` "
                    f"(audit `{step['audit_id']}`)")
        else:
            lines.append(f"- Reason: {_cell(claim['reason'])}")
        lines.extend(["", "### Caveats", ""])
        caveats = claim.get("caveats", [])
        lines.extend([f"- {item}" for item in caveats]
                     or ["- None recorded."])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@tool(family="report")
def render_reproduction_report(
        file: str, out_name: str = "reproduction.md") -> dict:
    """Render a validated reproduction manifest as deterministic Markdown."""
    manifest = _read_manifest(file)
    errors = validate_manifest(manifest)
    if errors:
        return {"status": "error", "valid": False, "errors": errors,
                "error": "refusing: reproduction manifest is invalid"}
    path = output_path(out_name)
    path.write_text(_render(manifest))
    return {"valid": True, "errors": [], "file": str(path),
            "artifacts": [str(path)]}
