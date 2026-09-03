"""Audit trail: every tool call, its arguments, outcome, and artifacts.

Append-only JSONL. Nothing happens off the record; any number in a report can
be traced back to the exact call that produced it.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from pathlib import Path
from typing import Any

from helio_agent.workspace import LOG_DIR, ensure_dirs

AUDIT_FILE = LOG_DIR / "audit.jsonl"


def _jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


def canonical_result(obj: Any) -> Any:
    """Return a stable JSON-safe representation of a tool result."""
    if isinstance(obj, dict):
        return {str(k): canonical_result(v) for k, v in sorted(obj.items())
                if k != "audit_id"}
    if isinstance(obj, (list, tuple)):
        return [canonical_result(v) for v in obj]
    if isinstance(obj, set):
        return sorted((canonical_result(v) for v in obj), key=repr)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return canonical_result(item())
        except (TypeError, ValueError):
            pass
    return repr(obj)


def hash_input_files(args: Any) -> dict[str, str]:
    """Hash every existing regular-file path found in nested arguments."""
    found: dict[str, str] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple, set)):
            for child in value:
                visit(child)
        elif isinstance(value, (str, Path)):
            try:
                path = Path(value)
                if path.is_file():
                    resolved = str(path.resolve())
                    digest = hash_file(resolved)
                    if digest is not None:
                        found[resolved] = digest
            except (OSError, ValueError):
                return

    visit(args)
    return dict(sorted(found.items()))


_GIT_SHA: str | None = None


def git_sha() -> str:
    """Current repo commit (+ '-dirty' if the tree has changes); cached."""
    global _GIT_SHA
    if _GIT_SHA is None:
        import subprocess
        from helio_agent.workspace import ROOT
        try:
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                 cwd=ROOT, capture_output=True, text=True,
                                 timeout=5).stdout.strip()
            dirty = subprocess.run(["git", "status", "--porcelain"],
                                   cwd=ROOT, capture_output=True, text=True,
                                   timeout=5).stdout.strip()
            _GIT_SHA = (sha + ("-dirty" if dirty else "")) if sha else "unknown"
        except Exception:  # noqa: BLE001 - git absence must not break tools
            _GIT_SHA = "unknown"
    return _GIT_SHA


def hash_file(path: str) -> str | None:
    import hashlib
    from pathlib import Path
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record(tool_name: str, args: dict, status: str, elapsed_s: float,
           result_summary: Any = None, error: str | None = None,
           artifacts: list[str] | None = None,
           cache_keys: list[str] | None = None,
           result: Any = None,
           input_sha256: dict[str, str] | None = None) -> str:
    ensure_dirs()
    entry_id = uuid.uuid4().hex[:12]
    entry = {
        "id": entry_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "tool": tool_name,
        "args": {k: _jsonable(v) for k, v in args.items()},
        "status": status,
        "elapsed_s": round(elapsed_s, 3),
        "result_summary": _jsonable(result_summary),
        "result": canonical_result(result),
        "error": error,
        "artifacts": artifacts or [],
        "git_sha": git_sha(),
        "cache_keys": cache_keys or [],
        "artifact_sha256": {a: hash_file(a) for a in (artifacts or [])},
        "input_sha256": input_sha256 or {},
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry_id


def find_entry(entry_id: str) -> dict | None:
    if not AUDIT_FILE.exists():
        return None
    for line in AUDIT_FILE.read_text().splitlines():
        e = json.loads(line)
        if e.get("id") == entry_id:
            return e
    return None
