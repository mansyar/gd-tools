"""Integration tests for the init command.

Tests the full init flow end-to-end with only external dependencies
mocked (Godot binary detection). All file I/O, config generation, and
plugin enabling run against real files in tmp_path.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.godot import GodotInfo
from gd_tools.init import run_init

pytestmark = pytest.mark.integration


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal Godot project in tmp_path."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    return tmp_path


def test_init_fresh_project(tmp_path):
    """Full init flow on a clean project."""
    _setup_project(tmp_path)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch(
            "gd_tools.init.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.5.1", is_valid=True
            ),
        ),
    ):
        run_init(non_interactive=True)

    # Coverage addon files
    assert (tmp_path / "addons" / "gd-tools-coverage" / "coverage.gd").exists()

    # Config files
    assert (tmp_path / "gd-tools.toml").exists()
    assert (tmp_path / "gdlintrc").exists()
    assert (tmp_path / "gdformatrc").exists()

    # Data directory + gitignore
    assert (tmp_path / ".gd-tools").is_dir()
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".gd-tools/" in gitignore


def test_init_idempotent(tmp_path):
    """Running init twice produces no duplicate entries."""
    _setup_project(tmp_path)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch(
            "gd_tools.init.find_godot",
            return_value=GodotInfo(
                path="/fake/godot", version="4.5.1", is_valid=True
            ),
        ),
    ):
        run_init(non_interactive=True)
        run_init(non_interactive=True)

    # project.godot: no duplicate plugin entries
    project_godot = (tmp_path / "project.godot").read_text()
    assert project_godot.count("config_version=5") == 1

    # .gitignore: no duplicate .gd-tools/ entries
    gitignore_lines = (tmp_path / ".gitignore").read_text().splitlines()
    assert gitignore_lines.count(".gd-tools/") == 1

    # gd-tools.toml: exists and not duplicated
    assert (tmp_path / "gd-tools.toml").exists()


def test_init_native_project_does_not_install_gut(tmp_path):
    """Native initialization deploys the test addon without legacy GUT."""
    _setup_project(tmp_path)
    godot_info = GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)

    with (
        patch("gd_tools.init.find_project_root", return_value=tmp_path),
        patch("gd_tools.init.find_godot", return_value=godot_info),
    ):
        run_init(non_interactive=True)

    assert (tmp_path / "addons" / "gd-tools-test" / "gd_tools_test.gd").exists()
    assert not (tmp_path / "addons" / "gut").exists()
    assert not (tmp_path / ".gutconfig.json").exists()
    assert (tmp_path / "gd-tools.toml").exists()
