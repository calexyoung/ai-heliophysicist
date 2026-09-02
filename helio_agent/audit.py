"""Audit trail: every tool call, its arguments, outcome, and artifacts.

Append-only JSONL. Nothing happens off the record; any number in a report can
be traced back to the exact call that produced it.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from helio_agent.workspace import LOG_DIR, ensure_dirs

AUDIT_FILE = LOG_DIR / "audit.jsonl"


def _jsonable(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


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
           cache_keys: list[str] | None = None) -> str:
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
        "error": error,
        "artifacts": artifacts or [],
        "git_sha": git_sha(),
        "cache_keys": cache_keys or [],
        "artifact_sha256": {a: hash_file(a) for a in (artifacts or [])},
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
