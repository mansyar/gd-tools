"""Unit tests for the native test CLI adapter."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gd_tools.errors import (
    ConfigError,
    CoverageThresholdError,
    GdToolsError,
    GitChangeError,
    TestFailureError,
)
from gd_tools.native_test.command import (
    _generate_native_report,
    _test_directories,
    run_native_test_command,
)
from gd_tools.native_test.preflight import NativePreflightError
from gd_tools.native_test.protocol import (
    NativeExecutionMode,
    NativePreflightResult,
    NativeRunResult,
    NativeSuite,
    NativeSuiteIntegration,
    NativeTest,
    NativeTestResult,
    RuntimeMode,
)
from gd_tools.test_runner import TestResult

pytestmark = pytest.mark.unit


def _native_result(
    status: str = "passed",
    tests: list[NativeTestResult] | None = None,
) -> NativeRunResult:
    return NativeRunResult(
        run_id="run-1",
        status=status,
        tests=(
            tests
            if tests is not None
            else [
                NativeTestResult(
                    suite="ExampleSuite", name="test_ok", status="passed"
                )
            ]
        ),
    )


def _config() -> SimpleNamespace:
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


def _preflight(suites: list[NativeSuite]) -> NativePreflightResult:
    return NativePreflightResult(status="ok", suites=suites)


def test_test_directories_preserves_explicit_file_selector(tmp_path):
    """The adapter keeps an explicit file path exact for discovery."""
    selected = tmp_path / "test" / "selected.gd"
    selected.parent.mkdir(parents=True)
    selected.touch()

    assert _test_directories(tmp_path, [str(selected)], _config()) == [
        str(selected)
    ]


def test_to_test_result_normalizes_statuses_and_writes_junit(tmp_path):
    """Native statuses map to the existing TestResult contract and JUnit XML."""
    from gd_tools.native_test.command import _to_test_result

    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite",
                name="test_pass",
                status="passed",
                duration_seconds=0.1,
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="test_fail",
                status="failed",
                duration_seconds=0.2,
                message="expected true",
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="test_skip",
                status="skipped",
                duration_seconds=0.0,
            ),
        ],
    )

    result = _to_test_result(native, tmp_path, str(tmp_path / "results.xml"))

    assert isinstance(result, TestResult)
    assert (result.total, result.passed, result.failed, result.skipped) == (
        3,
        1,
        1,
        1,
    )
    assert [detail.status for detail in result.test_details] == [
        "pass",
        "fail",
        "skip",
    ]
    root = ET.parse(tmp_path / "results.xml").getroot()
    assert root.find("testsuite").attrib["tests"] == "3"
    assert root.find("testsuite/testcase/failure") is not None
    assert root.find("testsuite/testcase[3]/skipped") is not None


def test_run_native_command_propagates_filters_and_timeout(tmp_path):
    """The adapter passes discovery filters and the process timeout through."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result()
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
            return_value=[suite],
        ) as discover,
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        result = run_native_test_command(
            _config(),
            suite="ExampleSuite",
            test_name="test_ok",
            tags=["smoke"],
            test_timeout=1.5,
            timeout=42,
        )

    assert result.failed == 0
    discover.assert_called_once_with(
        tmp_path,
        ["test"],
        suite="ExampleSuite",
        test="test_ok",
        tags=["smoke"],
        timeout_seconds=1.5,
        retries=0,
    )
    assert run.call_args.kwargs["process_timeout"] == 42.0
    assert run.call_args.kwargs["coverage"] is None


def test_run_native_command_preflights_once_before_suite_processes(
    tmp_path,
):
    """Import, one preflight, and isolated suite execution stay ordered."""
    plain = NativeSuite(
        name="PlainSuite",
        path="res://test/plain.gd",
        tests=[NativeTest(name="test_ok")],
    )
    windowed = NativeSuite(
        name="WindowedSuite",
        path="res://test/windowed.gd",
        tests=[NativeTest(name="test_ok")],
        integration=NativeSuiteIntegration(mode=NativeExecutionMode.WINDOWED),
    )
    native = _native_result()
    events = []

    def fake_import(*args, **kwargs):
        events.append("import")

    def fake_preflight(project_root, manifest, **kwargs):
        events.append("preflight")
        assert manifest.suites == [plain, windowed]
        assert kwargs["godot_binary"] == "godot"
        assert kwargs["timeout_seconds"] == 42.0
        return _preflight([windowed, plain])

    def fake_run(project_root, suites, godot_binary, **kwargs):
        events.append("suites")
        assert suites == [windowed, plain]
        assert suites[0].integration.mode == NativeExecutionMode.WINDOWED
        assert kwargs["run_id"]
        assert kwargs["work_dir"] == (
            tmp_path / ".gd-tools" / "artifacts" / kwargs["run_id"] / "native"
        )
        return native

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
        patch(
            "gd_tools.native_test.command._import_project",
            side_effect=fake_import,
        ),
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[plain, windowed],
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=fake_preflight,
        ) as preflight,
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            side_effect=fake_run,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        result = run_native_test_command(_config(), timeout=42)

    assert result.failed == 0
    assert events == ["import", "preflight", "suites"]
    preflight.assert_called_once()
    run.assert_called_once()
    run_id = run.call_args.kwargs["run_id"]
    assert preflight.call_args.kwargs["run_dir"] == (
        tmp_path / ".gd-tools" / "artifacts" / run_id / "preflight"
    )


def _run_with_preflight_capture(tmp_path, suites, **command_kwargs):
    """Drive run_native_test_command and capture the preflight manifest."""
    captured: dict = {}

    def fake_preflight(project_root, manifest, **kwargs):
        captured["manifest"] = manifest
        captured["kwargs"] = kwargs
        return _preflight(suites)

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
            return_value=suites,
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=fake_preflight,
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=_native_result(),
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.native_test.command.output.print_info") as notice,
    ):
        run_native_test_command(_config(), **command_kwargs)
        captured["notice_calls"] = notice.call_args_list

    return captured


def test_preflight_manifest_declares_native_runtime_for_native_only_runs(
    tmp_path,
):
    """A native-only run keeps the native runtime marker on the manifest."""
    manifest = _run_with_preflight_capture(
        tmp_path,
        [NativeSuite(name="ExampleSuite", path="res://test/example.gd")],
    )["manifest"]

    assert manifest.runtime == RuntimeMode.NATIVE


def test_preflight_cache_uses_project_scoped_directory(tmp_path):
    """The cache lives at project scope so entries survive across run ids."""
    captured = _run_with_preflight_capture(
        tmp_path,
        [NativeSuite(name="ExampleSuite", path="res://test/example.gd")],
    )

    assert captured["kwargs"]["cache_dir"] == (
        tmp_path / ".gd-tools" / "native" / "preflight-cache"
    )


def test_no_cache_flag_bypasses_the_preflight_cache(tmp_path):
    """``--no-cache`` disables both preflight-cache read and write."""
    captured = _run_with_preflight_capture(
        tmp_path,
        [NativeSuite(name="ExampleSuite", path="res://test/example.gd")],
        no_cache=True,
    )

    assert captured["kwargs"]["use_cache"] is False


def test_preflight_manifest_declares_gut_runtime_for_bridge_runs(tmp_path):
    """Any bridge suite flips the manifest runtime marker to the bridge."""
    bridge = NativeSuite(
        name="LegacySuite",
        path="res://test/legacy_test.gd",
        runtime=RuntimeMode.GUT,
    )
    manifest = _run_with_preflight_capture(tmp_path, [bridge])["manifest"]

    assert manifest.runtime == RuntimeMode.GUT


def test_preflight_manifest_declares_gut_runtime_for_mixed_runs(tmp_path):
    """A mixed run reports the bridge marker so diagnostics stay honest."""
    native = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    bridge = NativeSuite(
        name="LegacySuite",
        path="res://test/legacy_test.gd",
        runtime=RuntimeMode.GUT,
    )
    manifest = _run_with_preflight_capture(tmp_path, [native, bridge])[
        "manifest"
    ]

    assert manifest.runtime == RuntimeMode.GUT


def test_bridge_run_prints_migration_notice(tmp_path):
    """Bridge runs announce the temporary bridge path (FR-9)."""
    bridge = NativeSuite(
        name="LegacySuite",
        path="res://test/legacy_test.gd",
        runtime=RuntimeMode.GUT,
    )
    captured = _run_with_preflight_capture(tmp_path, [bridge])

    notices = [str(call.args[0]) for call in captured["notice_calls"]]
    assert any(
        "compatibility bridge" in notice and "docs/gut-migration.md" in notice
        for notice in notices
    )


def test_native_only_run_prints_no_bridge_notice(tmp_path):
    """Pure native runs do not mention the bridge."""
    native = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    captured = _run_with_preflight_capture(tmp_path, [native])

    notices = [str(call.args[0]) for call in captured["notice_calls"]]
    assert not any("compatibility bridge" in notice for notice in notices)


def test_run_native_command_propagates_preflight_failure(tmp_path):
    """Preflight infrastructure failures stop before suite execution."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=NativePreflightError("invalid integration declaration"),
        ),
        patch("gd_tools.native_test.command.run_native_tests") as run,
    ):
        with pytest.raises(NativePreflightError, match="invalid integration"):
            run_native_test_command(_config())

    run.assert_not_called()
    indexes = list(
        (tmp_path / ".gd-tools" / "artifacts").glob("*/artifacts.json")
    )
    assert len(indexes) == 1
    index = json.loads(indexes[0].read_text(encoding="utf-8"))
    assert index["status"] == "error"
    assert index["preflight"]["result"].endswith("preflight.result.json")


def test_run_native_command_marks_the_run_before_preflight_runs(tmp_path):
    """A run that dies before publishing an index is still prunable.

    The marker is written before preflight, so a run that never reaches
    ``publish_artifact_index`` still leaves a directory retention recognizes.
    Without this, the write would be reachable only through pre-existing
    prune tests, which hand-build the marker instead of calling the writer.
    """
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=RuntimeError("preflight process died"),
        ),
    ):
        with pytest.raises(RuntimeError, match="preflight process died"):
            run_native_test_command(_config())

    run_dirs = [
        path
        for path in (tmp_path / ".gd-tools" / "artifacts").iterdir()
        if path.is_dir()
    ]
    assert len(run_dirs) == 1
    assert (run_dirs[0] / ".gdtools-run").exists()
    assert not (run_dirs[0] / "artifacts.json").exists()


def test_run_native_command_reports_a_failing_run_directory_creation(tmp_path):
    """An unwritable artifact root is an environment error, not a traceback."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command.mark_run_started",
            side_effect=OSError("no space left on device"),
        ),
    ):
        with pytest.raises(GdToolsError, match="run directory") as excinfo:
            run_native_test_command(_config())

    assert excinfo.value.exit_code == 2
    assert "no space left on device" in str(excinfo.value)


def test_run_native_command_empty_suites_gives_gut_guidance(tmp_path):
    """A GUT-only or empty project gets actionable runtime guidance."""
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
        patch(
            "gd_tools.native_test.command.discover_native_suites",
            return_value=[],
        ),
    ):
        with pytest.raises(
            ConfigError, match=r"Add a suite extending GdToolsTest"
        ):
            run_native_test_command(_config())


def test_run_native_command_raises_failure_unless_no_exit_code(tmp_path):
    """Test failures preserve the existing exit-code contract."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite", name="test_fail", status="failed"
            )
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(_config())
        result = run_native_test_command(_config(), no_exit_code=True)

    assert result.failed == 1


def test_run_native_command_prioritizes_test_failure_over_coverage_threshold(
    tmp_path,
):
    """A test failure remains the primary error when coverage also fails."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "failed",
        [
            NativeTestResult(
                suite="ExampleSuite", name="test_fail", status="failed"
            )
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch(
            "gd_tools.native_test.command._generate_native_report",
            side_effect=CoverageThresholdError("below threshold"),
        ),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(_config(), coverage=True, min_percent=100)


def test_run_native_command_raises_infrastructure_error(tmp_path):
    """A native runtime error maps to the configuration exit class."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "error",
        [
            NativeTestResult(
                suite="ExampleSuite", name="<process>", status="error"
            )
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
    ):
        with pytest.raises(GdToolsError, match="infrastructure"):
            run_native_test_command(_config())


# --- Phase 6: reporting and exit codes for integration runs ---


def test_run_native_command_surfaces_the_published_artifact_index(tmp_path):
    """A completed run reports the index path it actually received."""
    from gd_tools.native_test.command import _to_test_result

    index_path = tmp_path / "run-1" / "artifacts.json"
    native = _native_result(
        status="passed",
        tests=[{"name": "test_pass", "status": "passed", "suite": "S"}],
    )
    native = native.model_copy(update={"artifact_index_path": index_path})

    result = _to_test_result(native, tmp_path, str(tmp_path / "results.xml"))

    assert result.artifact_index_path == index_path
    junit = (tmp_path / "results.xml").read_text(encoding="utf-8")
    assert f'name="artifact_index" value="{index_path}"' in junit
    # A run with no published index reports none rather than a placeholder.
    without = _native_result(
        status="passed",
        tests=[{"name": "test_pass", "status": "passed", "suite": "S"}],
    )
    assert _to_test_result(without, tmp_path, None).artifact_index_path is None


def test_run_native_command_reports_infrastructure_error_before_raising(
    tmp_path,
):
    """Infrastructure failures still publish JUnit, artifacts, and CLI output."""
    junit_path = tmp_path / "results.xml"
    artifact_index = (
        tmp_path / ".gd-tools" / "artifacts" / "run-1" / "artifacts.json"
    )
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "error",
        [
            NativeTestResult(
                suite="ExampleSuite",
                name="<suite>",
                status="error",
                message="Suite could not load",
                diagnostics={"screenshot": "suite-0000.failure.png"},
            ),
            NativeTestResult(
                suite="LaterSuite",
                name="test_ok",
                status="passed",
            ),
        ],
    )
    native.artifact_index_path = artifact_index
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch("gd_tools.native_test.command._generate_native_report") as report,
        patch(
            "gd_tools.native_test.command.format_test_results"
        ) as format_results,
    ):
        with pytest.raises(GdToolsError, match="Suite could not load"):
            run_native_test_command(_config(), junit_xml=str(junit_path))

    report.assert_called_once()
    format_results.assert_called_once()
    assert junit_path.is_file()
    root = ET.parse(junit_path).getroot()
    assert root.find("testsuite").attrib["tests"] == "2"
    failures = root.findall("testsuite/testcase/failure")
    assert len(failures) == 1
    assert "screenshot" in failures[0].text
    assert (
        root.find("testsuite/testcase[2]").attrib["classname"] == "LaterSuite"
    )
    artifact_property = root.find("testsuite/properties/property")
    assert artifact_property is not None
    assert artifact_property.attrib["name"] == "artifact_index"
    assert artifact_property.attrib["value"] == str(artifact_index)


def test_run_native_command_infrastructure_error_dominates_test_failure(
    tmp_path,
):
    """Infrastructure failures stay exit-2 beside test and coverage failures."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    native = _native_result(
        "error",
        [
            NativeTestResult(
                suite="ExampleSuite",
                name="test_fail",
                status="failed",
                message="assertion failed",
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="<process>",
                status="error",
                message="windowed display unavailable",
            ),
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests", return_value=native
        ),
        patch(
            "gd_tools.native_test.command._generate_native_report",
            side_effect=CoverageThresholdError("below threshold"),
        ),
    ):
        with pytest.raises(GdToolsError, match="windowed display unavailable"):
            run_native_test_command(_config(), coverage=True, min_percent=100)

    junit_path = tmp_path / ".gd-tools" / "results.xml"
    assert junit_path.is_file()
    root = ET.parse(junit_path).getroot()
    assert root.find("testsuite").attrib["tests"] == "2"


def test_native_report_still_reconciles_when_threshold_fails(tmp_path):
    """R6: the report and the omission gate survive a threshold failure.

    The legacy seam reports the coverage and evaluates the omission gate even
    when generate_report raises the threshold error, so `--min` plus
    omissions exits 2 with the partial block visible. The native seam must
    reach the same shared `_report_coverage` on that path instead of
    short-circuiting, or the two runtimes disagree exactly when the gate
    matters most.
    """
    coverage_dir = tmp_path / ".gd-tools" / "coverage"
    coverage_dir.mkdir(parents=True)
    (coverage_dir / "plan.json").write_text(
        json.dumps(
            {
                "version": 2,
                "generated_by": "gd-tools-test",
                "files": [
                    {
                        "file_id": 0,
                        "path": "res://scripts/a.gd",
                        "source_hash": "sha256:test",
                        "lines": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00",
                "files": [],
            }
        ),
        encoding="utf-8",
    )
    result = _native_result().model_copy(
        update={"coverage_data_path": coverage_path}
    )
    summary = object()
    error = CoverageThresholdError(
        "below threshold",
        report_result=SimpleNamespace(summary=summary, file_summaries=[]),
    )
    with (
        patch(
            "gd_tools.native_test.command.reporter.generate_report",
            side_effect=error,
        ),
        patch(
            "gd_tools.native_test.command._report_coverage"
        ) as report_coverage,
    ):
        with pytest.raises(CoverageThresholdError) as excinfo:
            _generate_native_report(
                _config(),
                tmp_path,
                result,
                coverage=True,
                min_percent=90,
                show_uncovered=False,
                no_cache=False,
            )

    assert excinfo.value is error
    report_coverage.assert_called_once()
    assert report_coverage.call_args.args[2] is summary


def test_run_native_command_forwards_parallel_to_orchestrator(tmp_path):
    """The adapter passes the parallel worker count to the orchestrator."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=_native_result(),
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        run_native_test_command(_config(), parallel=4)

    assert run.call_args.kwargs["parallel"] == 4


def test_run_native_command_parallel_omitted_runs_sequential(tmp_path):
    """parallel=None propagates the sequential default to the orchestrator."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=_native_result(),
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        run_native_test_command(_config())

    assert run.call_args.kwargs["parallel"] is None


def test_run_native_command_parallel_failed_tests_raise_exit_1(tmp_path):
    """A failed suite under parallel still raises TestFailureError (exit 1)."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    failed = _native_result(
        status="failed",
        tests=[
            NativeTestResult(
                suite="ExampleSuite",
                name="test_ok",
                status="passed",
            ),
            NativeTestResult(
                suite="ExampleSuite",
                name="test_bad",
                status="failed",
            ),
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=failed,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        with pytest.raises(TestFailureError):
            run_native_test_command(_config(), parallel=2)


def test_run_native_command_parallel_infrastructure_error_exits_2(tmp_path):
    """An infrastructure error under parallel still exits with code 2."""
    suite = NativeSuite(name="ExampleSuite", path="res://test/example.gd")
    error = _native_result(
        status="error",
        tests=[
            NativeTestResult(
                suite="ExampleSuite",
                name="test_ok",
                status="error",
                message="engine crashed",
            ),
        ],
    )
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
            return_value=[suite],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([suite]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=error,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        with pytest.raises(GdToolsError) as excinfo:
            run_native_test_command(_config(), parallel=2)

    assert excinfo.value.exit_code == 2


def test_changed_empty_change_set_exits_early_without_godot(tmp_path):
    """--changed with no changes reports and returns before any Godot work."""
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[],
        ) as collect,
        patch("gd_tools.native_test.command.find_godot") as find_godot,
        patch(
            "gd_tools.native_test.command.output.print_info"
        ) as notice,
    ):
        result = run_native_test_command(_config(), changed=True)

    assert result.total == 0
    find_godot.assert_not_called()
    assert "no changes detected" in notice.call_args.args[0]


def test_changed_narrows_discovery_to_mapped_suites(tmp_path):
    """--changed runs only the suites mapped from the changed files."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[enemy, player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda project_root, manifest, **kw: _preflight(
                list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch(
            "gd_tools.native_test.command.output.print_info"
        ) as notice,
    ):
        run_native_test_command(_config(), changed=True)

    executed = run.call_args.args[1]
    assert [suite.path for suite in executed] == ["res://tests/test_enemy.gd"]
    assert any(
        "--changed: 1 of 2 suites selected" in call.args[0]
        for call in notice.call_args_list
    )


def test_changed_unmapped_file_falls_back_to_full_suite(tmp_path):
    """A change that maps to no suite runs everything with a notice."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[enemy, player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("project.godot")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([enemy, player]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch(
            "gd_tools.native_test.command.output.print_info"
        ) as notice,
    ):
        run_native_test_command(_config(), changed=True)

    executed = run.call_args.args[1]
    assert [suite.path for suite in executed] == [
        "res://tests/test_enemy.gd",
        "res://tests/test_player.gd",
    ]
    assert any(
        "No suite mapped for 'project.godot'" in call.args[0]
        for call in notice.call_args_list
    )


def test_changed_base_flag_switches_the_change_source(tmp_path):
    """--base forwards the ref to change collection."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    native = _native_result()
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
            return_value=[enemy],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ) as collect,
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([enemy]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
    ):
        run_native_test_command(_config(), changed=True, base="main")

    collect.assert_called_once_with(tmp_path, "main")


def test_changed_collection_error_propagates_exit_2(tmp_path):
    """Git failures surface as GdToolsError (exit 2) with the message."""
    with (
        patch(
            "gd_tools.native_test.command.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            side_effect=GitChangeError(
                "Not a git repository: --changed requires the project to "
                "be tracked by git."
            ),
        ),
        pytest.raises(GitChangeError) as exc_info,
    ):
        run_native_test_command(_config(), changed=True)

    assert exc_info.value.exit_code == 2


def test_changed_verbose_prints_per_file_mapping(tmp_path):
    """--verbose prints each changed file's mapping detail."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[enemy, player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            return_value=_preflight([enemy, player]),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ),
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch(
            "gd_tools.native_test.command.output.print_verbose"
        ) as verbose,
    ):
        run_native_test_command(_config(), changed=True)

    assert any(
        "src/enemy.gd" in call.args[0]
        and "res://tests/test_enemy.gd" in call.args[0]
        for call in verbose.call_args_list
    )


def test_changed_composes_with_parallel(tmp_path):
    """--changed + --parallel runs the narrowed suites concurrently."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[enemy, player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda project_root, manifest, **kw: _preflight(
                list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.native_test.command.output.print_info"),
    ):
        run_native_test_command(_config(), changed=True, parallel=2)

    assert [suite.path for suite in run.call_args.args[1]] == [
        "res://tests/test_enemy.gd"
    ]
    assert run.call_args.kwargs["parallel"] == 2


def test_changed_composes_with_coverage(tmp_path):
    """--changed + --coverage instruments only the executed (narrowed) suites."""
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[enemy, player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=("coverage-settings", None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda project_root, manifest, **kw: _preflight(
                list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.native_test.command.output.print_info"),
    ):
        run_native_test_command(_config(), changed=True, coverage=True)

    assert [suite.path for suite in run.call_args.args[1]] == [
        "res://tests/test_enemy.gd"
    ]
    assert run.call_args.kwargs["coverage"] == "coverage-settings"


def test_changed_with_suite_filter_maps_within_selection(tmp_path):
    """--suite narrows discovery first; --changed maps within that
    selection (the already-filtered suites are the mapping domain)."""
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    native = _native_result()
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
            return_value=[player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/player.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda project_root, manifest, **kw: _preflight(
                list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch("gd_tools.native_test.command.output.print_info"),
    ):
        run_native_test_command(_config(), changed=True)

    assert [suite.path for suite in run.call_args.args[1]] == [
        "res://tests/test_player.gd"
    ]


def test_changed_with_suite_filter_falls_back_to_filtered_selection(tmp_path):
    """A change mapping outside the --suite selection falls back to the
    filtered selection, not the full discovery set."""
    player = NativeSuite(name="TestPlayer", path="res://tests/test_player.gd")
    enemy = NativeSuite(name="TestEnemy", path="res://tests/test_enemy.gd")
    native = _native_result()
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
            return_value=[player],
        ),
        patch(
            "gd_tools.native_test.command.collect_changed_files",
            return_value=[Path("src/enemy.gd")],
        ),
        patch(
            "gd_tools.native_test.command._prepare_coverage",
            return_value=(None, None),
        ),
        patch(
            "gd_tools.native_test.command.run_preflight_cached",
            side_effect=lambda project_root, manifest, **kw: _preflight(
                list(manifest.suites)
            ),
        ),
        patch(
            "gd_tools.native_test.command.run_native_tests",
            return_value=native,
        ) as run,
        patch("gd_tools.native_test.command._generate_native_report"),
        patch("gd_tools.native_test.command.format_test_results"),
        patch(
            "gd_tools.native_test.command.output.print_info"
        ) as notice,
    ):
        run_native_test_command(_config(), changed=True)

    assert [suite.path for suite in run.call_args.args[1]] == [
        "res://tests/test_player.gd"
    ]
    assert any(
        "No suite mapped for 'src/enemy.gd'" in call.args[0]
        for call in notice.call_args_list
    )
