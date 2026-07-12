"""Unit tests for the shared file discovery module.

Covers .gd file discovery, recursive directory walking,
exclude pattern filtering, and case-insensitive extension
matching.
"""

from pathlib import Path

from gd_tools.file_discovery import discover_gd_files

import pytest

pytestmark = pytest.mark.unit

# --- File discovery ---


def test_discover_gd_files_recursive(tmp_path):
    """Test that .gd files are collected from nested directories."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "enemy.gd").write_text("extends Node\n")
    (tmp_path / "subdir" / "nested").mkdir()
    (tmp_path / "subdir" / "nested" / "boss.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert len(result) == 3
    files = [Path(f).name for f in result]
    assert "player.gd" in files
    assert "enemy.gd" in files
    assert "boss.gd" in files


def test_discover_gd_files_case_insensitive(tmp_path):
    """Test that .GD and .Gd extensions are also collected."""
    (tmp_path / "lower.gd").write_text("extends Node\n")
    (tmp_path / "upper.GD").write_text("extends Node\n")
    (tmp_path / "mixed.Gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert len(result) == 3
    files = [Path(f).name for f in result]
    assert "lower.gd" in files
    assert "upper.GD" in files
    assert "mixed.Gd" in files


def test_discover_gd_files_excludes(tmp_path):
    """Test that excluded directories are skipped by name."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text("extends Node\n")
    (tmp_path / ".godot").mkdir()
    (tmp_path / ".godot" / "imported.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=["addons", ".godot"])
    assert len(result) == 1
    assert Path(result[0]).name == "player.gd"


def test_discover_gd_files_excludes_nested(tmp_path):
    """Test that excluded directories are skipped at any nesting level."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.gd").write_text("extends Node\n")
    (tmp_path / "src" / "addons").mkdir()
    (tmp_path / "src" / "addons" / "plugin.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path), excludes=["addons"])
    assert len(result) == 1
    assert Path(result[0]).name == "main.gd"


def test_discover_gd_files_no_files(tmp_path):
    """Test that a directory with no .gd files returns an empty list."""
    (tmp_path / "readme.txt").write_text("hello\n")
    (tmp_path / "config.json").write_text("{}\n")

    result = discover_gd_files(str(tmp_path), excludes=[])
    assert result == []


def test_discover_gd_files_default_excludes(tmp_path):
    """Test that DEFAULT_EXCLUDES are used when excludes is None."""
    (tmp_path / "player.gd").write_text("extends Node\n")
    (tmp_path / "addons").mkdir()
    (tmp_path / "addons" / "plugin.gd").write_text("extends Node\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hook.gd").write_text("extends Node\n")

    result = discover_gd_files(str(tmp_path))
    assert len(result) == 1
    assert Path(result[0]).name == "player.gd"
