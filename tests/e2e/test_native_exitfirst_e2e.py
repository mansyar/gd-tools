"""E2E tests for ``--exitfirst`` and its composition with the other flags.

These run the full ``gd-tools test`` CLI against a real Godot project and
verify (1) fail-fast early stop with a coherent artifact index and JUnit
report, and (2) the combined ``--changed --shard --exitfirst --parallel
--coverage`` pipeline (spec FR1.1-FR1.7, FR2.4, FR2.6).
"""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

NATIVE_FIXTURE = (
    Path(__file__).parent.parent
    / "fixtures"
    / "projects"
    / "native_test_project"
)
NATIVE_ADDON = (
    Path(__file__).parent.parent.parent
    / "src"
    / "gd_tools"
    / "addons"
    / "gd-tools-test"
)

_PASS_SUITE = """\
extends GdToolsTest

class_name {cls}

func test_ok() -> void:
\tassert_true(true, "always passes")
"""

_FAIL_SUITE = """\
extends GdToolsTest

class_name FFFailSuite

func test_fail() -> void:
\tassert_true(false, "intentional failure for fail-fast")
"""


def _gd_tools_command() -> list[str]:
    exe = Path(sys.executable).parent / "gd-tools.exe"
    if exe.is_file():
        return [str(exe)]
    return [sys.executable, "-m", "gd_tools"]


def _base_env(godot_bin: str) -> dict[str, str]:
    import os

    env = dict(os.environ)
    env["GODOT_BIN"] = godot_bin
    env["GD_TOOLS_NO_UPDATE_CHECK"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _run_cli(
    args: list[str], project: Path, godot_bin: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _gd_tools_command() + args,
        cwd=project,
        env=_base_env(godot_bin),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
    )


def _suite_files() -> dict[str, str]:
    files = {
        "test/ff_suite_01.gd": _PASS_SUITE.format(cls="FFPassSuite01"),
        "test/ff_suite_02.gd": _FAIL_SUITE,
        "test/ff_suite_03.gd": _PASS_SUITE.format(cls="FFPassSuite03"),
        "test/ff_suite_04.gd": _PASS_SUITE.format(cls="FFPassSuite04"),
    }
    return files


def _prepare_project(
    tmp_path: Path, godot_bin: str, files: dict[str, str]
) -> Path:
    import shutil

    project = tmp_path / "ff_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.rmtree(project / "test", ignore_errors=True)
    shutil.copytree(
        NATIVE_ADDON, project / "addons" / "gd-tools-test", dirs_exist_ok=True
    )
    for rel, body in files.items():
        target = project / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    result = subprocess.run(
        _gd_tools_command() + ["init", "--non-interactive"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=180,
        env=_base_env(godot_bin),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return project


def _junit_class_names(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    return [
        case.attrib["classname"]
        for case in root.iter("testcase")
        if "classname" in case.attrib
    ]


def test_exitfirst_stops_early_and_publishes_coherent_artifacts(
    tmp_path: Path, godot_bin: str
) -> None:
    project = _prepare_project(tmp_path, godot_bin, _suite_files())

    result = _run_cli(
        ["test", "--exitfirst", "--parallel", "1", "--junit-xml", "ff.xml"],
        project,
        godot_bin,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        "Stopped early: fail-fast after suite FFFailSuite (2 of 4 suites skipped)"
        in result.stdout
    )

    class_names = set(_junit_class_names(project / "ff.xml"))
    assert class_names == {
        "FFPassSuite01",
        "FFFailSuite",
        "FFPassSuite03",
        "FFPassSuite04",
    }

    artifacts_root = project / ".gd-tools" / "artifacts"
    run_dirs = [d for d in artifacts_root.iterdir() if d.is_dir()]
    assert len(run_dirs) == 1, sorted(p.name for p in artifacts_root.iterdir())
    artifacts = json.loads(
        (run_dirs[0] / "artifacts.json").read_text(encoding="utf-8")
    )
    assert [entry["suite"] for entry in artifacts["suites"]] == [
        "FFPassSuite01",
        "FFFailSuite",
        "FFPassSuite03",
        "FFPassSuite04",
    ]
    assert [entry.get("fail_fast") for entry in artifacts["suites"]] == [
        None,
        None,
        "skipped",
        "skipped",
    ]


def test_combined_changed_shard_exitfirst_parallel_coverage(
    tmp_path: Path, godot_bin: str
) -> None:
    project = _prepare_project(tmp_path, godot_bin, _suite_files())

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=project,
            capture_output=True,
            text=True,
            check=True,
        )

    _git("init")
    _git("-c", "user.email=e@example.com", "-c", "user.name=t", "add", "-A")
    _git(
        "-c",
        "user.email=e@example.com",
        "-c",
        "user.name=t",
        "commit",
        "-m",
        "init",
    )
    suite03 = project / "test" / "ff_suite_03.gd"
    suite03.write_text(
        suite03.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8"
    )

    result = _run_cli(
        [
            "test",
            "--changed",
            "--shard",
            "1/1",
            "--exitfirst",
            "--parallel",
            "2",
            "--coverage",
            "--junit-xml",
            "comb.xml",
        ],
        project,
        godot_bin,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "--changed: 1 of 4 suites selected" in result.stdout
    assert "Running shard 1/1 (1 of 1 suites)." in result.stdout
    assert set(_junit_class_names(project / "comb.xml")) == {"FFPassSuite03"}
    assert (project / ".gd-tools" / "coverage" / "coverage.json").is_file()
