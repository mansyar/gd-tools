"""Opt-in native-versus-legacy runtime benchmark.

Run with ``GD_TOOLS_RUN_BENCHMARK=1 pytest -m performance``.  The benchmark
uses the same machine, Godot binary, headless mode, and small-suite shape for
both runtimes.  It is intentionally excluded from the default suite because
startup-heavy benchmarks are noisy on shared CI workers.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from statistics import median

import pytest

from conftest import find_godot_binary
from gd_tools.init import install_coverage_addon

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("GD_TOOLS_RUN_BENCHMARK") != "1",
        reason="set GD_TOOLS_RUN_BENCHMARK=1 to run the performance benchmark",
    ),
    pytest.mark.usefixtures("godot_bin", "compatible_gut"),
]

FIXTURES = Path(__file__).parent.parent / "fixtures"
NATIVE_FIXTURE = FIXTURES / "projects" / "native_test_project"
LEGACY_FIXTURE = FIXTURES / "projects" / "sample_project"
GUT_ADDON = Path(__file__).parent.parent.parent / "spike" / "addons" / "gut"


def _cli_command() -> list[str]:
    bin_dir = Path(sys.executable).parent
    for name in ("gd-tools.exe", "gd-tools"):
        candidate = bin_dir / name
        if candidate.exists():
            return [str(candidate)]
    return [sys.executable, "-m", "gd_tools"]


def _environment(godot_bin: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GODOT_BIN": godot_bin,
            "GD_TOOLS_NO_UPDATE_CHECK": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    return env


def _native_project(tmp_path: Path) -> Path:
    project = tmp_path / "native"
    shutil.copytree(NATIVE_FIXTURE, project)
    result = subprocess.run(
        [*_cli_command(), "init", "--non-interactive"],
        cwd=project,
        env=_environment(find_godot_binary() or ""),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return project


def _legacy_project(tmp_path: Path) -> Path:
    project = tmp_path / "legacy"
    shutil.copytree(LEGACY_FIXTURE, project)
    shutil.copytree(GUT_ADDON, project / "addons" / "gut")
    install_coverage_addon(project)
    (project / ".gutconfig.json").write_text(
        json.dumps(
            {
                "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
                "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd",
            }
        ),
        encoding="utf-8",
    )
    (project / "gd-tools.toml").write_text(
        '[test]\nruntime = "gut"\n', encoding="utf-8"
    )
    return project


def _measure(
    args: list[str], project: Path, godot_bin: str
) -> tuple[float, float, int]:
    """Return (time to first output, total wall time, exit code)."""
    started = time.perf_counter()
    process = subprocess.Popen(
        [*_cli_command(), *args],
        cwd=project,
        env=_environment(godot_bin),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    first_line = process.stdout.readline()
    startup = time.perf_counter() - started
    output = [first_line]
    output.extend(process.stdout)
    returncode = process.wait()
    total = time.perf_counter() - started
    return startup, total, returncode


def test_native_runtime_is_within_two_times_legacy_small_suite(
    tmp_path, record_property
):
    """The native runtime stays within the approved 2x regression budget."""
    godot_bin = find_godot_binary()
    assert godot_bin is not None
    native = _native_project(tmp_path)
    legacy = _legacy_project(tmp_path)

    iterations = int(os.environ.get("GD_TOOLS_BENCHMARK_ITERATIONS", "2"))
    native_totals: list[float] = []
    legacy_totals: list[float] = []
    native_startups: list[float] = []
    legacy_startups: list[float] = []

    for _ in range(iterations):
        native_startup, native_total, native_code = _measure(
            [
                "--quiet",
                "test",
                "--suite",
                "NativeFixtureSuite",
                "--no-exit-code",
            ],
            native,
            godot_bin,
        )
        legacy_startup, legacy_total, legacy_code = _measure(
            [
                "--quiet",
                "test",
                "--runtime",
                "gut",
                "--suite",
                "res://test/test_calculator.gd",
                "--no-exit-code",
            ],
            legacy,
            godot_bin,
        )
        assert native_code == 0
        assert legacy_code == 0
        native_startups.append(native_startup)
        native_totals.append(native_total)
        legacy_startups.append(legacy_startup)
        legacy_totals.append(legacy_total)

    native_median = median(native_totals)
    legacy_median = median(legacy_totals)
    ratio = native_median / legacy_median if legacy_median else float("inf")
    record_property("native_startup_seconds", median(native_startups))
    record_property("legacy_startup_seconds", median(legacy_startups))
    record_property("native_total_seconds", native_median)
    record_property("legacy_total_seconds", legacy_median)
    record_property("native_to_legacy_ratio", ratio)
    print(
        "native benchmark:",
        json.dumps(
            {
                "iterations": iterations,
                "native_startup_seconds": median(native_startups),
                "legacy_startup_seconds": median(legacy_startups),
                "native_total_seconds": native_median,
                "legacy_total_seconds": legacy_median,
                "ratio": ratio,
            },
            sort_keys=True,
        ),
    )

    assert ratio <= 2.0, (
        "native runtime exceeded the 2x small-suite regression budget: "
        f"native={native_median:.3f}s legacy={legacy_median:.3f}s ratio={ratio:.2f}"
    )
