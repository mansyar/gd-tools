"""Unit tests for the ``gd-tools clean`` CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def _make_project(root: Path) -> None:
    """Create a minimal .gd-tools layout with one known artifact."""
    gd = root / ".gd-tools"
    (gd / "coverage").mkdir(parents=True)
    (gd / "coverage" / "coverage.json").write_text("x" * 100, encoding="utf-8")
    (gd / "artifacts" / "run_1").mkdir(parents=True)
    (gd / "artifacts" / "run_1" / "result.xml").write_text(
        "y" * 50, encoding="utf-8"
    )
    (root / "gd-tools.toml").write_text("[test]\n", encoding="utf-8")


def _invoke_in(tmp_path: Path, args: list[str]):
    runner = CliRunner()
    import os

    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return runner.invoke(cli, args)
    finally:
        os.chdir(cwd)


def test_clean_with_no_flags_prints_inventory_and_hint(tmp_path):
    _make_project(tmp_path)
    result = _invoke_in(tmp_path, ["clean"])
    assert result.exit_code == 0
    assert "coverage" in result.output
    assert "artifacts" in result.output
    # Hint pointing at how to actually delete.
    assert "--all" in result.output or "--coverage" in result.output
    # Nothing was deleted.
    assert (tmp_path / ".gd-tools" / "coverage" / "coverage.json").exists()
    assert (tmp_path / ".gd-tools" / "artifacts" / "run_1").exists()


def test_clean_dry_run_reports_would_remove_and_keeps_files(tmp_path):
    _make_project(tmp_path)
    result = _invoke_in(tmp_path, ["clean", "--all", "--dry-run"])
    assert result.exit_code == 0
    assert "would remove" in result.output.lower()
    assert (tmp_path / ".gd-tools" / "coverage" / "coverage.json").exists()
    assert (
        tmp_path / ".gd-tools" / "artifacts" / "run_1" / "result.xml"
    ).exists()


def test_clean_coverage_removes_dir_and_prints_summary(tmp_path):
    _make_project(tmp_path)
    result = _invoke_in(tmp_path, ["clean", "--coverage"])
    assert result.exit_code == 0
    assert not (tmp_path / ".gd-tools" / "coverage").exists()
    # Summary mentions the freed amount and the removed target.
    assert "coverage" in result.output
    assert "100" in result.output  # coverage.json is 100 bytes
    # artifacts survive
    assert (
        tmp_path / ".gd-tools" / "artifacts" / "run_1" / "result.xml"
    ).exists()


def test_clean_all_removes_everything_but_config(tmp_path):
    _make_project(tmp_path)
    result = _invoke_in(tmp_path, ["clean", "--all"])
    assert result.exit_code == 0
    assert not (tmp_path / ".gd-tools" / "coverage").exists()
    assert not (tmp_path / ".gd-tools" / "artifacts").exists()
    assert (tmp_path / ".gd-tools").exists()
    assert (tmp_path / "gd-tools.toml").exists()


def test_clean_reports_nothing_to_remove_without_error(tmp_path):
    result = _invoke_in(tmp_path, ["clean", "--all"])
    assert result.exit_code == 0
    assert "nothing to remove" in result.output.lower()


def test_clean_failure_exits_2_with_path(tmp_path):
    _make_project(tmp_path)
    target = tmp_path / ".gd-tools" / "coverage"

    def boom(path, *args, **kwargs):
        if path == target:
            raise PermissionError(f"cannot remove {path}")

    with patch("gd_tools.clean._remove_path", side_effect=boom):
        result = _invoke_in(tmp_path, ["clean", "--coverage"])
    assert result.exit_code == 2
    assert str(target) in result.output


def test_clean_help_documents_flags_and_all_override(tmp_path):
    result = _invoke_in(tmp_path, ["clean", "--help"])
    assert result.exit_code == 0
    for flag in [
        "--coverage",
        "--artifacts",
        "--baselines",
        "--cache",
        "--all",
        "--dry-run",
    ]:
        assert flag in result.output
    assert "override" in result.output.lower()
