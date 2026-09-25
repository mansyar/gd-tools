"""Public CLI E2E coverage for the native test runtime."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import find_godot_binary

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)

skip_if_no_godot = pytest.mark.skipif(
    find_godot_binary() is None,
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _setup_project(tmp_path: Path) -> Path:
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    return project


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return subprocess.run(
        [*_gd_tools_command(), *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )


@skip_if_no_godot
def test_native_cli_init_installs_native_runtime_without_gut(
    tmp_path, godot_bin
):
    """Native init deploys the addon and leaves GUT opt-in."""
    project = _setup_project(tmp_path)

    result = _run_cli(["init", "--non-interactive"], project, godot_bin)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / "addons" / "gd-tools-test" / "gd_tools_test.gd").is_file()
    assert not (project / "addons" / "gut").exists()
    assert not (project / ".gutconfig.json").exists()
    assert 'runtime = "native"' in (project / "gd-tools.toml").read_text(
        encoding="utf-8"
    )


@skip_if_no_godot
def test_native_cli_defaults_to_native_and_writes_junit(tmp_path, godot_bin):
    """The default test command runs native suites and emits JUnit XML."""
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )

    result = _run_cli(
        [
            "--quiet",
            "test",
            "--suite",
            "NativeFixtureSuite",
            "--junit-xml",
            ".gd-tools/native-results.xml",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    junit = project / ".gd-tools" / "native-results.xml"
    assert junit.is_file()
    content = junit.read_text(encoding="utf-8")
    assert "test_pass" in content
    assert "test_async" in content


@skip_if_no_godot
def test_native_cli_preserves_failure_and_no_exit_exit_codes(
    tmp_path, godot_bin
):
    """Native assertion failures map to 1 unless suppression is requested."""
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )

    failed = _run_cli(
        ["--quiet", "test", "--suite", "NativeLifecycleSuite"],
        project,
        godot_bin,
    )
    suppressed = _run_cli(
        [
            "--quiet",
            "test",
            "--suite",
            "NativeLifecycleSuite",
            "--no-exit-code",
        ],
        project,
        godot_bin,
    )

    assert failed.returncode == 1, failed.stdout + failed.stderr
    assert suppressed.returncode == 0, suppressed.stdout + suppressed.stderr


@skip_if_no_godot
def test_native_cli_empty_selection_gives_legacy_guidance(tmp_path, godot_bin):
    """A missing native selection explains how to use the GUT fallback."""
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )

    result = _run_cli(
        ["--quiet", "test", "--suite", "DoesNotExist"],
        project,
        godot_bin,
    )

    assert result.returncode == 2
    assert "--runtime gut" in result.stdout + result.stderr


@skip_if_no_godot
@pytest.mark.slow
def test_native_cli_writes_coverage_artifacts(tmp_path, godot_bin):
    """The public native command produces plan, data, and report artifacts."""
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )

    result = _run_cli(
        [
            "--quiet",
            "test",
            "--coverage",
            "--suite",
            "NativeCoverageSuite",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "plan.json").is_file()
    assert (coverage_dir / "coverage.json").is_file()


@skip_if_no_godot
def test_native_cli_explicit_gut_runtime_remains_selectable(
    tmp_path, godot_bin
):
    """The legacy selector remains available even for a native project."""
    project = _setup_project(tmp_path)
    assert (
        _run_cli(["init", "--non-interactive"], project, godot_bin).returncode
        == 0
    )

    result = _run_cli(
        ["--quiet", "test", "--runtime", "gut"],
        project,
        godot_bin,
    )

    assert result.returncode == 2
    assert "GUT is not installed" in result.stdout + result.stderr
