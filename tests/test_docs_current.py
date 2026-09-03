"""Docs must match the live registry (pattern from helio-agent).

The README/architecture tool counts drifted three times before this test
existed. Any change to the registry without a docs update now fails CI.
"""

import ast
import re
from pathlib import Path

from helio_agent.registry import FAMILIES, list_tools

ROOT = Path(__file__).resolve().parent.parent


def _core_count():
    return sum(1 for t in list_tools() if t.scope == "core")


def _directly_validated_tools() -> set[str]:
    tree = ast.parse((ROOT / "validation" / "run_validation.py").read_text())
    return {
        node.args[0].value
        for node in ast.walk(tree)
        if (isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "run_tool"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str))
    }


def test_readme_tool_count_matches_registry():
    n = _core_count()
    readme = (ROOT / "README.md").read_text()
    m = re.search(r"(\d+) tools", readme)
    assert m, "README must state the tool count as '<N> tools'"
    assert int(m.group(1)) == n, (
        f"README says {m.group(1)} tools but the registry has {n}; "
        "update README.md and docs/ARCHITECTURE.md")


def test_architecture_tool_count_matches_registry():
    n = _core_count()
    arch = (ROOT / "docs" / "ARCHITECTURE.md").read_text()
    m = re.search(r"(\d+) tools wrapping sunpy", arch)
    assert m and int(m.group(1)) == n, (
        f"docs/ARCHITECTURE.md tool count != registry ({n})")


def test_readme_distinguishes_direct_validation_from_supporting_tools():
    direct = _directly_validated_tools()
    core = {t.name for t in list_tools() if t.scope == "core"}
    assert direct <= core
    readme = (ROOT / "README.md").read_text()
    match = re.search(r"(\d+) are directly exercised", readme)
    assert match, "README must distinguish directly exercised tools"
    assert int(match.group(1)) == len(direct)
    assert "supporting tools" in readme.lower()


def test_every_family_documented_in_readme():
    readme = (ROOT / "README.md").read_text()
    for fam in FAMILIES:
        assert f"**{fam}**" in readme, f"README missing family section {fam!r}"


def test_every_tool_has_docstring():
    for t in list_tools():
        assert t.doc.strip(), f"tool {t.name} has no docstring"


def test_reference_docs_current():
    """docs/TOOLS.md and docs/SKILLS.md are generated; they must match the
    registry and skills tree exactly (regenerate: uv run python scripts/gen_docs.py)."""
    import subprocess, sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_docs.py"), "--check"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
