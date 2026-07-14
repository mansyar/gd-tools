"""E2E tests for autoload-based coverage instrumentation.

Tests the core bug fix: when an autoload's _ready() creates instances of
other scripts, those scripts still get coverage instrumentation because
_GDTCoverage._ready() runs first (as the first autoload) and instruments
all files before any instances are created.

The fixture project (tests/fixtures/autoload_coverage/) has:
  - GameState autoload — instantiates ChimeraData in _ready()
  - ChimeraData — non-autoload script instantiated by the autoload
  - GUT tests — exercise ChimeraData methods

Tests that require Godot are automatically skipped when the binary is not
on PATH.

All tests are marked @pytest.mark.e2e.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gd_tools.init import install_coverage_addon, register_coverage_autoload

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SPIKE_DIR = Path(__file__).parent.parent.parent / "spike"

skip_if_no_godot = pytest.mark.skipif(
    not (os.environ.get("GODOT_BIN") or shutil.which("godot")),
    reason="Godot binary not found (set GODOT_BIN or add to PATH)",
)


def _gd_tools_bin() -> str:
    """Return the path to the gd-tools executable."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        path = bin_dir / name
        if path.exists():
            return str(path)
    found = shutil.which("gd-tools")
    if found:
        return found
    return str(bin_dir / "gd-tools")


def _setup_autoload_coverage_project(tmp_path: Path) -> Path:
    """Set up the autoload_coverage fixture project with GUT + coverage addon.

    Copies the fixture project (which has GameState as an autoload that
    instantiates ChimeraData), installs GUT and the coverage addon, and
    registers _GDTCoverage as the first autoload (prepending it before
    GameState via register_coverage_autoload()).
    """
    src = FIXTURES_DIR / "autoload_coverage"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    shutil.copytree(
        SPIKE_DIR / "addons" / "gut",
        tmp_path / "addons" / "gut",
        dirs_exist_ok=True,
    )
    install_coverage_addon(tmp_path)
    register_coverage_autoload(tmp_path)
    return tmp_path


def _run_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run gd-tools CLI with *args* in *cwd*."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [_gd_tools_bin(), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )


def _find_file_id(plan: dict, path_fragment: str) -> int | None:
    """Find the file_id for a plan entry matching *path_fragment*."""
    for f in plan["files"]:
        if path_fragment in f["path"]:
            return f["file_id"]
    return None


# ---------------------------------------------------------------------------
# Autoload-instantiated script gets coverage (the core bug fix)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_if_no_godot
def test_autoload_instantiated_script_gets_coverage(tmp_path):
    """Scripts instantiated by autoloads show non-zero coverage.

    chimera_data.gd is instantiated by GameState._ready() (an autoload).
    Godot creates all autoload instances before calling any _ready(), so
    coverage.gd uses reload(true) (keep_state) to instrument scripts that
    already have active instances.
    """
    project = _setup_autoload_coverage_project(tmp_path)
    result = _run_cli(
        ["test", "--coverage", "--suite", "res://tests/test_chimera_data.gd"],
        cwd=project,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    coverage_dir = project / ".gd-tools" / "coverage"
    plan = json.loads((coverage_dir / "plan.json").read_text())
    data = json.loads((coverage_dir / "coverage.json").read_text())

    chimera_file_id = _find_file_id(plan, "chimera_data.gd")
    assert chimera_file_id is not None, "chimera_data.gd not in plan"

    # Find chimera_data.gd in coverage output
    chimera_entry = None
    for f in data["files"]:
        if f["file_id"] == chimera_file_id:
            chimera_entry = f
            break

    assert chimera_entry is not None, (
        "chimera_data.gd not in coverage output — "
        "instrumentation may have failed (reload(true) did not apply)"
    )

    total_hits = sum(int(v) for v in chimera_entry["hits"].values())
    assert total_hits > 0, (
        f"chimera_data.gd has 0 coverage hits. "
        f"Hits: {chimera_entry['hits']}"
    )


# ---------------------------------------------------------------------------
# Autoload init code is NOT recorded as coverage
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_if_no_godot
def test_autoload_init_code_not_recorded(tmp_path):
    """Autoload _ready() code is NOT recorded as coverage.

    The tracker activates via pre_run_hook (after autoloads init), so
    autoload initialization code (GameState._ready()) should have 0 hits
    even though it was executed during autoload init.
    """
    project = _setup_autoload_coverage_project(tmp_path)
    result = _run_cli(
        ["test", "--coverage", "--suite", "res://tests/test_chimera_data.gd"],
        cwd=project,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    coverage_dir = project / ".gd-tools" / "coverage"
    plan = json.loads((coverage_dir / "plan.json").read_text())
    data = json.loads((coverage_dir / "coverage.json").read_text())

    game_state_file_id = _find_file_id(plan, "game_state.gd")
    assert game_state_file_id is not None, "game_state.gd not in plan"

    # game_state.gd should NOT appear in coverage output (no hits recorded
    # because tracker was inactive during autoload init).
    game_state_entry = None
    for f in data["files"]:
        if f["file_id"] == game_state_file_id:
            game_state_entry = f
            break

    if game_state_entry is not None:
        total_hits = sum(int(v) for v in game_state_entry["hits"].values())
        assert total_hits == 0, (
            f"game_state.gd should have 0 hits (autoload init runs before "
            f"tracker activation). Got: {game_state_entry['hits']}"
        )


# ---------------------------------------------------------------------------
# Regression: overall coverage system still works
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@skip_if_no_godot
def test_coverage_system_regression(tmp_path):
    """Coverage system produces valid output on the autoload fixture.

    Regression check: plan includes both autoload and non-autoload scripts,
    tests pass, and coverage.json is generated with correct structure.
    """
    project = _setup_autoload_coverage_project(tmp_path)
    result = _run_cli(
        ["test", "--coverage", "--suite", "res://tests/test_chimera_data.gd"],
        cwd=project,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    coverage_dir = project / ".gd-tools" / "coverage"
    assert (coverage_dir / "plan.json").exists()
    assert (coverage_dir / "coverage.json").exists()

    plan = json.loads((coverage_dir / "plan.json").read_text())
    data = json.loads((coverage_dir / "coverage.json").read_text())

    # Plan includes both autoload and non-autoload scripts
    plan_paths = [f["path"] for f in plan["files"]]
    assert any(
        "game_state.gd" in p for p in plan_paths
    ), "autoload script (game_state.gd) should be in plan"
    assert any(
        "chimera_data.gd" in p for p in plan_paths
    ), "non-autoload script (chimera_data.gd) should be in plan"

    # Coverage output has valid structure
    assert data["version"] == 1
    assert "generated_at" in data
    assert "files" in data
    assert isinstance(data["files"], list)
