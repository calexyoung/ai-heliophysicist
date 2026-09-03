"""Generate reference documentation from the live registry and skills tree.

    uv run python scripts/gen_docs.py          # write docs/TOOLS.md, docs/SKILLS.md,
                                               # and the README docs index
    uv run python scripts/gen_docs.py --check  # exit 1 if any of them are stale

tests/test_docs_current.py runs --check, so the reference can never drift
from the code: every tool and every skill document is listed, always, and
every file in docs/ is linked from README.md.

README.md is only partly generated: the script rewrites the blocks between
the `gen_docs:` markers (the docs index and the pointer line above it) and
leaves the rest of the file alone.
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


DOCS_INDEX_START = "<!-- gen_docs:docs-index start -->"
DOCS_INDEX_END = "<!-- gen_docs:docs-index end -->"
DOCS_LEAD_START = "<!-- gen_docs:docs-lead start -->"
DOCS_LEAD_END = "<!-- gen_docs:docs-lead end -->"

# The short pointer line near the top of the README: the handful of documents
# a first-time reader should open, and what to call each one. Order is this
# map's order; a doc absent here stays out of the line and appears only in the
# full index below it.
DOC_LEAD = {
    "USAGE.md": "Walkthroughs",
    "TOOLS.md": "every tool",
    "SKILLS.md": "every skill",
    "MODULES.md": "internals",
}

# One-line descriptions for the README index. Files listed here keep this
# order; anything else in docs/ is appended alphabetically with a summary
# derived from the document itself, so a new doc is always linked even
# before someone writes it a blurb.
DOC_BLURB = {
    "USAGE.md": "**Detailed usage documentation** \u2014 setup, CLI, workflows, troubleshooting",
    "TOOLS.md": "**Every tool**: signature + docstring, generated from the registry (drift fails CI)",
    "SKILLS.md": "**Every skill document**, cataloged with its one-line summary (generated)",
    "MODULES.md": "The `helio_agent` package module by module: registry, audit, cache, monitor, reports, tool modules",
    "ARCHITECTURE.md": "Full design, mapping to the AI Astrophysicist model",
    "helio_agent_review.md": "What the helio-agent harness taught this repo, and what was deliberately not ported",
    "helio_agent_merge_analysis.md": "Why helio-agent and ai-heliophysicist stay separate repositories",
}


def _derive_summary(path: Path) -> str:
    """First prose line of a document, for a docs file with no curated blurb."""
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        line = re.sub(r"^>\s*", "", line)
        line = re.sub(r"^\*(.+)\*$", r"\1", line)
        return line.rstrip(",;:") if line else ""
    return ""


def readme_docs_index() -> str:
    """The generated README block linking every file in docs/."""
    docs = sorted(p for p in (ROOT / "docs").glob("*.md"))
    curated = [p for key in DOC_BLURB for p in docs if p.name == key]
    rest = [p for p in docs if p.name not in DOC_BLURB]
    out = [DOCS_INDEX_START,
           "<!-- generated by scripts/gen_docs.py - do not edit by hand -->",
           "",
           f"### Reference documentation ({len(docs)})",
           "",
           "| Document | What |",
           "|---|---|"]
    for p in curated + rest:
        summ = DOC_BLURB.get(p.name) or _derive_summary(p)
        out.append(f"| [`docs/{p.name}`](docs/{p.name}) | {summ} |")
    out += ["", DOCS_INDEX_END]
    return "\n".join(out)


def readme_docs_lead() -> str:
    """The generated one-line README pointer to the documents that matter most."""
    missing = [n for n in DOC_LEAD if not (ROOT / "docs" / n).exists()]
    if missing:
        raise SystemExit(f"DOC_LEAD names missing docs: {', '.join(missing)}")
    parts = [f"[{label}](docs/{name})" for name, label in DOC_LEAD.items()]
    return "\n".join([DOCS_LEAD_START,
                      "<!-- generated by scripts/gen_docs.py - do not edit by hand -->",
                      "**\u2192 " + " \u00b7 ".join(parts) + "**",
                      DOCS_LEAD_END])


def _splice(text: str, start_marker: str, end_marker: str, block: str) -> str:
    start, end = text.find(start_marker), text.find(end_marker)
    if start == -1 or end == -1:
        raise SystemExit(
            f"README.md is missing the {start_marker} / {end_marker} markers; "
            "add them where the generated block belongs.")
    return text[:start] + block + text[end + len(end_marker):]


def readme_md() -> str:
    """README.md with only the generated blocks rewritten."""
    text = (ROOT / "README.md").read_text()
    text = _splice(text, DOCS_LEAD_START, DOCS_LEAD_END, readme_docs_lead())
    return _splice(text, DOCS_INDEX_START, DOCS_INDEX_END, readme_docs_index())


def main() -> int:
    targets = {ROOT / "docs" / "TOOLS.md": tools_md(),
               ROOT / "docs" / "SKILLS.md": skills_md(),
               ROOT / "README.md": readme_md()}
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
