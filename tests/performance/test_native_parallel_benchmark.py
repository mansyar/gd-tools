"""Opt-in parallel-versus-sequential execution benchmark.

Run with ``GD_TOOLS_RUN_BENCHMARK=1 pytest -m performance``.  The benchmark
spawns the same fixture suites sequentially and through the parallel worker
pool and asserts that the parallel run finishes first.  Like the
native-versus-legacy benchmark it is excluded from the default suite because
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
            "func test_settles_after_frames() -> void:\n"
            "    for _frame in range(30):\n"
            "        await get_tree().process_frame\n"
            "    assert_true(true)\n",
            encoding="utf-8",
        )
    return project


def _run_test(project: Path, godot_bin: str, extra: list[str]) -> float:
    started = time.perf_counter()
    result = subprocess.run(
        [*_cli_command(), "--quiet", "test", "--no-exit-code", *extra],
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
    return elapsed


def test_parallel_run_completes_faster_than_sequential(
    benchmark_project, godot_bin, record_property
):
    """An M-suite run with N workers finishes faster than sequentially."""
    workers = int(os.environ.get("GD_TOOLS_BENCHMARK_PARALLEL_WORKERS", "4"))
    sequential = _run_test(benchmark_project, godot_bin, [])
    parallel = _run_test(
        benchmark_project, godot_bin, ["--parallel", str(workers)]
    )

    ratio = parallel / sequential if sequential else float("inf")
    record_property("suite_count", SUITE_COUNT)
    record_property("workers", workers)
    record_property("sequential_seconds", sequential)
    record_property("parallel_seconds", parallel)
    record_property("parallel_to_sequential_ratio", ratio)
    print(
        "parallel benchmark:",
        json.dumps(
            {
                "suite_count": SUITE_COUNT,
                "workers": workers,
                "sequential_seconds": sequential,
                "parallel_seconds": parallel,
                "ratio": ratio,
            },
            sort_keys=True,
        ),
    )

    assert parallel < sequential, (
        f"parallel execution ({parallel:.3f}s) was not faster than "
        f"sequential execution ({sequential:.3f}s); ratio={ratio:.2f}"
    )


def test_parallel_speedup_is_statistically_stable(
    benchmark_project, godot_bin, record_property
):
    """The speedup holds across repeated runs (median-of-3 comparison)."""
    iterations = int(os.environ.get("GD_TOOLS_BENCHMARK_ITERATIONS", "3"))
    workers = int(os.environ.get("GD_TOOLS_BENCHMARK_PARALLEL_WORKERS", "4"))
    sequential_times: list[float] = []
    parallel_times: list[float] = []
    for _ in range(iterations):
        sequential_times.append(_run_test(benchmark_project, godot_bin, []))
        parallel_times.append(
            _run_test(
                benchmark_project, godot_bin, ["--parallel", str(workers)]
            )
        )

    sequential_median = statistics.median(sequential_times)
    parallel_median = statistics.median(parallel_times)
    record_property("iterations", iterations)
    record_property("sequential_median_seconds", sequential_median)
    record_property("parallel_median_seconds", parallel_median)
    print(
        "parallel stability benchmark:",
        json.dumps(
            {
                "iterations": iterations,
                "sequential_median_seconds": sequential_median,
                "parallel_median_seconds": parallel_median,
            },
            sort_keys=True,
        ),
    )

    assert parallel_median < sequential_median, (
        f"parallel median ({parallel_median:.3f}s) was not faster than "
        f"sequential median ({sequential_median:.3f}s)"
    )
