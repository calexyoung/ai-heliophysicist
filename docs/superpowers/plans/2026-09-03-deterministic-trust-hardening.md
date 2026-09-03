# Deterministic Trust Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce replay accuracy, provenance, workspace isolation, monitor health, replay-safe POST requests, and structured paper-reproduction records.

**Architecture:** Strengthen the existing registry/audit/cache boundaries instead of adding a parallel runtime. A new focused `reproduction.py` module owns versioned paper manifests, while current tools continue to use plain dictionaries and the six existing families.

**Tech Stack:** Python 3.11+, pytest, requests, pathlib, JSON/JSONL, existing `@tool` registry.

**Spec:** `docs/superpowers/specs/2026-09-03-deterministic-trust-hardening-design.md`

## Global Constraints

- Do not change scientific algorithms, thresholds, or published validation tolerances.
- Preserve all existing audit fields and read historical JSONL entries without migration.
- Never store API keys, authorization headers, or request bodies in cache metadata.
- Generated paths must remain inside the active data or output workspace after symlink resolution.
- Invalid provenance must return an explicit refusal rather than a scientific verdict.
- Use one failing-test, minimal-implementation, passing-test cycle for each behavior group.

---

### Task 1: Contained Workspace Paths

**Files:**
- Modify: `helio_agent/workspace.py:67-80`
- Create: `tests/test_workspace_paths.py`

**Interfaces:**
- Produces: `_workspace_path(base: Path, name: str) -> Path`
- Preserves: `output_path(name: str) -> Path`, `data_path(name: str) -> Path`

- [ ] **Step 1: Write failing containment tests**

```python
from pathlib import Path

import pytest

from helio_agent import workspace


@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    data = tmp_path / "workspace" / "data"
    output = tmp_path / "workspace" / "outputs"
    monkeypatch.setattr(workspace, "DATA_DIR", data)
    monkeypatch.setattr(workspace, "OUTPUT_DIR", output)
    return data, output


def test_nested_output_stays_inside_workspace(isolated_workspace):
    _, output = isolated_workspace
    got = workspace.output_path("figures/result.png")
    assert got == output / "figures" / "result.png"
    assert got.parent.is_dir()


@pytest.mark.parametrize("name", ["../escape.txt", "../../.env", "/tmp/escape.txt"])
def test_output_path_rejects_escape(isolated_workspace, name):
    with pytest.raises(ValueError, match="outside workspace|relative"):
        workspace.output_path(name)


def test_data_path_rejects_symlink_escape(isolated_workspace, tmp_path):
    data, _ = isolated_workspace
    data.mkdir(parents=True)
    (data / "link").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="outside workspace"):
        workspace.data_path("link/escape.txt")
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_workspace_paths.py -q`

Expected: traversal and symlink tests fail because current helpers return unchecked paths; the nested-parent assertion also fails.

- [ ] **Step 3: Implement the contained resolver**

Implement `_workspace_path` with `Path(name).is_absolute()`, `Path.resolve(strict=False)`, and `candidate.is_relative_to(base.resolve())`. Create the validated candidate's parent directory and have both public helpers delegate to it.

- [ ] **Step 4: Run the focused tests and full offline suite**

Run: `uv run pytest tests/test_workspace_paths.py -q`

Expected: all tests pass.

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add helio_agent/workspace.py tests/test_workspace_paths.py
git commit -m "fix: contain generated workspace paths"
```

### Task 2: Exact Audit Records and Replay Verdicts

**Files:**
- Modify: `helio_agent/audit.py:19-90`
- Modify: `helio_agent/registry.py:86-156`
- Create: `tests/test_audit_replay.py`

**Interfaces:**
- Produces: `audit.canonical_result(result: object) -> object`
- Produces: `audit.hash_input_files(args: object) -> dict[str, str]`
- Extends: `audit.record(..., result: Any = None, input_sha256: dict[str, str] | None = None)`
- Preserves: `registry.replay(entry_id: str, readonly_cache: bool = True) -> dict`

- [ ] **Step 1: Write failing replay tests**

Create real temporary audit logs and temporary input/output files. Register uniquely named test tools in the in-process registry and remove them in fixture teardown.

```python
def test_replay_detects_changed_nonartifact_result(audit_registry):
    state = {"value": 1}

    @registry.tool(family="measure", name="_test_changing_value")
    def changing_value():
        value = state["value"]
        state["value"] += 1
        return {"value": value}

    first = registry.run_tool("_test_changing_value")
    replayed = registry.replay(first["audit_id"])
    assert replayed["verdict"] == "mismatch"
    assert "result" in replayed["mismatch_dimensions"]


def test_replay_refuses_changed_input(audit_registry, tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("time,x\n2024-01-01,1\n")

    @registry.tool(family="measure", name="_test_read_value")
    def read_value(file: str):
        return {"value": Path(file).read_text()}

    first = registry.run_tool("_test_read_value", file=str(source))
    source.write_text("time,x\n2024-01-01,2\n")
    replayed = registry.replay(first["audit_id"])
    assert replayed["verdict"] == "mismatch"
    assert "inputs" in replayed["mismatch_dimensions"]


def test_legacy_status_only_entry_is_unverifiable(audit_registry):
    audit.AUDIT_FILE.write_text(json.dumps({
        "id": "legacy", "tool": "plasma_parameters", "args": {
            "density_cm3": 5.0, "b_nT": 5.0
        }, "status": "ok", "artifact_sha256": {}
    }) + "\n")
    replayed = registry.replay("legacy")
    assert replayed["verdict"] == "unverifiable"
```

Also cover output artifact changes, missing/new artifact sets, canonical dictionary ordering, and exclusion of `audit_id` from stored results.

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_audit_replay.py -q`

Expected: failures show status-only replay reporting `match` and missing new audit fields.

- [ ] **Step 3: Store canonical results and input hashes**

Capture input hashes before invoking a tool. Store a canonical result without `audit_id` on success and a canonical error result on failure. Do not change the concise `result_summary` field.

- [ ] **Step 4: Implement dimension-based replay**

Compute `mismatch_dimensions` and `unverifiable_dimensions`. Require equality of original/replay status, canonical result, pre-run inputs, artifact path sets, and artifact hashes whenever those dimensions exist. Return `match`, `mismatch`, or `unverifiable`; include the existing response keys for compatibility.

- [ ] **Step 5: Run focused and full tests**

Run: `uv run pytest tests/test_audit_replay.py -q`

Expected: all tests pass.

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add helio_agent/audit.py helio_agent/registry.py tests/test_audit_replay.py
git commit -m "fix: make audit replay compare exact results"
```

### Task 3: Verifiable Claim Provenance

**Files:**
- Modify: `helio_agent/tools/verify.py:34-78`
- Modify: `validation/run_validation.py:360-380`
- Create: `tests/test_verify_claim_provenance.py`

**Interfaces:**
- Consumes: `audit.find_entry(entry_id: str) -> dict | None`
- Produces: `verify_claim(..., computed_audit_id: str) -> dict` with existing success fields and explicit refusal errors.

- [ ] **Step 1: Write failing provenance tests**

```python
def test_verify_claim_refuses_unknown_audit_id(isolated_audit):
    out = run_tool("verify_claim", claimed_value=1, computed_value=1,
                   claimed_units="nT", computed_units="nT",
                   computed_audit_id="missing")
    assert out["status"] == "error"
    assert out["verdict"] == "refused"


def test_verify_claim_refuses_value_not_in_recorded_result(isolated_audit):
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500)
    out = run_tool("verify_claim", claimed_value=99, computed_value=99,
                   claimed_units="h", computed_units="h",
                   computed_audit_id=measured["audit_id"])
    assert out["verdict"] == "refused"


def test_verify_claim_accepts_value_in_successful_audit(isolated_audit):
    measured = run_tool("propagation_delay", solar_wind_speed_kms=500)
    value = measured["delay_minutes"]
    out = run_tool("verify_claim", claimed_value=value, computed_value=value,
                   claimed_units="minutes", computed_units="minutes",
                   computed_audit_id=measured["audit_id"])
    assert out["status"] == "ok"
    assert out["verdict"] == "match"
```

Add `minutes`/`min` normalization needed by the real tool example, plus cases for failed and legacy entries.

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_verify_claim_provenance.py -q`

Expected: fake and unrelated audit identifiers are incorrectly accepted.

- [ ] **Step 3: Implement numeric-leaf provenance validation**

Resolve the audit entry, require `status == "ok"`, require a full recorded result, recursively collect finite numeric leaves while excluding booleans, and require one to equal `computed_value` within floating-point tolerance. Refuse before calculating the claim difference when provenance is invalid.

- [ ] **Step 4: Replace fake validation IDs with a real measured call**

In `case_verify_claim`, call `propagation_delay`, use its returned `delay_minutes` and audit ID for the positive comparison, and retain explicit unit-mismatch/no-audit/mismatch branches with real audit provenance.

- [ ] **Step 5: Run focused, offline, and validation-case tests**

Run: `uv run pytest tests/test_verify_claim_provenance.py -q`

Run: `uv run pytest -q`

Run: `uv run python validation/run_validation.py verify`

Expected: every command passes.

- [ ] **Step 6: Commit**

```bash
git add helio_agent/tools/verify.py validation/run_validation.py tests/test_verify_claim_provenance.py
git commit -m "fix: require real provenance for claim verification"
```

### Task 4: Replay-Safe POST Requests

**Files:**
- Modify: `helio_agent/http.py:78-144`
- Modify: `helio_agent/tools/literature.py:53-64`
- Modify: `helio_agent/tools/export.py:183-214`
- Modify: `tests/test_http_cache.py`

**Interfaces:**
- Produces: `cached_request(method: str, url: str, *, params: dict | None = None, json_body: object | None = None, headers: dict | None = None, timeout: int = 90, allow_error: bool = False, ttl_seconds: float | None = None) -> CachedResponse`
- Extends: `cache_key(url, params=None, method="GET", json_body=None) -> str`
- Preserves: `cached_get(...) -> CachedResponse`

- [ ] **Step 1: Add failing POST cache tests**

```python
def test_post_body_changes_cache_key():
    a = hhttp.cache_key("https://x.test", method="POST", json_body={"ids": ["a"]})
    b = hhttp.cache_key("https://x.test", method="POST", json_body={"ids": ["b"]})
    assert a != b


def test_post_roundtrip_uses_cache(monkeypatch):
    calls = {"n": 0}

    class FakeResponse:
        status_code = 200
        content = b'{"export": "@article{x}"}'
        url = "https://x.test/export"

        def raise_for_status(self):
            return None

    def request(method, url, **kwargs):
        calls["n"] += 1
        return FakeResponse()

    monkeypatch.setattr(hhttp.requests, "request", request)
    first = hhttp.cached_request("POST", "https://x.test/export",
                                 json_body={"ids": ["a"]},
                                 headers={"Authorization": "Bearer SECRET"})
    second = hhttp.cached_request("POST", "https://x.test/export",
                                  json_body={"ids": ["a"]},
                                  headers={"Authorization": "Bearer SECRET"})
    assert calls["n"] == 1
    assert not first.from_cache and second.from_cache
    assert "SECRET" not in next(hhttp.CACHE_DIR.rglob("*.json")).read_text()


def test_readonly_post_miss_never_calls_network(monkeypatch):
    monkeypatch.setenv("HELIO_CACHE_MODE", "readonly")
    monkeypatch.setattr(hhttp.requests, "request",
                        lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(hhttp.CacheMiss):
        hhttp.cached_request("POST", "https://x.test/export", json_body={"x": 1})
```

- [ ] **Step 2: Run the cache tests and verify RED**

Run: `uv run pytest tests/test_http_cache.py -q`

Expected: `cached_request` and body-aware cache identity do not exist.

- [ ] **Step 3: Implement method-aware caching**

Use `requests.request` for misses. Hash a canonical JSON encoding of `json_body` into the key without storing the body. Preserve old GET cache keys when `json_body is None` so existing cache entries remain usable.

- [ ] **Step 4: Migrate the two POST callers**

Replace direct `requests.post` calls in `get_bibtex` and Unmarkdown `export_html` with `cached_request("POST", ...)`. Remove their local `requests` imports. Both calls must honor readonly replay.

- [ ] **Step 5: Run focused and full tests**

Run: `uv run pytest tests/test_http_cache.py -q`

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add helio_agent/http.py helio_agent/tools/literature.py helio_agent/tools/export.py tests/test_http_cache.py
git commit -m "feat: cache replayable POST requests"
```

### Task 5: Explicit Monitor Health

**Files:**
- Modify: `helio_agent/monitor.py:33-160`
- Modify: `helio_agent/cli.py:48-52`
- Create: `tests/test_monitor_health.py`

**Interfaces:**
- Produces: `_save_state(state: dict) -> None` using atomic replacement.
- Extends: `cycle(...) -> dict` with `status` and `failed_sources`.
- CLI: exit 1 for monitor `status == "error"`; exit 0 for `ok` and `degraded`.

- [ ] **Step 1: Write failing monitor health tests**

Use a deterministic fake `run_tool` keyed by requested tool name and a temporary `STATE_FILE`.

```python
def test_required_event_failure_marks_cycle_error(monitor_env):
    monitor_env.fail("search_donki", "DONKI unavailable")
    out = monitor.cycle()
    assert out["status"] == "error"
    assert any(x["tool"] == "search_donki" for x in out["failed_sources"])


def test_conditions_failure_marks_cycle_degraded(monitor_env):
    monitor_env.fail("get_noaa_realtime", "NOAA unavailable")
    out = monitor.cycle()
    assert out["status"] == "degraded"
    assert out["conditions"] == {"kp_latest": None, "xray_flux_wm2": None}


def test_successful_cycle_is_ok(monitor_env):
    out = monitor.cycle()
    assert out["status"] == "ok"
    assert out["failed_sources"] == []
```

Add an atomic-write test that patches `Path.replace` to observe a temporary sibling, and a CLI test that patches `monitor.cycle` to return each status and checks `main()` exit codes.

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_monitor_health.py -q`

Expected: responses lack status/failure details and CLI returns zero on required-source failure.

- [ ] **Step 3: Implement source classification and atomic state writes**

Record each failed call once. Treat both `search_donki` ingestion calls as required; condition feeds are optional. Store `last_attempt` every run and update `last_successful_ingestion` only when required calls succeed. Write JSON to `STATE_FILE.with_suffix(".tmp")` and replace `STATE_FILE` atomically.

- [ ] **Step 4: Implement CLI exit behavior**

Print the cycle result once and return 1 only for `status == "error"`.

- [ ] **Step 5: Run focused and full tests**

Run: `uv run pytest tests/test_monitor_health.py -q`

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add helio_agent/monitor.py helio_agent/cli.py tests/test_monitor_health.py
git commit -m "fix: surface monitor source failures"
```

### Task 6: Structured Paper-Reproduction Manifests

**Files:**
- Create: `helio_agent/reproduction.py`
- Create: `tests/test_reproduction_manifest.py`
- Modify: `helio_agent/tools/__init__.py`
- Modify: `tests/tool_schemas.lock.json`

**Interfaces:**
- Produces: `validate_manifest(manifest: dict) -> list[str]`
- Produces registered tools:
  - `create_reproduction_manifest(paper: dict, claims: list[dict], out_name: str = "reproduction.json") -> dict`
  - `validate_reproduction_manifest(file: str) -> dict`
  - `render_reproduction_report(file: str, out_name: str = "reproduction.md") -> dict`

- [ ] **Step 1: Write failing schema and audit-reference tests**

Create `tmp_workspace` by monkeypatching `reproduction.data_path` and
`reproduction.output_path` to return descendants of `tmp_path`. Create
`valid_claim` and `valid_manifest` fixtures as literal dictionaries with one
`ready` claim; obtain their recipe and verification audit IDs from real
temporary audited tools rather than inventing identifiers.

```python
def test_create_validate_and_render_manifest(tmp_workspace, valid_claim):
    made = run_tool("create_reproduction_manifest",
                    paper={"title": "Example", "doi": "10.1/example"},
                    claims=[valid_claim], out_name="papers/example.json")
    assert made["status"] == "ok"
    checked = run_tool("validate_reproduction_manifest", file=made["file"])
    assert checked["valid"] is True
    rendered = run_tool("render_reproduction_report", file=made["file"],
                        out_name="papers/example.md")
    text = Path(rendered["file"]).read_text()
    assert "# Reproduction: Example" in text
    assert "Claim c1" in text and "match" in text


def test_validation_reports_all_manifest_errors(tmp_workspace):
    bad = {"schema_version": 1, "paper": {}, "claims": [
        {"id": "same", "capability": "unknown"},
        {"id": "same", "capability": "ready", "recipe": []},
    ]}
    path = tmp_workspace / "bad.json"
    path.write_text(json.dumps(bad))
    out = run_tool("validate_reproduction_manifest", file=str(path))
    assert out["valid"] is False
    assert len(out["errors"]) >= 3


def test_validation_refuses_fake_recipe_audit(tmp_workspace, valid_manifest):
    valid_manifest["claims"][0]["recipe"][0]["audit_id"] = "missing"
    path = tmp_workspace / "fake.json"
    path.write_text(json.dumps(valid_manifest))
    out = run_tool("validate_reproduction_manifest", file=str(path))
    assert out["valid"] is False
    assert any("missing" in e for e in out["errors"])
```

Also cover `method_gap` and `blocked` claims without computed results, duplicate claim IDs, invalid verdicts, unsuccessful audit entries, verification-audit disagreement, deterministic formatting, and contained output names.

- [ ] **Step 2: Run the tests and verify RED**

Run: `uv run pytest tests/test_reproduction_manifest.py -q`

Expected: the module and tools do not exist.

- [ ] **Step 3: Implement pure validation helpers**

Use schema version `1`; accepted capability states are `ready`, `method_gap`, and `blocked`; accepted verdicts are `match`, `mismatch`, `refused`, and `unverified`. Accumulate path-addressed errors in stable claim order. Require complete data/method/provenance fields only for `ready` claims.

- [ ] **Step 4: Implement and register create/validate/render tools**

Write JSON with `sort_keys=True`, `indent=2`, and a trailing newline. Render Markdown with paper identity, a claim summary table, per-claim provenance/recipe, and caveats. All outputs use `data_path` or `output_path` and return artifacts.

- [ ] **Step 5: Update the schema lock and generated tool docs**

Run: `uv run python tests/test_schema_lock.py --update`

Run: `uv run python scripts/gen_docs.py`

- [ ] **Step 6: Run focused and full tests**

Run: `uv run pytest tests/test_reproduction_manifest.py -q`

Run: `uv run pytest -q`

Expected: all tests pass and generated documentation is current.

- [ ] **Step 7: Commit**

```bash
git add helio_agent/reproduction.py helio_agent/tools/__init__.py tests/test_reproduction_manifest.py tests/tool_schemas.lock.json docs/TOOLS.md
git commit -m "feat: add paper reproduction manifests"
```

### Task 7: Accurate Documentation and Final Validation

**Files:**
- Modify: `README.md:13-16`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/MODULES.md`
- Modify: `docs/USAGE.md`
- Modify: `skills/methods/paper_reproduction.md`
- Modify: `scripts/gen_docs.py:24-31`
- Modify: `docs/TOOLS.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Documents the new audit fields, three replay verdicts, monitor health states, cached POST behavior, contained paths, and reproduction-manifest workflow.

- [ ] **Step 1: Add a failing behavioral validation-coverage test**

Extend `tests/test_docs_current.py` to derive tools directly referenced by literal `run_tool` calls in `validation/run_validation.py`. Require README wording to report the direct count and distinguish supporting tools rather than claiming every registered tool has a published anchor.

- [ ] **Step 2: Run the documentation test and verify RED**

Run: `uv run pytest tests/test_docs_current.py -q`

Expected: README still makes the broader unsupported claim.

- [ ] **Step 3: Update authored and generated documentation**

Describe direct versus indirect validation honestly. Add paste-ready CLI examples for creating, validating, and rendering a reproduction manifest. Update module and architecture diagrams/text without claiming automated PDF interpretation. Regenerate `docs/TOOLS.md`.

- [ ] **Step 4: Run all offline verification**

Run: `uv run pytest -q`

Expected: all tests pass with no failures.

Run: `uv run python scripts/gen_docs.py --check`

Expected: `reference docs current`.

Run: `git diff --check`

Expected: no output and exit 0.

- [ ] **Step 5: Run the complete live scientific validation**

Run: `uv run python -u validation/run_validation.py`

Expected: every published-result check passes. Capture and report the exact passed/total count; do not infer success from partial output.

- [ ] **Step 6: Inspect repository state and generated artifacts**

Run: `git status --short`

Expected: only intended source/test/doc changes plus the pre-existing untracked `graphify-out/` directory.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/ARCHITECTURE.md docs/MODULES.md docs/USAGE.md skills/methods/paper_reproduction.md scripts/gen_docs.py docs/TOOLS.md CHANGELOG.md tests/test_docs_current.py
git commit -m "docs: define hardened deterministic guarantees"
```

### Task 8: Completion Review

**Files:**
- Review only: all commits and changed files from Tasks 1-7.

**Interfaces:**
- Consumes all previous task outputs; produces no code unless verification finds a regression.

- [ ] **Step 1: Review the complete diff against the design**

Run: `git diff 618b97c^..HEAD --stat`

Run: `git diff 618b97c^..HEAD -- helio_agent tests validation scripts README.md docs skills CHANGELOG.md`

Check each design requirement against a concrete implementation and test.

- [ ] **Step 2: Re-run the final offline suite from a clean process**

Run: `uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 3: Report verification evidence and remaining limitations**

Report exact test counts, live-validation counts, commit IDs, changed files, and any upstream warnings. Explicitly retain the limitation that arbitrary PDF interpretation and claim extraction require agent/scientist review.
