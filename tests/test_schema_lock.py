"""Schema lock (pattern from helio-agent's test_schema_lock).

Each tool's signature (name, family, parameter names + annotations) is
hashed into tests/tool_schemas.lock.json. Changing a tool's interface
without regenerating the lock fails CI — interface drift becomes a
deliberate act, reviewed in the same diff.

Regenerate after an intentional change:
    uv run python tests/test_schema_lock.py --update
"""

import hashlib
import json
import sys
from pathlib import Path

from helio_agent.registry import list_tools

LOCK = Path(__file__).resolve().parent / "tool_schemas.lock.json"


def current_schemas() -> dict[str, str]:
    out = {}
    for t in list_tools():
        blob = json.dumps({"family": t.family, "params": t.params},
                          sort_keys=True)
        out[t.name] = hashlib.sha256(blob.encode()).hexdigest()[:16]
    return out


def test_tool_schemas_locked():
    assert LOCK.exists(), (
        "tests/tool_schemas.lock.json missing; generate with "
        "`uv run python tests/test_schema_lock.py --update`")
    locked = json.loads(LOCK.read_text())
    current = current_schemas()
    added = sorted(set(current) - set(locked))
    removed = sorted(set(locked) - set(current))
    changed = sorted(k for k in set(current) & set(locked)
                     if current[k] != locked[k])
    assert not (added or removed or changed), (
        f"tool interfaces drifted from lock — added={added} removed={removed} "
        f"changed={changed}; if intentional, regenerate the lock with "
        "`uv run python tests/test_schema_lock.py --update`")


if __name__ == "__main__":
    if "--update" in sys.argv:
        LOCK.write_text(json.dumps(current_schemas(), indent=1, sort_keys=True) + "\n")
        print(f"wrote {LOCK} ({len(current_schemas())} tools)")
    else:
        print(__doc__)
