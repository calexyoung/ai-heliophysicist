"""Tool registry.

Tools are plain Python functions registered with the @tool decorator. Each
declares a family (mirroring the six families of the AI Astrophysicist
pattern) and gets automatic audit logging when invoked through run_tool().

Families:
    discover   - find datasets, spacecraft, events, imagery in the archives
    retrieve   - fetch actual data to local disk
    reduce     - turn raw products into clean analysis-ready series/maps
    measure    - fit, correlate, and quantify (the science numbers)
    literature - ADS / arXiv
    report     - plots, tables, PDF reports
"""

from __future__ import annotations

import inspect
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from helio_agent import audit

FAMILIES = ("discover", "retrieve", "reduce", "measure", "literature", "report")

_REGISTRY: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    family: str
    func: Callable
    doc: str = ""
    params: dict[str, str] = field(default_factory=dict)
    scope: str = "core"   # "core" or "user:<name>" for users/<name>/tools/

    def signature(self) -> str:
        return f"{self.name}{inspect.signature(self.func)}"


_CURRENT_SCOPE = "core"


def tool(family: str, name: str | None = None):
    """Register a function as an agent tool."""
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; must be one of {FAMILIES}")

    def deco(func: Callable) -> Callable:
        tname = name or func.__name__
        sig = inspect.signature(func)
        params = {p: str(v.annotation) for p, v in sig.parameters.items()}
        if tname in _REGISTRY and _REGISTRY[tname].scope != _CURRENT_SCOPE:
            raise ValueError(
                f"user tool {tname!r} would shadow a {_REGISTRY[tname].scope} "
                "tool; user tools must use new names")
        _REGISTRY[tname] = Tool(
            name=tname, family=family, func=func,
            doc=inspect.getdoc(func) or "", params=params,
            scope=_CURRENT_SCOPE,
        )
        return func

    return deco


def get_tool(name: str) -> Tool:
    _load_all()
    if name not in _REGISTRY:
        raise KeyError(f"no tool named {name!r}; see list_tools()")
    return _REGISTRY[name]


def list_tools(family: str | None = None) -> list[Tool]:
    _load_all()
    tools = sorted(_REGISTRY.values(), key=lambda t: (t.family, t.name))
    if family:
        tools = [t for t in tools if t.family == family]
    return tools


def run_tool(name: str, **kwargs: Any) -> dict:
    """Invoke a tool with audit logging. Returns the tool's dict result.

    Every tool returns a dict; by convention it includes 'status' and, where
    files are produced, an 'artifacts' list of paths.
    """
    from helio_agent import http as hhttp
    t = get_tool(name)
    start = time.monotonic()
    input_sha256 = audit.hash_input_files(kwargs)
    hhttp.reset_touched()
    try:
        result = t.func(**kwargs)
        if not isinstance(result, dict):
            result = {"result": result}
        result.setdefault("status", "ok")
        elapsed = time.monotonic() - start
        summary = {k: v for k, v in result.items()
                   if k in ("status", "n_records", "n_results", "message", "summary")}
        audit_id = audit.record(name, kwargs, result["status"], elapsed,
                                result_summary=summary,
                                artifacts=result.get("artifacts", []),
                                cache_keys=hhttp.touched_keys(),
                                result=result, input_sha256=input_sha256)
        result["audit_id"] = audit_id
        return result
    except Exception as exc:  # noqa: BLE001 - tools surface all failure detail
        elapsed = time.monotonic() - start
        error_result = {"status": "error",
                        "error": f"{type(exc).__name__}: {exc}"}
        audit_id = audit.record(name, kwargs, "error", elapsed, error=str(exc),
                                cache_keys=hhttp.touched_keys(),
                                result=error_result, input_sha256=input_sha256)
        error_result["audit_id"] = audit_id
        return error_result


def replay(entry_id: str, readonly_cache: bool = True) -> dict:
    """Re-execute an audited tool call and compare artifact checksums.

    With readonly_cache (default) HTTP goes through the cache only, so a
    replay proves the recorded result is reproducible from recorded inputs;
    a CacheMiss means the original call predates the cache or bypassed it.
    Library-managed downloads (cdasws/Fido/pyspedas) hit their own file
    caches. Artifacts are re-written in place and compared by sha256.
    """
    import os
    e = audit.find_entry(entry_id)
    if e is None:
        return {"status": "error", "error": f"no audit entry {entry_id!r}"}
    current_inputs = audit.hash_input_files(e["args"])
    old_mode = os.environ.get("HELIO_CACHE_MODE")
    if readonly_cache:
        os.environ["HELIO_CACHE_MODE"] = "readonly"
    try:
        result = run_tool(e["tool"], **e["args"])
    finally:
        if readonly_cache:
            if old_mode is None:
                os.environ.pop("HELIO_CACHE_MODE", None)
            else:
                os.environ["HELIO_CACHE_MODE"] = old_mode
    old_hashes = e.get("artifact_sha256") or {}
    new_hashes = {a: audit.hash_file(a) for a in result.get("artifacts", [])}
    matches, mismatches = [], []
    for path in sorted(set(old_hashes) | set(new_hashes)):
        old = old_hashes.get(path)
        new = new_hashes.get(path)
        (matches if old is not None and new == old else mismatches).append(path)

    mismatch_dimensions = []
    unverifiable_dimensions = []
    if result.get("status") != e.get("status"):
        mismatch_dimensions.append("status")

    old_result = e.get("result")
    if old_result is None:
        if not old_hashes:
            unverifiable_dimensions.append("result")
    elif audit.canonical_result(result) != old_result:
        mismatch_dimensions.append("result")

    if "input_sha256" not in e:
        if not old_hashes:
            unverifiable_dimensions.append("inputs")
    elif current_inputs != (e.get("input_sha256") or {}):
        mismatch_dimensions.append("inputs")

    if mismatches:
        mismatch_dimensions.append("artifacts")
    if mismatch_dimensions:
        verdict = "mismatch"
    elif unverifiable_dimensions:
        verdict = "unverifiable"
    else:
        verdict = "match"
    return {"status": "ok", "verdict": verdict, "tool": e["tool"],
            "original_id": entry_id, "replay_id": result.get("audit_id"),
            "original_git_sha": e.get("git_sha"),
            "artifacts_matched": matches, "artifacts_mismatched": mismatches,
            "mismatch_dimensions": mismatch_dimensions,
            "unverifiable_dimensions": unverifiable_dimensions,
            "replay_status": result.get("status"),
            "replay_error": result.get("error")}


def _load_all() -> None:
    """Import all tool modules so their registrations run.

    Core tools come from helio_agent.tools; if a user profile is active
    (HELIO_AGENT_USER), every .py under users/<name>/tools/ is loaded too,
    tagged scope="user:<name>". User tools are one-off/paper-specific by
    policy (see users/README.md) — anything general belongs in core with a
    validation case.
    """
    global _CURRENT_SCOPE
    import helio_agent.tools  # noqa: F401

    from helio_agent.workspace import active_user, user_dir
    u = active_user()
    if not u:
        return
    tools_dir = (user_dir() or Path()) / "tools"
    if not tools_dir.is_dir():
        return
    import importlib.util
    for py in sorted(tools_dir.glob("*.py")):
        modname = f"helio_user_{u}_{py.stem}"
        if modname in sys.modules:
            continue
        _CURRENT_SCOPE = f"user:{u}"
        try:
            spec = importlib.util.spec_from_file_location(modname, py)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[modname] = mod
            spec.loader.exec_module(mod)
        finally:
            _CURRENT_SCOPE = "core"
