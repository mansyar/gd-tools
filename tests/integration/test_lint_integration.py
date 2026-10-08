"""Integration tests for the lint command.

Tests the full CLI flow: load_config → run_lint → format output → exit code.
Uses fixture .gd files from tests/fixtures/ and the real run_lint function
(only load_config is mocked since no project.godot exists in the test env).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig

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
    # Flat line format: file:line:col: rule: message  [SEVERITY]
    assert "function-name" in result.output
    assert "BadFunctionName" in result.output
    assert "[ERROR]" in result.output
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


def test_lint_matches_bare_gdlint_on_gdlintrc_disable(tmp_path, monkeypatch):
    """gd-tools lint and bare gdlint agree on a gdlintrc disable list.

    Regression for the adoption report: a ``disable:`` entry in
    gdlintrc was honored by bare gdlint but ignored by
    ``gd-tools lint`` because ``run_lint`` called ``lint_code``
    without a config.
    """
    source = "extends Node\n\nvar later = 1\nconst EARLIER = 1\n"
    (tmp_path / "order.gd").write_text(source, encoding="utf-8")
    (tmp_path / "gdlintrc").write_text(
        "disable:\n  - class-definitions-order\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    # Bare gdlint honors the disable list.
    bare = subprocess.run(
        [sys.executable, "-m", "gdtoolkit.linter", "order.gd"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert bare.returncode == 0, bare.stdout + bare.stderr
    assert "class-definitions-order" not in bare.stdout

    # gd-tools lint honors it too.
    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "class-definitions-order" not in result.output


def test_lint_matches_bare_gdlint_without_disables(tmp_path, monkeypatch):
    """With nothing disabled both tools report the rule violation.

    An explicit empty ``disable:`` list keeps the test hermetic — an
    ambient gdlintrc above the tmp tree must not influence gdlint.
    """
    source = "extends Node\n\nvar later = 1\nconst EARLIER = 1\n"
    (tmp_path / "order.gd").write_text(source, encoding="utf-8")
    (tmp_path / "gdlintrc").write_text("disable: []\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    bare = subprocess.run(
        [sys.executable, "-m", "gdtoolkit.linter", "order.gd"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert bare.returncode == 1, bare.stdout + bare.stderr

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path)])

    assert result.exit_code == 1
    assert "class-definitions-order" in result.output


def test_lint_explicit_config_path_flag(tmp_path, monkeypatch):
    """--lint-config points at a config outside the discovered search."""
    source = "extends Node\n\nvar later = 1\nconst EARLIER = 1\n"
    project = tmp_path / "proj"
    project.mkdir()
    (project / "order.gd").write_text(source, encoding="utf-8")
    rc = tmp_path / "elsewhere.yaml"
    rc.write_text("disable:\n  - class-definitions-order\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(
            cli, ["lint", str(project), "--lint-config", str(rc)]
        )

    assert result.exit_code == 0, result.output
    assert "class-definitions-order" not in result.output
