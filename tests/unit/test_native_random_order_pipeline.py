"""Unit tests for random-order wiring in the native test command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.ordering import apply_random_order
from gd_tools.native_test.orchestrator import NativeRunResult
from gd_tools.native_test.protocol import (
    NativeSuite,
    NativeTest,
    NativeTestResult,
)

pytestmark = pytest.mark.unit


def _suite(name, methods=("test_a", "test_b", "test_c")):
    """Build a suite with the given method names."""
    return NativeSuite(
        name=name,
        path=f"res://test/{name}.gd",
        tests=[NativeTest(name=method) for method in methods],
    )


def _suites(count=5, methods=("test_a", "test_b", "test_c")):
    """Build ``count`` suites, each with the given methods."""
    return [_suite(f"Suite{i:02d}", methods) for i in range(count)]


def _native_result():
    """A minimal successful native run result."""
    return NativeRunResult(
        run_id="run-1",
        status="passed",
        tests=[
            NativeTestResult(suite="Suite00", name="test_ok", status="passed")
        ],
    )


def _config_ns():
    """A config namespace sufficient for the native command."""
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


def _patch_command(suites, tmp_path):
    """Patch the command adapter's surroundings for a dry unit run.

    Returns the nine patchers positionally: find_project_root, find_godot,
    _import_project, discover_native_suites, _prepare_coverage,
    run_preflight_cached, run_native_tests, _generate_native_report,
    format_test_results.
    """
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


def _run(suites, tmp_path, **kwargs):
    """Run the command with the surroundings patched.

    Returns ``(forwarded_suites, preflight_manifest, verbose_messages)``.
    """
    patches = _patch_command(suites, tmp_path)
    with (
        patches[0] as _,
        patches[1] as _,
        patches[2] as _,
        patches[3] as _,
        patches[4] as _,
        patches[5] as preflight,
        patches[6] as run,
        patches[7] as _,
        patches[8] as _,
        patch("gd_tools.native_test.command.output.print_verbose") as verbose,
    ):
        run_native_test_command(_config_ns(), **kwargs)

    return (
        run.call_args.args[1],
        preflight.call_args.args[1],
        [call.args[0] for call in verbose.call_args_list],
    )


# --- ordering is applied, and applied at the right point ---


def test_random_order_shuffles_the_dispatched_suites(tmp_path):
    """--random-order hands the orchestrator a shuffled suite order."""
    suites = _suites(5)

    forwarded, _, _ = _run(suites, tmp_path, random_order=True, seed=42)

    expected = apply_random_order(suites, 42).suites
    assert [s.name for s in forwarded] == [s.name for s in expected]
    assert [s.name for s in forwarded] != [s.name for s in suites]


def test_random_order_is_applied_after_preflight(tmp_path):
    """Preflight still sees the deterministic discovery order (FR-9)."""
    suites = _suites(5)

    _, manifest, _ = _run(suites, tmp_path, random_order=True, seed=42)

    assert [s.name for s in manifest.suites] == [s.name for s in suites]


def test_random_order_shuffles_methods_in_the_dispatched_manifest(tmp_path):
    """The manifest sent to Godot carries the shuffled method order (AC-4)."""
    suites = _suites(5)

    forwarded, _, _ = _run(suites, tmp_path, random_order=True, seed=42)

    expected = apply_random_order(suites, 42).suites
    for forwarded_suite, expected_suite in zip(forwarded, expected):
        assert forwarded_suite.name == expected_suite.name
        assert [t.name for t in forwarded_suite.tests] == [
            t.name for t in expected_suite.tests
        ]


def test_disabled_random_order_is_unchanged(tmp_path):
    """Without the flag the dispatched order is the discovery order."""
    suites = _suites(5)

    forwarded, _, verbose = _run(suites, tmp_path)

    assert [s.name for s in forwarded] == [s.name for s in suites]
    for forwarded_suite, suite in zip(forwarded, suites):
        assert [t.name for t in forwarded_suite.tests] == [
            t.name for t in suite.tests
        ]
    # Verbose output is shared with the import/preflight cache diagnostics,
    # so the invariant is "no ordering listing", not "no verbose output".
    assert not any("Random order" in message for message in verbose)


# --- reporting ---


def test_seed_is_reported_for_replay(tmp_path, capsys):
    """The run reports the seed it used and how to replay it (FR-13)."""
    _run(_suites(5), tmp_path, random_order=True, seed=42)

    out = capsys.readouterr().out
    assert "Random order: seed 42" in out
    assert "--seed 42" in out


def test_no_seed_line_when_random_order_is_disabled(tmp_path, capsys):
    """An unrandomized run reports no seed line (NFR-1)."""
    _run(_suites(5), tmp_path)

    assert "Random order" not in capsys.readouterr().out


def test_verbose_lists_the_resolved_order(tmp_path):
    """Under --verbose the resolved execution order is listed (FR-15)."""
    suites = _suites(3)

    _, _, verbose = _run(suites, tmp_path, random_order=True, seed=42)

    assert any("Random order" in message for message in verbose)
    listing = " ".join(verbose)
    for suite in suites:
        assert suite.name in listing
