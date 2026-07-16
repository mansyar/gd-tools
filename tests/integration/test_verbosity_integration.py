"""Integration tests for --verbose and --quiet global flags.

Tests the full CLI flow with verbosity flags across lint, format, and
doctor commands. Verifies that verbose mode shows underlying commands
and timing, quiet mode suppresses non-essential output, and default mode
matches current behavior.

Only load_config and external dependencies (Godot, network) are mocked.
The real run_lint, run_format, and run_doctor functions execute against
fixture .gd files in tmp_path.
"""

import io
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.config import GdToolsConfig
from gd_tools.godot import GodotInfo

pytestmark = pytest.mark.integration

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_verbosity():
    """Reset verbosity to DEFAULT after each test to avoid state leakage."""
    yield
    from gd_tools.verbosity import Verbosity, set_verbosity

    set_verbosity(Verbosity.DEFAULT)


@pytest.fixture(autouse=True)
def _mock_update_check():
    """Prevent update check network calls in integration tests."""
    with (
        patch("gd_tools.cli.check_for_update", return_value=None),
        patch("gd_tools.cli.check_addon_version", return_value=None),
    ):
        yield


def _copy_fixture(tmp_path: Path, name: str, dest_name: str | None = None):
    """Copy a fixture file into tmp_path, optionally renaming it."""
    src = FIXTURES_DIR / name
    dst = tmp_path / (dest_name or name)
    dst.parent.mkdir(parents=True, exist_ok=True)
    import shutil

    shutil.copy(src, dst)
    return dst


# ---------------------------------------------------------------------------
# Verbose mode — lint
# ---------------------------------------------------------------------------


def test_verbose_lint_shows_file_being_linted(tmp_path):
    """--verbose lint shows each file being linted."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--verbose", "lint", str(tmp_path)])

    assert result.exit_code == 1
    assert "Linting:" in result.output
    assert "bad.gd" in result.output


def test_verbose_lint_shows_timing(tmp_path):
    """--verbose lint shows elapsed time."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--verbose", "lint", str(tmp_path)])

    assert result.exit_code == 1
    assert "Elapsed:" in result.output


def test_default_lint_no_verbose_output(tmp_path):
    """Default mode (no flag) does not show verbose output."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["lint", str(tmp_path)])

    assert result.exit_code == 1
    assert "Linting:" not in result.output
    assert "Elapsed:" not in result.output


# ---------------------------------------------------------------------------
# Quiet mode — lint
# ---------------------------------------------------------------------------


def test_quiet_lint_shows_only_violations(tmp_path):
    """--quiet lint shows violations but suppresses info messages."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--quiet", "lint", str(tmp_path)])

    assert result.exit_code == 1
    # Violations are still shown
    assert "function-name" in result.output
    assert "BadFunctionName" in result.output
    assert "[ERROR]" in result.output


def test_quiet_lint_no_files_suppressed(tmp_path):
    """--quiet lint with no files suppresses the info message."""
    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--quiet", "lint", str(tmp_path)])

    assert result.exit_code == 0
    # "No GDScript files found" is an info message, suppressed in quiet
    assert "No GDScript files found" not in result.output


# ---------------------------------------------------------------------------
# Verbose mode — format
# ---------------------------------------------------------------------------


def test_verbose_format_shows_file_being_formatted(tmp_path):
    """--verbose format shows each file being formatted."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--verbose", "format", str(tmp_path)])

    assert result.exit_code == 0
    assert "Formatting:" in result.output
    assert "bad.gd" in result.output


def test_verbose_format_shows_timing(tmp_path):
    """--verbose format shows elapsed time."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--verbose", "format", str(tmp_path)])

    assert result.exit_code == 0
    assert "Elapsed:" in result.output


def test_default_format_no_verbose_output(tmp_path):
    """Default mode (no flag) does not show verbose output."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["format", str(tmp_path)])

    assert result.exit_code == 0
    assert "Formatting:" not in result.output
    assert "Elapsed:" not in result.output


# ---------------------------------------------------------------------------
# Quiet mode — format
# ---------------------------------------------------------------------------


def test_quiet_format_shows_results(tmp_path):
    """--quiet format shows format results but suppresses info messages."""
    _copy_fixture(tmp_path, "bad.gd")

    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--quiet", "format", str(tmp_path)])

    assert result.exit_code == 0
    # Summary is still shown
    assert "Formatted" in result.output


def test_quiet_format_no_files_suppressed(tmp_path):
    """--quiet format with no files suppresses the info message."""
    runner = CliRunner()
    mock_config = GdToolsConfig()
    with patch("gd_tools.cli.load_config", return_value=mock_config):
        result = runner.invoke(cli, ["--quiet", "format", str(tmp_path)])

    assert result.exit_code == 0
    # "No .gd files found" is an info message, suppressed in quiet
    assert "No .gd files found" not in result.output


# ---------------------------------------------------------------------------
# Quiet mode — doctor
# ---------------------------------------------------------------------------


def _create_fake_gut_zip(version: str = "9.5.0") -> bytes:
    """Create a fake GUT archive zip in memory."""
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


def test_quiet_doctor_shows_one_line_pass(tmp_path, monkeypatch):
    """--quiet doctor shows one-line pass status, no detailed table."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    fake_zip = _create_fake_gut_zip()
    mock_response = Mock()
    mock_response.content = fake_zip
    mock_response.raise_for_status = Mock()

    godot_info = GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)

    # Run init first to set up the project
    with (
        patch("gd_tools.init.find_godot", return_value=godot_info),
        patch("gd_tools.init.requests.get", return_value=mock_response),
    ):
        from gd_tools.init import run_init

        run_init(non_interactive=True)

    # Run doctor with --quiet
    runner = CliRunner()
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = runner.invoke(cli, ["--quiet", "doctor"])

    assert result.exit_code == 0
    assert "[OK]" in result.output
    assert "All checks passed" in result.output
    # Detailed table not shown
    assert "Godot Binary" not in result.output


def test_quiet_doctor_shows_one_line_fail(tmp_path, monkeypatch):
    """--quiet doctor shows one-line fail status, no detailed table."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    godot_info = GodotInfo(path="/fake/godot", version="4.6.2", is_valid=True)

    runner = CliRunner()
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = runner.invoke(cli, ["--quiet", "doctor"])

    assert result.exit_code == 1
    assert "[FAIL]" in result.output
    assert "Some checks failed" in result.output
    # Detailed table not shown
    assert "Godot Binary" not in result.output


def test_default_doctor_shows_full_table(tmp_path, monkeypatch):
    """Default mode (no flag) shows full doctor table."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    godot_info = GodotInfo(path="/fake/godot", version="4.6.2", is_valid=True)

    runner = CliRunner()
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = runner.invoke(cli, ["doctor"])

    # Default mode shows the full table
    assert "Godot Binary" in result.output


# ---------------------------------------------------------------------------
# Mutual exclusion
# ---------------------------------------------------------------------------


def test_verbose_quiet_mutual_exclusion():
    """--verbose and --quiet together produce exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--verbose", "--quiet", "lint"])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_verbose_quiet_short_flags_mutual_exclusion():
    """-v and -q together produce exit code 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["-v", "-q", "lint"])

    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


# ---------------------------------------------------------------------------
# Quiet mode — update check suppression
# ---------------------------------------------------------------------------


def test_quiet_suppresses_update_notification(tmp_path, monkeypatch):
    """--quiet suppresses update check notification."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    godot_info = GodotInfo(path="/fake/godot", version="4.6.2", is_valid=True)

    runner = CliRunner()
    with (
        patch(
            "gd_tools.cli.check_for_update", return_value="99.0.0"
        ) as mock_check,
        patch("gd_tools.cli.check_addon_version", return_value=None),
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = runner.invoke(cli, ["--quiet", "doctor"])

    # check_for_update should NOT be called in quiet mode
    mock_check.assert_not_called()
    assert result.exit_code == 1


def test_default_calls_update_check(tmp_path, monkeypatch):
    """Default mode (no flag) calls update check."""
    _setup_project(tmp_path)
    monkeypatch.chdir(tmp_path)

    godot_info = GodotInfo(path="/fake/godot", version="4.6.2", is_valid=True)

    runner = CliRunner()
    with (
        patch("gd_tools.cli.check_for_update", return_value=None) as mock_check,
        patch("gd_tools.cli.check_addon_version", return_value=None),
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        result = runner.invoke(cli, ["doctor"])

    # check_for_update SHOULD be called in default mode
    mock_check.assert_called_once()
    assert result.exit_code == 1
