"""End-to-end tests for ``gd-tools test --changed`` on a real project.

Exercises the CLI as a subprocess against a real git-backed Godot project
with a real Godot binary, following the acceptance sequence:

1. a clean tree reports "no changes detected" and exits 0,
2. editing a source file runs only the mapped suite,
3. modifying ``project.godot`` falls back to the full suite with a notice,
4. a committed change on a branch is selected via ``--base main``.
"""

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.usefixtures("godot_bin"),
]

_RUN_TIMEOUT = 300.0


def _gd_tools_command() -> list[str]:
    """Use the installed CLI entry point when available."""
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _write_project(root: Path) -> None:
    """Create a minimal Godot project with two native suites."""
    (root / "src").mkdir()
    (root / "test").mkdir()
    (root / "tests").mkdir()
    (root / "project.godot").write_text(
        'config_version=5\n\n[application]\nconfig/name="changed_e2e"\n',
        encoding="utf-8",
    )
    (root / ".gitignore").write_text(".godot/\n.gd-tools/\n", encoding="utf-8")
    (root / "src" / "enemy.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "src" / "player.gd").write_text("extends Node\n", encoding="utf-8")
    (root / "tests" / "test_enemy.gd").write_text(
        "extends GdToolsTest\n"
        "\n"
        "\n"
        "class_name EnemySuite\n"
        "\n"
        "\n"
        "func test_ok() -> void:\n"
        "\tassert_eq(1, 1)\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_player.gd").write_text(
        "extends GdToolsTest\n"
        "\n"
        "\n"
        "class_name PlayerSuite\n"
        "\n"
        "\n"
        "func test_ok() -> void:\n"
        "\tassert_eq(2, 2)\n",
        encoding="utf-8",
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )


def _run(
    project: Path, godot_bin: str, *args: str
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
        timeout=_RUN_TIMEOUT,
    )


def _junit_test_count(junit_path: Path) -> int:
    root = ET.parse(junit_path).getroot()
    return sum(1 for _ in root.iter("testcase"))


@pytest.mark.e2e_smoke
def test_changed_selection_end_to_end(tmp_path, godot_bin):
    """--changed selects mapped suites, falls back, and honors --base."""
    project = tmp_path / "changed_project"
    project.mkdir()
    _write_project(project)
    _git(project, "init", "-b", "main")
    _git(project, "config", "user.email", "e2e@example.com")
    _git(project, "config", "user.name", "gd-tools e2e")
    init = _run(project, godot_bin, "init", "--non-interactive")
    assert init.returncode == 0, init.stdout + init.stderr
    # Warm up: one full run makes Godot generate .uid files and .godot/ so
    # the baseline commit captures them (they are product noise otherwise).
    warmup = _run(project, godot_bin, "test")
    assert warmup.returncode == 0, warmup.stdout + warmup.stderr
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "baseline")

    # 1. A clean tree detects no changes: exit 0, no Godot processes.
    clean = _run(project, godot_bin, "test", "--changed")
    assert clean.returncode == 0, clean.stdout + clean.stderr
    assert "no changes detected" in clean.stdout

    # 2. Editing a source file runs only the mapped suite.
    (project / "src" / "enemy.gd").write_text(
        "extends Node\n# touched\n", encoding="utf-8"
    )
    mapped_junit = tmp_path / "junit-mapped.xml"
    mapped = _run(
        project,
        godot_bin,
        "test",
        "--changed",
        "--junit-xml",
        str(mapped_junit),
    )
    assert mapped.returncode == 0, mapped.stdout + mapped.stderr
    assert "--changed: 1 of 2 suites selected" in mapped.stdout
    assert _junit_test_count(mapped_junit) == 1

    # 3. A project-level change maps to nothing: full-suite fallback.
    godot_project = project / "project.godot"
    original = godot_project.read_text(encoding="utf-8")
    godot_project.write_text(original + "\n# touched\n", encoding="utf-8")
    fallback_junit = tmp_path / "junit-fallback.xml"
    fallback = _run(
        project,
        godot_bin,
        "test",
        "--changed",
        "--junit-xml",
        str(fallback_junit),
    )
    assert fallback.returncode == 0, fallback.stdout + fallback.stderr
    assert "No suite mapped for 'project.godot'" in fallback.stdout
    assert _junit_test_count(fallback_junit) == 2
    godot_project.write_text(original, encoding="utf-8")

    # 4. A committed change on a branch is selected via --base main.
    _git(project, "checkout", "--", "src/enemy.gd")
    _git(project, "checkout", "-b", "feature")
    (project / "src" / "player.gd").write_text(
        "extends Node\n# touched\n", encoding="utf-8"
    )
    _git(project, "add", "-A")
    _git(project, "commit", "-m", "touch player")
    base_junit = tmp_path / "junit-base.xml"
    base_run = _run(
        project,
        godot_bin,
        "test",
        "--changed",
        "--base",
        "main",
        "--junit-xml",
        str(base_junit),
    )
    assert base_run.returncode == 0, base_run.stdout + base_run.stderr
    assert "--changed: 1 of 2 suites selected (base 'main')" in base_run.stdout
    assert _junit_test_count(base_junit) == 1

    # The committed change no longer appears in the working tree.
    committed = _run(project, godot_bin, "test", "--changed")
    assert committed.returncode == 0, committed.stdout + committed.stderr
    assert "no changes detected" in committed.stdout
