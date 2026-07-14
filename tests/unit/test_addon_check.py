"""Unit tests for the stale addon detection module."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@patch("gd_tools.addon_check.find_project_root")
@patch("gd_tools.addon_check.__version__", "0.3.0")
def test_no_warning_when_versions_match(mock_find_root, tmp_path, capsys):
    """No warning when addon version equals package version."""
    addon_dir = tmp_path / "addons" / "gd-tools-coverage"
    addon_dir.mkdir(parents=True)
    (addon_dir / "_version.txt").write_text("0.3.0\n", encoding="utf-8")

    mock_find_root.return_value = tmp_path

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


@patch("gd_tools.addon_check.find_project_root")
@patch("gd_tools.addon_check.__version__", "0.3.0")
def test_stale_warning_when_addon_older(mock_find_root, tmp_path, capsys):
    """Stale warning printed to stderr when addon version < package version."""
    addon_dir = tmp_path / "addons" / "gd-tools-coverage"
    addon_dir.mkdir(parents=True)
    (addon_dir / "_version.txt").write_text("0.2.0\n", encoding="utf-8")

    mock_find_root.return_value = tmp_path

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "outdated" in captured.err
    assert "v0.2.0" in captured.err
    assert "v0.3.0" in captured.err


@patch("gd_tools.addon_check.find_project_root")
@patch("gd_tools.addon_check.__version__", "0.3.0")
def test_missing_file_warning(mock_find_root, tmp_path, capsys):
    """Missing file warning printed when version file is absent."""
    addon_dir = tmp_path / "addons" / "gd-tools-coverage"
    addon_dir.mkdir(parents=True)

    mock_find_root.return_value = tmp_path

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "version file not found" in captured.err
    assert "gd-tools init" in captured.err


@patch("gd_tools.addon_check.find_project_root")
@patch("gd_tools.addon_check.__version__", "0.3.0")
def test_no_warning_when_addon_newer(mock_find_root, tmp_path, capsys):
    """No warning when addon version > package version (downgrade scenario)."""
    addon_dir = tmp_path / "addons" / "gd-tools-coverage"
    addon_dir.mkdir(parents=True)
    (addon_dir / "_version.txt").write_text("0.4.0\n", encoding="utf-8")

    mock_find_root.return_value = tmp_path

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert captured.err == ""


@patch("gd_tools.addon_check.find_project_root")
@patch("gd_tools.addon_check.__version__", "0.3.0")
def test_stale_warning_when_unparseable(mock_find_root, tmp_path, capsys):
    """Stale warning printed when version string is unparseable."""
    addon_dir = tmp_path / "addons" / "gd-tools-coverage"
    addon_dir.mkdir(parents=True)
    (addon_dir / "_version.txt").write_text("not-a-version\n", encoding="utf-8")

    mock_find_root.return_value = tmp_path

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert "WARNING" in captured.err
    assert "outdated" in captured.err
    assert "not-a-version" in captured.err
    assert "v0.3.0" in captured.err


def test_suppressed_by_env_var(monkeypatch, capsys):
    """Check is fully suppressed when GD_TOOLS_NO_UPDATE_CHECK=1."""
    monkeypatch.setenv("GD_TOOLS_NO_UPDATE_CHECK", "1")

    from gd_tools.addon_check import check_addon_version

    check_addon_version()

    captured = capsys.readouterr()
    assert captured.err == ""


@patch("gd_tools.addon_check.find_project_root")
def test_fails_silently_on_unexpected_error(mock_find_root, capsys):
    """Check fails silently (no exception, no crash) on unexpected file system errors."""
    mock_find_root.side_effect = RuntimeError("Unexpected error")

    from gd_tools.addon_check import check_addon_version

    check_addon_version()  # Should not raise

    captured = capsys.readouterr()
    assert captured.err == ""
