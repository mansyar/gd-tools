"""Integration tests for the lint command.

Tests the full CLI flow: load_config → run_lint → format output → exit code.
Uses fixture .gd files from tests/fixtures/ and the real run_lint function
(only load_config is mocked since no project.godot exists in the test env).
"""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig

import pytest

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _copy_fixture(tmp_path: Path, name: str, dest_name: str | None = None):
    """Copy a fixture file into tmp_path, optionally renaming it."""
    src = FIXTURES_DIR / name
    dst = tmp_path / (dest_name or name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    return dst


def test_lint_full_run_text_output(tmp_path):
    """Full lint run with text output on a project with errors."""
    _copy_fixture(tmp_path, "clean.gd")
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path)])

    assert result.exit_code == 1
    # Table headers present
    assert "File" in result.output
    assert "Line" in result.output
    assert "Column" in result.output
    assert "Rule" in result.output
    assert "Severity" in result.output
    assert "Message" in result.output
    # The function-name rule should appear in the output
    assert "function-name" in result.output
    # Rich table may truncate long messages, so check a short fragment
    assert "is not valid" in result.output
    # Summary line
    assert "errors" in result.output
    assert "files checked" in result.output


def test_lint_full_run_json_output(tmp_path):
    """Full lint run with JSON output on a project with errors."""
    _copy_fixture(tmp_path, "clean.gd")
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(
            cli, ["lint", str(tmp_path), "--report-format", "json"]
        )

    assert result.exit_code == 1
    data = json.loads(result.output.strip())
    assert data["files_checked"] == 2
    assert len(data["errors"]) >= 1
    assert data["errors"][0]["rule"] == "function-name"
    assert "BadFunctionName" in data["errors"][0]["message"]
    assert data["warnings"] == []


def test_lint_excludes_respected(tmp_path):
    """Files in excluded directories (addons/) are not linted."""
    _copy_fixture(tmp_path, "clean.gd")
    _copy_fixture(tmp_path, "addons/plugin.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path)])

    # Only clean.gd was checked — no errors, exit 0
    assert result.exit_code == 0
    assert "[OK]" in result.output


def test_lint_fix_flag_noop(tmp_path):
    """--fix flag prints warning and does not modify files."""
    bad_file = _copy_fixture(tmp_path, "bad.gd")
    original_content = bad_file.read_text()

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path), "--fix"])

    # Warning message present
    assert "gdlint is read-only" in result.output
    assert "--fix has no effect" in result.output
    # File content unchanged
    assert bad_file.read_text() == original_content
    # Lint still ran (exit 1 because bad.gd has errors)
    assert result.exit_code == 1
