"""Unit tests for the GUT bridge deprecation notice."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.preflight import NativePreflightResult
from gd_tools.native_test.protocol import (
    NativeRunResult,
    NativeSuite,
    RuntimeMode,
)

pytestmark = pytest.mark.unit


def _config():
    return SimpleNamespace(
        godot=SimpleNamespace(),
        test=SimpleNamespace(
            test_dirs=["test"],
            timeout_seconds=5.0,
            retries=0,
            tags=[],
        ),
        coverage=SimpleNamespace(
            output_dir=".gd-tools/coverage",
            exclude=[],
            test_dirs=["test"],
            format="text",
        ),
    )


def _native_result():
    return NativeRunResult(
        run_id="run-1",
        status="passed",
        tests=[],
        coverage_data_path=None,
        artifact_index_path=None,
        engine_warnings=[],
        diagnostics={},
        stdout="",
        stderr="",
    )


def _run_command(suites, print_info, tmp_path):
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.find_godot",
            return_value=SimpleNamespace(
                path="godot", version="4.7", is_valid=True
            ),
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
            return_value=NativePreflightResult(
                status="ok", suites=list(suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=_native_result(),
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.output.print_info", print_info),
    ):
        run_native_test_command(_config())


def test_gut_bridge_suite_prints_deprecation_notice_once(tmp_path):
    """A GUT-style suite announces deprecation and the removal release once."""
    print_info = MagicMock()
    suites = [
        NativeSuite(
            name="LegacySuite",
            path="res://test/legacy_test.gd",
            runtime=RuntimeMode.GUT,
        )
    ]
    _run_command(suites, print_info, tmp_path)

    bridge_calls = [
        call
        for call in print_info.call_args_list
        if "bridge" in str(call.args).lower()
    ]
    assert len(bridge_calls) == 1
    message = bridge_calls[0].args[0]
    assert "deprecated" in message.lower()
    assert "v0.6.0" in message


def test_native_suites_do_not_announce_bridge(tmp_path):
    """Native-only runs print no bridge/deprecation notice."""
    print_info = MagicMock()
    suites = [NativeSuite(name="NativeSuite", path="res://test/native_test.gd")]
    _run_command(suites, print_info, tmp_path)

    for call in print_info.call_args_list:
        assert "bridge" not in str(call.args).lower()
        assert "deprecated" not in str(call.args).lower()
