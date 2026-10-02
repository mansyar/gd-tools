"""Removal-contract tests for Phase 2 of the GUT bridge removal.

Covers the v0.6.0 behavior agreed in the track spec:

- ``gd-tools doctor`` reports legacy GUT artifacts informationally and
  advises ``gd-tools migrate`` (no bridge-health checks remain).
- ``runtime = "gut"`` in ``gd-tools.toml`` is a hard config error (exit 2)
  with migration guidance.
- ``gd-tools migrate`` keeps report/translate/apply behavior and its
  guidance text is v0.6.0-aware (the bridge no longer exists).
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from gd_tools.cli import cli
from gd_tools.config import TestConfig
from gd_tools.doctor import run_doctor
from gd_tools.godot import GodotInfo
from gd_tools.migration.reporter import render_migration_report
from gd_tools.migration.scan import ConstructHit, MigrationReport, SuiteReport

pytestmark = pytest.mark.unit

REMOVAL_MESSAGE = "removed in v0.6.0"
MIGRATE_POINTER = "gd-tools migrate"


# --- Doctor: migration advisor (FR-5) ---


def _make_project(tmp_path: Path, legacy: bool = True) -> Path:
    """Create a minimal Godot project, optionally with legacy GUT artifacts."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    (tmp_path / "gd-tools.toml").write_text("")
    if legacy:
        gut_dir = tmp_path / "addons" / "gut"
        gut_dir.mkdir(parents=True)
        (gut_dir / "gut.gd").write_text("extends Node\n")
        (tmp_path / ".gutconfig.json").write_text('{"dirs": ["res://test/"]}')
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "legacy_suite.gd").write_text(
            "extends GutTest\n\n\ntest_something() -> void:\n\tpass\n"
        )
    return tmp_path


def _run_doctor_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    godot_info = GodotInfo(path="/fake/godot", version="4.5.1", is_valid=True)
    with (
        patch("gd_tools.doctor.find_godot", return_value=godot_info),
        patch("subprocess.run"),
    ):
        return run_doctor()


def test_doctor_reports_legacy_gut_artifacts_informationally(
    tmp_path, monkeypatch
):
    """Legacy artifacts produce a passing, non-blocking advisory check."""
    _make_project(tmp_path)
    result = _run_doctor_in(tmp_path, monkeypatch)

    legacy = [c for c in result.checks if c.name == "Legacy GUT"]
    assert len(legacy) == 1
    check = legacy[0]
    assert check.passed
    assert "addons/gut" in check.message
    assert ".gutconfig.json" in check.message
    assert "legacy_suite.gd" in check.message
    assert MIGRATE_POINTER in check.fix_hint or MIGRATE_POINTER in check.message


def test_doctor_legacy_check_clean_when_no_artifacts(tmp_path, monkeypatch):
    """A project without GUT artifacts reports a neutral pass."""
    _make_project(tmp_path, legacy=False)
    result = _run_doctor_in(tmp_path, monkeypatch)

    legacy = [c for c in result.checks if c.name == "Legacy GUT"]
    assert len(legacy) == 1
    assert legacy[0].passed


def test_doctor_has_no_bridge_health_checks(tmp_path, monkeypatch):
    """The bridge-health check names are gone from the doctor report."""
    _make_project(tmp_path, legacy=False)
    result = _run_doctor_in(tmp_path, monkeypatch)

    names = {c.name for c in result.checks}
    for gone in ("GUT Installed", "GUT Version", "GUT Suites", "GUT Config"):
        assert gone not in names
    assert len(result.checks) == 9


def test_doctor_autoload_hint_does_not_mention_with_gut(tmp_path):
    """The autoload fix hint points at plain init (no --with-gut)."""
    from gd_tools.doctor import check_autoload

    result = check_autoload(tmp_path, required=True)
    assert "--with-gut" not in result.fix_hint
    assert "`gd-tools init`" in result.fix_hint


# --- Config: hard error on runtime = "gut" (FR-3) ---


def test_config_runtime_gut_rejected_with_guidance():
    """TestConfig rejects runtime='gut' with the v0.6.0 removal guidance."""
    with pytest.raises(ValidationError) as excinfo:
        TestConfig(runtime="gut")
    message = str(excinfo.value)
    assert REMOVAL_MESSAGE in message
    assert MIGRATE_POINTER in message


def test_config_validate_runtime_gut_exits_2(tmp_path, monkeypatch):
    """`config validate` hard-errors (exit 2) on runtime = "gut"."""
    (tmp_path / "project.godot").write_text("config_version=5\n")
    (tmp_path / "gd-tools.toml").write_text(
        '[test]\nruntime = "gut"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(cli, ["config", "validate"])
    assert result.exit_code == 2
    assert REMOVAL_MESSAGE in result.output
    assert MIGRATE_POINTER in result.output


# --- Migrate: v0.6.0-aware guidance (FR-6) ---


def _report() -> MigrationReport:
    """A report with one clean and one dirty legacy suite."""
    dirty = SuiteReport(
        path="res://test/dirty_suite.gd",
        test_count=2,
        unsupported=(ConstructHit(name="assert_setget", line=4),),
        aliases=(ConstructHit(name="yield_before_seconds", line=9),),
    )
    clean = SuiteReport(path="res://test/clean_suite.gd", test_count=1)
    return MigrationReport(suites=(dirty, clean))


def test_migration_report_is_v060_aware():
    """The report no longer claims aliases work; it names v0.6.0 removal."""
    output = render_migration_report(_report())
    assert REMOVAL_MESSAGE in output
    assert MIGRATE_POINTER in output
    assert "works now" not in output
    assert "the bridge cannot run these" not in output
