"""Command-line interface for the tool layer.

Usage:
    helio-agent list [family]
    helio-agent describe <tool>
    helio-agent run <tool> '<json-args>'
    helio-agent replay <audit-id>
    helio-agent audit [n]

The LLM agent drives tools through `run`; each call is audit-logged.
"""

from __future__ import annotations

import json
import sys

from helio_agent.registry import get_tool, list_tools, run_tool
from helio_agent.audit import AUDIT_FILE


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = args[0]

    if cmd == "list":
        family = args[1] if len(args) > 1 else None
        current = None
        for t in list_tools(family):
            if t.family != current:
                current = t.family
                print(f"\n[{current}]")
            first_line = t.doc.splitlines()[0] if t.doc else ""
            tag = "" if t.scope == "core" else f" [{t.scope}]"
            print(f"  {t.name:32s}{tag} {first_line}")
        return 0

    if cmd == "describe":
        t = get_tool(args[1])
        print(f"{t.name}  (family: {t.family})")
        print(t.signature())
        print()
        print(t.doc)
        return 0

    if cmd == "run":
        name = args[1]
        kwargs = json.loads(args[2]) if len(args) > 2 else {}
        result = run_tool(name, **kwargs)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "ok" else 1

    if cmd == "replay":
        from helio_agent.registry import replay
        result = replay(args[1])
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("verdict") == "match" else 1

    if cmd == "report":
        from helio_agent.reports import REPORTS
        name = args[1] if len(args) > 1 else ""
        if name not in REPORTS:
            print(f"unknown report {name!r}; available: {list(REPORTS)}")
            return 1
        date = args[args.index("--date") + 1] if "--date" in args else None
        result = REPORTS[name](date=date, archive="--archive" in args)
        print(json.dumps(result, indent=2, default=str))
        return 0 if result.get("status") == "ok" else 1

    if cmd == "monitor":
        from helio_agent.monitor import cycle
        result = cycle()
        print(json.dumps(result, indent=2, default=str))
        return 1 if result.get("status") == "error" else 0

    if cmd == "audit":
        n = int(args[1]) if len(args) > 1 else 10
        if not AUDIT_FILE.exists():
            print("no audit entries yet")
            return 0
        lines = AUDIT_FILE.read_text().strip().splitlines()
        for line in lines[-n:]:
            e = json.loads(line)
            print(f"{e['ts']}  {e['status']:5s}  {e['tool']}  ({e['elapsed_s']}s)")
        return 0

    print(f"unknown command {cmd!r}; see --help")
    return 1


if __name__ == "__main__":
    sys.exit(main())
