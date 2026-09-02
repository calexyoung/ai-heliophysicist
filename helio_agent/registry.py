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
import time
from dataclasses import dataclass, field
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

    def signature(self) -> str:
        return f"{self.name}{inspect.signature(self.func)}"


def tool(family: str, name: str | None = None):
    """Register a function as an agent tool."""
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; must be one of {FAMILIES}")

    def deco(func: Callable) -> Callable:
        tname = name or func.__name__
        sig = inspect.signature(func)
        params = {p: str(v.annotation) for p, v in sig.parameters.items()}
        _REGISTRY[tname] = Tool(
            name=tname, family=family, func=func,
            doc=inspect.getdoc(func) or "", params=params,
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
                                cache_keys=hhttp.touched_keys())
        result["audit_id"] = audit_id
        return result
    except Exception as exc:  # noqa: BLE001 - tools surface all failure detail
        elapsed = time.monotonic() - start
        audit_id = audit.record(name, kwargs, "error", elapsed, error=str(exc),
                                cache_keys=hhttp.touched_keys())
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                "audit_id": audit_id}


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
    for path, old in old_hashes.items():
        if old is None:
            continue
        (matches if new_hashes.get(path) == old else mismatches).append(path)
    verdict = "match" if (result.get("status") == e.get("status")
                          and not mismatches) else "mismatch"
    return {"status": "ok", "verdict": verdict, "tool": e["tool"],
            "original_id": entry_id, "replay_id": result.get("audit_id"),
            "original_git_sha": e.get("git_sha"),
            "artifacts_matched": matches, "artifacts_mismatched": mismatches,
            "replay_status": result.get("status"),
            "replay_error": result.get("error")}


def _load_all() -> None:
    """Import all tool modules so their registrations run."""
    import helio_agent.tools  # noqa: F401
