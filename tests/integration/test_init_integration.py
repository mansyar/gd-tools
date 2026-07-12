"""Integration tests for the init command.

Tests the full init flow end-to-end with only external dependencies
mocked (Godot binary detection, network downloads). All file I/O,
config generation, and plugin enabling run against real files in tmp_path.
"""

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from gd_tools.godot import GodotInfo
from gd_tools.init import run_init

pytestmark = pytest.mark.integration


def _create_fake_gut_zip(version: str = "9.5.0") -> bytes:
    """Create a fake GUT archive zip in memory.

    The zip mirrors the real GUT GitHub archive structure:
    Gut-<version>/addons/gut/gut.gd and plugin.cfg
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            f"Gut-{version}/addons/gut/gut.gd",
            "extends Node\n",
        )
        zf.writestr(
            f"Gut-{version}/addons/gut/plugin.cfg",
            f'[plugin]\nname="Gut"\nversion="{version}"\n',
        )
    return buf.getvalue()


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal Godot project in tmp_path."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    return tmp_path


def test_init_fresh_project(tmp_path):
    """Full init flow on a clean project with mocked Godot/GUT download."""
    _setup_project(tmp_path)
    fake_zip = _create_fake_gut_zip()

    mock_response = Mock()
    mock_response.content = fake_zip
    mock_response.raise_for_status = Mock()

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch(
            "gd_tools.init.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.5.1", is_valid=True
            ),
        ),
        patch("gd_tools.init.requests.get", return_value=mock_response),
    ):
        run_init(non_interactive=True)

    # GUT addon files
    assert (tmp_path / "addons" / "gut" / "gut.gd").exists()
    assert (tmp_path / "addons" / "gut" / "plugin.cfg").exists()

    # Coverage addon files
    assert (tmp_path / "addons" / "gd-tools-coverage" / "coverage.gd").exists()
    assert (
        tmp_path / "addons" / "gd-tools-coverage" / "pre_run_hook.gd"
    ).exists()
    assert (
        tmp_path / "addons" / "gd-tools-coverage" / "post_run_hook.gd"
    ).exists()

    # Config files
    assert (tmp_path / ".gutconfig.json").exists()
    assert (tmp_path / "gd-tools.toml").exists()
    assert (tmp_path / "gdlintrc").exists()
    assert (tmp_path / "gdformatrc").exists()

    # Data directory + gitignore
    assert (tmp_path / ".gd-tools").is_dir()
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".gd-tools/" in gitignore

    # GUT plugin enabled in project.godot
    project_godot = (tmp_path / "project.godot").read_text()
    assert "res://addons/gut/plugin.gd" in project_godot
    assert "[editor_plugins]" in project_godot


def test_init_project_with_existing_gut(tmp_path):
    """GUT already installed — no download attempt, plugin still enabled."""
    _setup_project(tmp_path)

    # Pre-install GUT
    gut_dir = tmp_path / "addons" / "gut"
    gut_dir.mkdir(parents=True)
    (gut_dir / "gut.gd").write_text("extends Node\n")
    (gut_dir / "plugin.cfg").write_text(
        '[plugin]\nname="Gut"\nversion="9.5.0"\n'
    )

    fake_zip = _create_fake_gut_zip()
    mock_response = Mock()
    mock_response.content = fake_zip
    mock_response.raise_for_status = Mock()

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch(
            "gd_tools.init.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.5.1", is_valid=True
            ),
        ),
        patch(
            "gd_tools.init.requests.get", return_value=mock_response
        ) as mock_get,
    ):
        run_init(non_interactive=True)

    # GUT was NOT downloaded
    mock_get.assert_not_called()

    # GUT plugin still enabled in project.godot
    project_godot = (tmp_path / "project.godot").read_text()
    assert "res://addons/gut/plugin.gd" in project_godot

    # Other artifacts still created
    assert (tmp_path / ".gutconfig.json").exists()
    assert (tmp_path / "gd-tools.toml").exists()
    assert (tmp_path / ".gd-tools").is_dir()


def test_init_idempotent(tmp_path):
    """Running init twice produces no duplicate entries."""
    _setup_project(tmp_path)
    fake_zip = _create_fake_gut_zip()

    mock_response = Mock()
    mock_response.content = fake_zip
    mock_response.raise_for_status = Mock()

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch(
            "gd_tools.init.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.5.1", is_valid=True
            ),
        ),
        patch("gd_tools.init.requests.get", return_value=mock_response),
    ):
        run_init(non_interactive=True)
        run_init(non_interactive=True)

    # project.godot: no duplicate plugin entries
    project_godot = (tmp_path / "project.godot").read_text()
    assert project_godot.count("res://addons/gut/plugin.gd") == 1
    assert project_godot.count("[editor_plugins]") == 1

    # .gitignore: no duplicate .gd-tools/ entries
    gitignore_lines = (tmp_path / ".gitignore").read_text().splitlines()
    assert gitignore_lines.count(".gd-tools/") == 1

    # .gutconfig.json: valid JSON (not duplicated)
    gutconfig = json.loads((tmp_path / ".gutconfig.json").read_text())
    assert "dirs" in gutconfig
    assert "pre_run_script" in gutconfig

    # gd-tools.toml: exists and not duplicated
    assert (tmp_path / "gd-tools.toml").exists()
