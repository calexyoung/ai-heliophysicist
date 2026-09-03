"""Generated workspace paths cannot escape their assigned directories."""

import pytest

from helio_agent import workspace


@pytest.fixture
def isolated_workspace(tmp_path, monkeypatch):
    data = tmp_path / "workspace" / "data"
    output = tmp_path / "workspace" / "outputs"
    monkeypatch.setattr(workspace, "DATA_DIR", data)
    monkeypatch.setattr(workspace, "OUTPUT_DIR", output)
    return data, output


def test_nested_output_stays_inside_workspace(isolated_workspace):
    _, output = isolated_workspace
    got = workspace.output_path("figures/result.png")
    assert got == output / "figures" / "result.png"
    assert got.parent.is_dir()


@pytest.mark.parametrize("name", ["../escape.txt", "../../.env", "/tmp/escape.txt"])
def test_output_path_rejects_escape(isolated_workspace, name):
    with pytest.raises(ValueError, match="outside workspace|relative"):
        workspace.output_path(name)


def test_data_path_rejects_symlink_escape(isolated_workspace, tmp_path):
    data, _ = isolated_workspace
    data.mkdir(parents=True)
    (data / "link").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="outside workspace"):
        workspace.data_path("link/escape.txt")
