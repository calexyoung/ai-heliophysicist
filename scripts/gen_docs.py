"""Generate reference documentation from the live registry and skills tree.

    uv run python scripts/gen_docs.py          # write docs/TOOLS.md, docs/SKILLS.md
    uv run python scripts/gen_docs.py --check  # exit 1 if the files are stale

tests/test_docs_current.py runs --check, so the reference can never drift
from the code: every tool and every skill document is listed, always.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from helio_agent.registry import FAMILIES, list_tools  # noqa: E402

FAMILY_BLURB = {
    "discover": "Find datasets, spacecraft, events, and imagery in the archives. Read-only; nothing here downloads bulk data.",
    "retrieve": "Fetch data to the persistent workspace. Every retrieval writes a file (usually a UTC-indexed CSV with NaN fills) and returns its path.",
    "reduce": "Turn retrieved files into analysis-ready series and maps. Deterministic transforms; no science judgment embedded.",
    "measure": "Fit, correlate, model, and quantify. Scientific methods require an appropriate published, analytic, or cross-implementation anchor; supporting operations are guarded by offline tests and validated composition.",
    "literature": "NASA ADS and arXiv access for context and cross-checking.",
    "report": "Publication-styled figures, statistical plots, PDF reports, and self-hosted HTML export.",
}


def tools_md() -> str:
    tools = [t for t in list_tools() if t.scope == "core"]
    out = ["# Tool reference", "",
           "*Generated from the live registry by `scripts/gen_docs.py` — do not edit by hand.*",
           "", f"{len(tools)} core tools in six families. Invoke any tool with",
           "`uv run helio-agent run <tool> '<json-kwargs>'` or `run_tool(name, **kwargs)`;",
           "every call is audit-logged and returns a dict with `status` and `audit_id`.",
           "Tools that cannot honestly do what was asked return `status: \"error\"` with a",
           "`refusing: ...` message saying why and what to try instead.", ""]
    out.append("| Family | Tools |")
    out.append("|---|---|")
    for fam in FAMILIES:
        names = [t.name for t in tools if t.family == fam]
        out.append(f"| **{fam}** ({len(names)}) | " + ", ".join(f"`{n}`" for n in names) + " |")
    out.append("")
    for fam in FAMILIES:
        out.append(f"## {fam}")
        out.append("")
        out.append(FAMILY_BLURB[fam])
        out.append("")
        for t in tools:
            if t.family != fam:
                continue
            out.append(f"### `{t.name}`")
            out.append("")
            out.append("```python")
            out.append(t.signature())
            out.append("```")
            out.append("")
            out.append(t.doc.strip())
            out.append("")
            src = Path(t.func.__code__.co_filename).relative_to(ROOT)
            out.append(f"*Source: `{src}`*")
            out.append("")
    return "\n".join(out) + "\n"


def skills_md() -> str:
    skills_dir = ROOT / "skills"
    groups = {"missions": "Mission guides", "methods": "Method recipes",
              "datasources": "Data source guides", "tools": "Software notes"}
    files = sorted(p for p in skills_dir.rglob("*.md") if p.name != "README.md")
    out = ["# Skills catalog", "",
           "*Generated from `skills/` by `scripts/gen_docs.py` — do not edit by hand.*",
           "", f"{len(files)} knowledge documents the agent must read before acting",
           "(see `skills/README.md` for the composition rule: method + mission +",
           "datasource). Each entry shows the document's own one-line summary.", ""]
    for key, title in groups.items():
        group = [p for p in files if p.parent.name == key]
        if not group:
            continue
        out.append(f"## {title} (`skills/{key}/`, {len(group)})")
        out.append("")
        out.append("| Document | Summary |")
        out.append("|---|---|")
        for p in group:
            text = p.read_text()
            h1 = re.search(r"^#\s+(.+)$", text, re.M)
            quote = re.search(r"^>\s*(.+)$", text, re.M)
            name = h1.group(1).strip() if h1 else p.stem
            summ = quote.group(1).strip() if quote else ""
            summ = re.sub(r"^One-line:\s*", "", summ)
            rel = p.relative_to(ROOT)
            out.append(f"| [{name}]({'../' + str(rel)}) | {summ} |")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> int:
    targets = {ROOT / "docs" / "TOOLS.md": tools_md(),
               ROOT / "docs" / "SKILLS.md": skills_md()}
    if "--check" in sys.argv:
        stale = [str(p.relative_to(ROOT)) for p, c in targets.items()
                 if not p.exists() or p.read_text() != c]
        if stale:
            print("STALE (run `uv run python scripts/gen_docs.py`):", ", ".join(stale))
            return 1
        print("reference docs current")
        return 0
    for p, c in targets.items():
        p.write_text(c)
        print(f"wrote {p.relative_to(ROOT)} ({len(c.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
