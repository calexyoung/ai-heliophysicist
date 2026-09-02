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


def record(tool_name: str, args: dict, status: str, elapsed_s: float,
           result_summary: Any = None, error: str | None = None,
           artifacts: list[str] | None = None) -> str:
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
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry_id
