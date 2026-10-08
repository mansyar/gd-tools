"""Unit tests for ``--shard k/N`` suite-level selection and the shard banner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.orchestrator import select_shard
from gd_tools.native_test.protocol import NativeSuite, NativeTestResult

pytestmark = pytest.mark.unit


def _suite(name: str) -> NativeSuite:
    return NativeSuite(name=name, path=f"res://test/{name}.gd")


def _suites(count: int) -> list[NativeSuite]:
    return [_suite(f"Suite{i:02d}") for i in range(count)]


def _native_ok() -> MagicMock:
    result = MagicMock()
    return result


# --- select_shard: round-robin over the plan order ---


def test_select_shard_round_robin_over_plan_order():
    """Suite i of the plan order goes to shard (i mod N) + 1."""
    suites = _suites(12)
    selected = select_shard(suites, 2, 3)
    assert [suite.name for suite in selected] == [
        "Suite01",
        "Suite04",
        "Suite07",
        "Suite10",
    ]


def test_select_shard_one_of_one_selects_full_plan():
    """--shard 1/1 is equivalent to no sharding."""
    suites = _suites(5)
    assert select_shard(suites, 1, 1) == suites


def test_select_shard_last_shard():
    """The last shard takes the final residue class (possibly smaller)."""
    suites = _suites(7)
    assert [suite.name for suite in select_shard(suites, 3, 3)] == [
        "Suite02",
        "Suite05",
    ]


def test_select_shard_is_a_pure_stable_filter():
    """Selection never mutates the plan and is stable across calls."""
    suites = _suites(6)
    snapshot = list(suites)
    select_shard(suites, 1, 2)
    assert suites == snapshot
    assert select_shard(suites, 2, 2) == select_shard(suites, 2, 2)


def test_select_shard_empty_plan():
    """An empty plan yields an empty selection."""
    assert select_shard([], 1, 2) == []


# --- command-level shard behavior ---


def _native_result() -> object:
    from gd_tools.native_test.orchestrator import NativeRunResult

    return NativeRunResult(
        run_id="run-1",
        status="passed",
        tests=[
            NativeTestResult(
                suite="ExampleSuite", name="test_ok", status="passed"
            )
        ],
    )


def _patch_command(suites, tmp_path):
    """Patch the command adapter's surroundings for a dry unit run."""
    return (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=MagicMock(path="godot", version="4.7", is_valid=True),
        ),
        patch("gd_tools.native_test.command._import_project"),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=list(suites),
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda root, manifest, **_: MagicMock(
                status="ok", suites=list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=_native_result(),
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    )


def test_run_native_command_shard_banner_and_selection(tmp_path, capsys):
    """The command runs only the shard's suites and reports the context."""
    suites = _suites(3)
    patches = _patch_command(suites, tmp_path)
    with patches[0] as _, patches[1] as _, patches[2] as _, patches[3] as _:
        with (
            patches[4] as _,
            patches[5] as _,
            patches[6] as run,
            patches[7] as _,
            patches[8] as _,
        ):
            run_native_test_command(_config_ns(), shard=(2, 3))

    captured = capsys.readouterr()
    assert "Running shard 2/3 (1 of 3 suites)" in captured.out
    assert [suite.name for suite in run.call_args.args[1]] == ["Suite01"]


def _config_ns():
    from types import SimpleNamespace

    return SimpleNamespace(
        godot=MagicMock(),
        test=SimpleNamespace(
            test_dirs=["test"], timeout_seconds=5.0, retries=0, tags=[]
        ),
        coverage=SimpleNamespace(
            output_dir=".gd-tools/coverage",
            exclude=[],
            test_dirs=["test"],
            format="text",
        ),
    )


def test_run_native_command_shard_one_of_one_runs_full_plan(tmp_path):
    """--shard 1/1 forwards the entire plan to the orchestrator."""
    suites = _suites(4)
    patches = _patch_command(suites, tmp_path)
    with patches[0] as _, patches[1] as _, patches[2] as _, patches[3] as _:
        with (
            patches[4] as _,
            patches[5] as _,
            patches[6] as run,
            patches[7] as _,
            patches[8] as _,
        ):
            run_native_test_command(_config_ns(), shard=(1, 1))

    assert [suite.name for suite in run.call_args.args[1]] == [
        "Suite00",
        "Suite01",
        "Suite02",
        "Suite03",
    ]


def test_run_native_command_empty_shard_runs_nothing(tmp_path, capsys):
    """A shard with no suites (e.g. 3/3 of two suites) runs nothing."""
    suites = _suites(2)
    patches = _patch_command(suites, tmp_path)
    with patches[0] as _, patches[1] as _, patches[2] as _, patches[3] as _:
        with (
            patches[4] as _,
            patches[5] as preflight,
            patches[6] as run,
            patches[7] as _,
            patches[8] as _,
        ):
            result = run_native_test_command(_config_ns(), shard=(3, 3))

    run.assert_not_called()
    preflight.assert_not_called()
    assert result.total == 0
    assert "shard" in capsys.readouterr().out.lower()


def test_shard_applies_after_changed_filtering(tmp_path):
    """Shard selection is a filter of the changed-filtered plan."""
    suites = _suites(4)
    narrowed = suites[:3]
    patches = _patch_command(suites, tmp_path)
    with patches[0] as _, patches[1] as _, patches[2] as _, patches[3] as _:
        with (
            patches[4] as _,
            patches[5] as _,
            patches[6] as run,
            patches[7] as _,
            patches[8] as _,
            patch(
                "gd_tools.native_test.command.collect_changed_files",
                return_value=[Path("changed.gd")],
            ),
            patch(
                "gd_tools.native_test.command._narrow_changed_suites",
                return_value=list(narrowed),
            ),
        ):
            run_native_test_command(_config_ns(), changed=True, shard=(2, 2))

    assert [suite.name for suite in run.call_args.args[1]] == ["Suite01"]
