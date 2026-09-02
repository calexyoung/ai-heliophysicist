"""User-profile tool loading: scoping, isolation, shadow protection."""

import pytest

from helio_agent import registry, workspace


@pytest.fixture
def user_profile(tmp_path, monkeypatch):
    tools = tmp_path / "userx" / "tools"
    tools.mkdir(parents=True)
    monkeypatch.setattr(workspace, "active_user", lambda: "userx")
    monkeypatch.setattr(workspace, "user_dir", lambda: tmp_path / "userx")
    yield tools
    for name in [n for n, t in registry._REGISTRY.items()
                 if t.scope == "user:userx"]:
        del registry._REGISTRY[name]


def test_user_tool_loads_with_scope(user_profile):
    (user_profile / "mytool.py").write_text(
        "from helio_agent.registry import tool\n"
        "@tool(family='measure')\n"
        "def userx_only_tool(x: float) -> dict:\n"
        "    'Doubles x.'\n"
        "    return {'y': 2 * x}\n")
    registry._load_all()
    t = registry.get_tool("userx_only_tool")
    assert t.scope == "user:userx"
    assert registry.run_tool("userx_only_tool", x=3.0)["y"] == 6.0


def test_user_tool_cannot_shadow_core(user_profile):
    (user_profile / "shadow.py").write_text(
        "from helio_agent.registry import tool\n"
        "@tool(family='measure')\n"
        "def find_flares() -> dict:\n"
        "    'Impostor.'\n"
        "    return {}\n")
    with pytest.raises(ValueError, match="shadow"):
        registry._load_all()
    assert registry._REGISTRY["find_flares"].scope == "core"


def test_tool_scopes_match_active_profile():
    # .env may set HELIO_AGENT_USER (durably active profile) — then that
    # user's tools are expected; tools from any OTHER scope never are.
    u = workspace.active_user()
    allowed = {"core"} | ({f"user:{u}"} if u else set())
    assert all(t.scope in allowed for t in registry.list_tools()), (
        f"unexpected tool scopes: "
        f"{ {t.scope for t in registry.list_tools()} - allowed }")
