"""Regression tests for the coverage addon version gate.

RED phase: ``test --coverage`` must refuse with exit code 2
before dispatching any suite when a deployed addon it depends
on is stale or missing. The gate does not exist yet, so the
refusal tests fail and the pass-through tests pass.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit

CLI_VERSION = "0.9.0"
STALE_VERSION = "0.8.0"
NEWER_VERSION = "0.10.0"
COVERAGE_ADDON = "gd-tools-coverage"
NATIVE_ADDON = "gd-tools-test"


def _write_addon(root, addon, version):
    """Create an addon dir with or without a version file."""
    addon_dir = root / "addons" / addon
    addon_dir.mkdir(parents=True, exist_ok=True)
    if version is not None:
        (addon_dir / "_version.txt").write_text(
            f"{version}\n", encoding="utf-8"
        )


def _invoke_coverage(
    tmp_path,
    monkeypatch,
    coverage_version,
    native_version,
    suppress=False,
):
    """Invoke ``test --coverage`` against a fake project root.

    Returns the (Click result, run_native mock) pair so tests
    can assert the exit code and zero suites dispatched.
    """
    _write_addon(tmp_path, COVERAGE_ADDON, coverage_version)
    _write_addon(tmp_path, NATIVE_ADDON, native_version)
    if suppress:
        monkeypatch.setenv("GD_TOOLS_NO_UPDATE_CHECK", "1")
    else:
        monkeypatch.delenv("GD_TOOLS_NO_UPDATE_CHECK", raising=False)
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch(
            "gd_tools.commands.test.load_config",
            return_value=mock_config,
        ),
        patch(
            "gd_tools.commands.test.run_native_test_command",
            return_value=MagicMock(),
        ) as mock_run,
        patch(
            "gd_tools.addon_check.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.config.find_project_root",
            return_value=tmp_path,
        ),
        patch("gd_tools.addon_check.__version__", CLI_VERSION),
        patch("gd_tools.__version__", CLI_VERSION),
        patch(
            "gd_tools.commands.test.__version__",
            CLI_VERSION,
            create=True,
        ),
        patch(
            "gd_tools.cli.check_for_update",
            return_value=None,
        ),
        patch(
            "gd_tools.cli.check_addon_version",
            return_value=None,
        ),
    ):
        result = runner.invoke(cli, ["test", "--coverage"])
    return result, mock_run


def test_stale_coverage_addon_refuses(tmp_path, monkeypatch):
    """Stale coverage addon aborts before dispatch (AC-1)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, STALE_VERSION, CLI_VERSION
    )
    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_missing_coverage_version_refuses(tmp_path, monkeypatch):
    """Missing coverage version file refuses (AC-2)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, None, CLI_VERSION
    )
    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_unparseable_coverage_version_refuses(tmp_path, monkeypatch):
    """Unparseable coverage version is stale (AC-7)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, "not-a-version", CLI_VERSION
    )
    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_stale_native_addon_refuses(tmp_path, monkeypatch):
    """Stale native test addon refuses (AC-3)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, CLI_VERSION, STALE_VERSION
    )
    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_missing_native_version_refuses(tmp_path, monkeypatch):
    """Missing native test version file refuses (AC-3)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, CLI_VERSION, None
    )
    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_gate_suppressed_by_env_var(tmp_path, monkeypatch):
    """GD_TOOLS_NO_UPDATE_CHECK=1 skips the gate (AC-4)."""
    result, mock_run = _invoke_coverage(
        tmp_path,
        monkeypatch,
        STALE_VERSION,
        STALE_VERSION,
        suppress=True,
    )
    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_newer_addon_proceeds(tmp_path, monkeypatch):
    """Deployed addon newer than CLI never refuses (AC-5)."""
    result, mock_run = _invoke_coverage(
        tmp_path, monkeypatch, NEWER_VERSION, NEWER_VERSION
    )
    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_refusal_names_versions_fix_and_abort(tmp_path, monkeypatch):
    """Refusal names versions, fix, and abort note (AC-6)."""
    result, _ = _invoke_coverage(
        tmp_path, monkeypatch, STALE_VERSION, CLI_VERSION
    )
    assert result.exit_code == 2
    assert STALE_VERSION in result.output
    assert CLI_VERSION in result.output
    assert "gd-tools init" in result.output
    assert "abort" in result.output.lower()
