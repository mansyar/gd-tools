"""Opt-in import-cache warm/cold benchmark.

Run with ``GD_TOOLS_RUN_BENCHMARK=1 pytest tests/performance``.  The
benchmark prepares a native fixture project, runs ``gd-tools test`` once
to populate the import-freshness cache, then measures repeat runs that
must skip the ``godot --headless --import`` step entirely.  Like the
other benchmarks it is excluded from the default suite because
process-spawn-heavy timings are noisy on shared CI workers.
"""

import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.e2e.test_native_runtime import _prepare_project

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("GD_TOOLS_RUN_BENCHMARK") != "1",
        reason="set GD_TOOLS_RUN_BENCHMARK=1 to run the performance benchmark",
    ),
    pytest.mark.usefixtures("godot_bin"),
]

SUITE_COUNT = 6


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


@pytest.fixture()
def benchmark_project(tmp_path, godot_bin) -> Path:
    """Prepare a native fixture project with several passing suites."""
    project = _prepare_project(tmp_path, godot_bin)
    shutil.rmtree(project / "test")
    (project / "test").mkdir()
    for index in range(SUITE_COUNT):
        (project / "test" / f"bench_{index}_suite.gd").write_text(
            "extends GdToolsTest\n\n\n"
            "func test_passes() -> void:\n"
            "    assert_true(true)\n",
            encoding="utf-8",
        )
    return project


def _run_test(project: Path, godot_bin: str) -> tuple[float, str]:
    started = time.perf_counter()
    result = subprocess.run(
        [*_cli_command(), "--verbose", "test", "--no-exit-code"],
        cwd=project,
        env=_environment(godot_bin),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    elapsed = time.perf_counter() - started
    assert result.returncode == 0, result.stdout + result.stderr
    return elapsed, result.stdout


def test_import_cache_speedup(benchmark_project, godot_bin, record_property):
    """A warm run is faster and spawns no import process."""
    cold, _ = _run_test(benchmark_project, godot_bin)

    warm_times: list[float] = []
    cache_hits = 0
    iterations = int(os.environ.get("GD_TOOLS_BENCHMARK_ITERATIONS", "3"))
    for _ in range(iterations):
        elapsed, stdout = _run_test(benchmark_project, godot_bin)
        warm_times.append(elapsed)
        if "Import cache hit" in stdout:
            cache_hits += 1

    warm_median = statistics.median(warm_times)
    ratio = warm_median / cold if cold else float("inf")
    record_property("suite_count", SUITE_COUNT)
    record_property("cold_seconds", cold)
    record_property("warm_median_seconds", warm_median)
    record_property("warm_to_cold_ratio", ratio)
    print(
        "import cache benchmark:",
        json.dumps(
            {
                "suite_count": SUITE_COUNT,
                "cold_seconds": cold,
                "warm_seconds": warm_times,
                "warm_median_seconds": warm_median,
                "warm_to_cold_ratio": ratio,
            },
            sort_keys=True,
        ),
    )

    assert cache_hits == iterations, (
        "not every warm run skipped the import via the cache; hits="
        f"{cache_hits}/{iterations}"
    )
    assert warm_median < cold, (
        f"warm repeat run ({warm_median:.3f}s) was not faster than the "
        f"cold run ({cold:.3f}s); ratio={ratio:.2f}"
    )
