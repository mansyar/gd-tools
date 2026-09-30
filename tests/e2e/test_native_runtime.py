"""E2E checks for the native Godot test runtime."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import import_godot_project

from gd_tools.config import GdToolsConfig, GodotConfig, TestConfig
from gd_tools.native_test.command import run_native_test_command
from gd_tools.native_test.orchestrator import run_native_tests
from gd_tools.native_test.protocol import NativeSuite, NativeTest

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


def _prepare_project(tmp_path: Path, godot_bin: str) -> Path:
    """Copy the clean fixture and import the native addon class cache."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_godot_project(godot_bin, project)
    return project


def _run_native_manifest(
    project: Path,
    godot_bin: str,
    manifest: dict,
    result_path: Path,
    *,
    events_path: Path | None = None,
    log_path: Path | None = None,
):
    """Run the native Godot runner with optional event and log artifacts."""
    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(
        result_path.with_suffix(".manifest.json")
    )
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    if events_path is not None:
        env["GD_TOOLS_NATIVE_EVENTS"] = str(events_path)
    if log_path is not None:
        env["GD_TOOLS_NATIVE_LOG"] = str(log_path)
    result_path.with_suffix(".manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    command = [
        godot_bin,
        "--headless",
        "--path",
        str(project),
        "--script",
        "res://addons/gd-tools-test/gd_tools_test_runner.gd",
    ]
    if log_path is not None:
        command.extend(["--log-file", str(log_path)])
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )


def test_native_fixture_loads_without_gut(godot_bin, tmp_path):
    """A native fixture must load without a GUT installation."""
    project = tmp_path / "native_test_project"
    shutil.copytree(NATIVE_FIXTURE, project)
    shutil.copytree(NATIVE_ADDON, project / "addons" / "gd-tools-test")

    import_godot_project(godot_bin, project)

    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://test/load_native_suite.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Parser Error" not in result.stdout + result.stderr
    assert not (project / "addons" / "gut").exists()


def _manifest(project, path, names, suite_name):
    """Build a native manifest selecting specific methods from one suite."""
    return {
        "protocol_version": 3,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": suite_name,
                "path": path,
                "tests": [{"name": name} for name in names],
            }
        ],
        "coverage": {"enabled": False},
    }


SATISFYING_METHODS = [
    "test_gt_passes_when_greater",
    "test_gte_passes_when_equal",
    "test_lt_passes_when_less",
    "test_lte_passes_when_equal",
    "test_between_passes_in_range",
    "test_between_inclusive_lower_bound",
    "test_between_inclusive_upper_bound",
    "test_almost_eq_passes_within_delta",
    "test_has_passes_for_present_element",
    "test_in_passes_for_present_element",
    "test_has_argument_order",
    "test_in_argument_order",
    "test_has_works_on_dictionary",
    "test_has_works_on_string_via_contains",
    "test_has_method_passes_for_existing_method",
    "test_is_passes_for_same_instance",
    "test_is_passes_for_shared_array",
]

FAILING_METHODS = [
    "test_gt_fails_when_not_greater",
    "test_gte_fails_when_less",
    "test_lt_fails_when_not_less",
    "test_lte_fails_when_greater",
    "test_between_fails_below_lower_bound",
    "test_between_fails_above_upper_bound",
    "test_between_fails_when_bounds_inverted",
    "test_almost_eq_fails_outside_delta",
    "test_has_fails_for_absent_element",
    "test_in_fails_for_absent_element",
    "test_has_method_fails_for_missing_method",
    "test_is_fails_for_distinct_instances",
]

TYPE_SAFETY_METHODS = [
    "test_between_rejects_non_numeric_value",
    "test_between_rejects_non_numeric_bound",
    "test_almost_eq_rejects_non_numeric",
    "test_has_rejects_non_container",
    "test_in_rejects_non_container",
    "test_has_method_rejects_non_object",
    "test_is_rejects_value_types",
    "test_is_rejects_null",
]


def _single_failure(payload, name):
    """Return the one recorded failure for a test, asserting there is exactly one."""
    entry = next(item for item in payload["tests"] if item["name"] == name)
    failures = entry["diagnostics"]["failures"]
    assert len(failures) == 1, f"{name} recorded {failures}"
    return failures[0]


def test_native_new_assertions_pass_on_satisfying_input(godot_bin, tmp_path):
    """Every GUT-core assertion passes when its contract is satisfied (R5)."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "satisfying.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/assertion_suite.gd",
            SATISFYING_METHODS,
            "NativeAssertionSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(SATISFYING_METHODS), payload["tests"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_native_new_assertions_report_values_and_message_detail(
    godot_bin, tmp_path
):
    """A violated assertion reports values and names the specific detail (R5, R6)."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "violated.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/assertion_failures_suite.gd",
            FAILING_METHODS,
            "NativeAssertionFailuresSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(FAILING_METHODS), payload["tests"]
    assert result.returncode == 1, result.stdout + result.stderr

    # R5: assert_between must name the violated bound and its value.
    lower = _single_failure(payload, "test_between_fails_below_lower_bound")
    assert lower["assertion"] == "assert_between"
    assert "0" in lower["message"], lower
    upper = _single_failure(payload, "test_between_fails_above_upper_bound")
    assert upper["assertion"] == "assert_between"
    assert "10" in upper["message"], upper

    # R5: assert_has / assert_in must name the missing element.
    has_failure = _single_failure(payload, "test_has_fails_for_absent_element")
    assert has_failure["assertion"] == "assert_has"
    assert "99" in has_failure["message"], has_failure
    in_failure = _single_failure(payload, "test_in_fails_for_absent_element")
    assert in_failure["assertion"] == "assert_in"
    assert "missing" in in_failure["message"], in_failure

    # R5: assert_almost_eq must name the observed delta and the allowance.
    almost = _single_failure(payload, "test_almost_eq_fails_outside_delta")
    assert almost["assertion"] == "assert_almost_eq"
    assert "0.1" in almost["message"], almost

    # R5: assert_has_method must name the object's type and the method.
    method = _single_failure(
        payload, "test_has_method_fails_for_missing_method"
    )
    assert method["assertion"] == "assert_has_method"
    assert "definitely_not_a_method" in method["message"], method

    # R5: assert_is must name both types and the distinctness.
    identity = _single_failure(payload, "test_is_fails_for_distinct_instances")
    assert identity["assertion"] == "assert_is"
    assert "distinct" in identity["message"].lower(), identity

    # R6: every failure still populates actual and expected.
    for name in FAILING_METHODS:
        failure = _single_failure(payload, name)
        assert failure["actual"] != "", name
        assert failure["expected"] != "", name


def test_native_assertions_are_attributed_to_user_code(godot_bin, tmp_path):
    """A new assertion is attributed to the user's line, not the base class (R6)."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "attributed.json"
    _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/assertion_failures_suite.gd",
            FAILING_METHODS,
            "NativeAssertionFailuresSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(FAILING_METHODS), payload["tests"]
    for name in FAILING_METHODS:
        failure = _single_failure(payload, name)
        assert "assertion_failures_suite.gd" in failure["source"], failure
        assert "gd_tools_test.gd" not in failure["source"], failure
        assert failure["line"] > 0, failure


def test_native_assertion_type_mismatch_fails_the_test_not_the_run(
    godot_bin, tmp_path
):
    """A wrong-typed argument fails the test; it must never escalate the run (R4)."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "type-safety.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/assertion_type_safety_suite.gd",
            TYPE_SAFETY_METHODS,
            "NativeAssertionTypeSafetySuite",
        ),
        result_path,
        # The log path must be set or the capture never runs, which would make
        # the `engine_errors` assertion below vacuously true. Found by code
        # review: this line was absent and the assertion proved nothing.
        log_path=tmp_path / "type-safety.log",
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(TYPE_SAFETY_METHODS), payload["tests"]

    # The R4 guarantee: every method here fails BY DESIGN, so exit 1 is correct.
    # Exit 2 is the failure this test exists to prevent -- a GDScript runtime
    # error is captured by the runner and escalates the whole run to an
    # environment failure, misrepresenting one bad call as a broken install.
    assert result.returncode == 1, result.stdout + result.stderr
    assert payload["status"] == "failed"
    assert payload["engine_errors"] == [], payload["engine_errors"]
    assert all(
        entry["status"] != "error" for entry in payload["tests"]
    ), payload

    # Every one records an actionable failure naming the type problem.
    for name in TYPE_SAFETY_METHODS:
        entry = next(item for item in payload["tests"] if item["name"] == name)
        assert entry["status"] == "failed", (name, entry["status"])
        message = _single_failure(payload, name)["message"]
        assert (
            "int" in message
            or "String" in message
            or "float" in message
            or "Nil" in message
        ), (name, message)
        assert "expects" in message or "identity" in message, (name, message)


# Methods whose container is valid but whose ELEMENT the container cannot hold.
# Found by code review: the container was type-checked, the element was not, so
# `assert_has("abc", 5)` reached `String.contains(5)` and raised a SCRIPT ERROR.
ELEMENT_MISMATCH_METHODS = [
    "test_has_rejects_element_a_string_container_cannot_hold",
    "test_in_rejects_element_a_string_container_cannot_hold",
    "test_has_rejects_element_a_packed_int_array_cannot_hold",
]

# The valid counterpart, which must KEEP passing: a correct element is
# unaffected by the new check, so this guards against over-rejecting.
ACCEPTING_ELEMENT_METHOD = (
    "test_has_accepts_an_element_a_string_container_can_hold"
)


def test_native_membership_element_mismatch_fails_the_test_not_the_run(
    godot_bin, tmp_path
):
    """A wrong-typed membership ELEMENT fails the test; it must not raise (R4).

    The container check alone was insufficient. Before this fix each of these
    recorded a MISSING-ELEMENT message ("String does not contain 5") because
    the raise happened inside `contains()` rather than at the assertion. The run
    still exited 1 by accident, so the exit-code criterion passed while the
    message described the wrong problem and stderr carried a SCRIPT ERROR that
    the engine-diagnostics capture could not see.
    """
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "element-mismatch.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/assertion_type_safety_suite.gd",
            ELEMENT_MISMATCH_METHODS + [ACCEPTING_ELEMENT_METHOD],
            "NativeAssertionTypeSafetySuite",
        ),
        result_path,
        log_path=tmp_path / "element-mismatch.log",
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(ELEMENT_MISMATCH_METHODS) + 1, payload[
        "tests"
    ]

    # Exit 1, not 2. A wrong-typed argument is a test failure; escalating it to
    # an environment failure is the outcome R4 exists to prevent.
    assert result.returncode == 1, result.stdout + result.stderr
    assert payload["engine_errors"] == [], payload["engine_errors"]

    for name in ELEMENT_MISMATCH_METHODS:
        message = _single_failure(payload, name)["message"]
        # The message must name the ELEMENT as the problem. The argument
        # position follows each assertion's own signature, which is inverted
        # for `assert_in` on purpose: the element is argument 1 there, not 2.
        position = 1 if name.startswith("test_in_") else 2
        assert "expects" in message, (name, message)
        assert f"argument {position}" in message, (name, message)
        # It must NOT read as a missing element, which is what it said before.
        assert "does not contain" not in message, (name, message)

    # The valid counterpart must still pass, so the new check does not
    # over-reject: a correct element is unaffected by it.
    passing = next(
        item
        for item in payload["tests"]
        if item["name"] == ACCEPTING_ELEMENT_METHOD
    )
    assert passing["status"] == "passed", passing


def test_native_script_errors_are_captured_and_escalate(godot_bin, tmp_path):
    """A GDScript SCRIPT ERROR must be captured and must exit 2.

    Found by code review: `_capture_engine_diagnostics` matched only lines
    beginning "ERROR:", but GDScript reports a runtime script error as
    "SCRIPT ERROR:". Every such error was written to the captured log and then
    ignored, so `engine_errors` stayed empty and the exit-2 escalation that is
    supposed to catch a broken run never fired.
    """
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "script-error.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/engine_error_suite.gd",
            [
                "test_raises_a_runtime_script_error",
                "test_after_the_error_also_reports",
            ],
            "NativeEngineErrorSuite",
        ),
        result_path,
        log_path=tmp_path / "script-error.log",
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert result.returncode == 2, result.stdout + result.stderr
    assert payload["status"] == "error", payload["status"]
    assert payload["engine_errors"], "the SCRIPT ERROR was not captured"
    assert any(
        "no_such_method_exists" in line for line in payload["engine_errors"]
    ), payload["engine_errors"]

    # The runner kept going: the error is captured, not a suite that aborted.
    names = [entry["name"] for entry in payload["tests"]]
    assert "test_after_the_error_also_reports" in names, names


def test_native_runner_executes_manifest(godot_bin, tmp_path):
    """The native runner executes sync/async tests from a manifest."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "manifest.json"
    result_path = tmp_path / "native-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeFixtureSuite",
                        "path": "res://test/native_suite.gd",
                        "tags": ["native"],
                        "tests": [
                            {"name": "test_pass", "timeout_seconds": 5.0},
                            {"name": "test_async", "timeout_seconds": 5.0},
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["protocol_version"] == 3
    assert payload["status"] == "passed"
    assert [test["name"] for test in payload["tests"]] == [
        "test_pass",
        "test_async",
    ]
    assert all(test["status"] == "passed" for test in payload["tests"])


def test_native_runner_runs_lifecycle_hooks_after_failure(godot_bin, tmp_path):
    """Lifecycle hooks run in order and cleanup follows a failed test."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "lifecycle-manifest.json"
    result_path = tmp_path / "lifecycle-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeLifecycleSuite",
                        "path": "res://test/lifecycle_suite.gd",
                        "tests": [
                            {"name": "test_pass"},
                            {"name": "test_fail"},
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    events = (
        (project / "lifecycle.log").read_text(encoding="utf-8").splitlines()
    )
    assert events == [
        "before_all",
        "before_each",
        "test_pass",
        "after_each",
        "before_each",
        "test_fail",
        "after_each",
        "after_all",
    ]
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert [test["status"] for test in payload["tests"]] == [
        "passed",
        "failed",
    ]


def test_native_runner_reports_lifecycle_failures_and_preserves_suite_state(
    godot_bin, tmp_path
):
    """Setup/teardown failures and suite state affect the native result."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 3,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeBeforeAllFailureSuite",
                "path": "res://test/review_before_all_suite.gd",
                "tests": [{"name": "test_never_reports_green"}],
            },
            {
                "name": "NativeAfterAllFailureSuite",
                "path": "res://test/review_after_all_suite.gd",
                "tests": [{"name": "test_pass"}],
            },
            {
                "name": "NativeReviewStateSuite",
                "path": "res://test/review_state_suite.gd",
                "tests": [{"name": "test_uses_suite_state"}],
            },
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "review-lifecycle-result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    results = payload["tests"]
    before_result = next(
        test for test in results if test["name"] == "before_all"
    )
    after_result = next(test for test in results if test["name"] == "after_all")
    state_result = next(
        test for test in results if test["name"] == "test_uses_suite_state"
    )
    assert before_result["status"] == "failed"
    assert before_result["suite"] == "NativeBeforeAllFailureSuite"
    assert after_result["status"] == "failed"
    assert after_result["suite"] == "NativeAfterAllFailureSuite"
    assert state_result["status"] == "passed"


def test_native_runner_bounds_lifecycle_timeout_and_runs_cleanup(
    godot_bin, tmp_path
):
    """A hanging setup hook is bounded and cleanup still runs."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 3,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeReviewTimeoutCleanupSuite",
                "path": "res://test/review_timeout_cleanup_suite.gd",
                "tests": [
                    {
                        "name": "test_pass",
                        "timeout_seconds": 0.05,
                    }
                ],
            }
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "review-timeout-result.json"
    log_path = tmp_path / "godot-timeout.log"

    process = _run_native_manifest(
        project,
        godot_bin,
        manifest,
        result_path,
        log_path=log_path,
    )

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    test = payload["tests"][0]
    assert test["status"] == "timeout"
    assert test["duration_seconds"] < 0.5
    assert (project / "review-timeout.log").read_text(
        encoding="utf-8"
    ).splitlines() == ["after_each"]


def test_native_runner_captures_engine_errors_and_warnings(godot_bin, tmp_path):
    """Godot engine diagnostics fail the run and appear in native JSON."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = {
        "protocol_version": 3,
        "project_root": str(project),
        "runtime": "native",
        "suites": [
            {
                "name": "NativeEngineDiagnosticsSuite",
                "path": "res://test/engine_diagnostics_suite.gd",
                "tests": [{"name": "test_engine_diagnostics"}],
            }
        ],
        "coverage": {"enabled": False},
    }
    result_path = tmp_path / "engine-diagnostics-result.json"
    log_path = tmp_path / "godot-engine.log"

    process = _run_native_manifest(
        project,
        godot_bin,
        manifest,
        result_path,
        log_path=log_path,
    )

    assert process.returncode == 2, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "error"
    assert any(
        "native engine error" in item for item in payload["engine_errors"]
    )
    assert any(
        "native engine warning" in item for item in payload["engine_warnings"]
    )


def test_native_assertions_report_values_and_source(godot_bin, tmp_path):
    """Assertion failures include values, message, and source location."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "assertion-manifest.json"
    result_path = tmp_path / "assertion-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeAssertionSuite",
                        "path": "res://test/assertion_suite.gd",
                        "tests": [{"name": "test_structured_failure"}],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    failure = payload["tests"][0]["diagnostics"]["failures"][0]
    assert failure["assertion"] == "assert_eq"
    assert failure["actual"] == "1"
    assert failure["expected"] == "2"
    assert failure["message"] == "values differ"
    assert "assertion_suite.gd" in failure["source"]
    assert failure["line"] > 0


def test_native_skipped_tests_report_status_and_reason(godot_bin, tmp_path):
    """A skip reports `skipped` with its reason and does not consume a retry."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "skip-status-result.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        {
            "protocol_version": 3,
            "project_root": str(project),
            "runtime": "native",
            "suites": [
                {
                    "name": "NativeSkipSuite",
                    "path": "res://test/skip_suite.gd",
                    "tests": [
                        {"name": "test_skips_with_reason", "retries": 2},
                        {"name": "test_skips_without_reason"},
                        {"name": "test_pending_test_alias"},
                    ],
                }
            ],
            "coverage": {"enabled": False},
        },
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    by_name = {test["name"]: test for test in payload["tests"]}
    with_reason = by_name["test_skips_with_reason"]
    without_reason = by_name["test_skips_without_reason"]
    pending = by_name["test_pending_test_alias"]

    assert result.returncode == 0, result.stdout + result.stderr
    assert with_reason["status"] == "skipped"
    assert with_reason["message"] == "no network in sandbox"
    # A skip is terminal, so the configured retry is never consumed.
    assert with_reason["attempts"] == 1
    assert without_reason["status"] == "skipped"
    assert without_reason["message"] != ""
    assert pending["status"] == "skipped"
    assert pending["message"] == "alias path"


def test_native_post_skip_assertions_are_discarded(godot_bin, tmp_path):
    """A failure recorded after a skip is discarded; one before it survives."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "skip-guard-result.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        {
            "protocol_version": 3,
            "project_root": str(project),
            "runtime": "native",
            "suites": [
                {
                    "name": "NativeSkipSuite",
                    "path": "res://test/skip_suite.gd",
                    "tests": [
                        {"name": "test_assertion_after_skip_is_discarded"},
                        {"name": "test_fail_after_skip_is_discarded"},
                        {"name": "test_failure_before_skip_still_fails"},
                    ],
                }
            ],
            "coverage": {"enabled": False},
        },
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    by_name = {test["name"]: test for test in payload["tests"]}
    after_assert = by_name["test_assertion_after_skip_is_discarded"]
    after_fail = by_name["test_fail_after_skip_is_discarded"]
    before_skip = by_name["test_failure_before_skip_still_fails"]

    assert result.returncode == 1, result.stdout + result.stderr
    assert after_assert["status"] == "skipped"
    assert after_assert["diagnostics"]["failures"] == []
    assert after_fail["status"] == "skipped"
    assert after_fail["diagnostics"]["failures"] == []
    assert before_skip["status"] == "failed"
    assert (
        before_skip["diagnostics"]["failures"][0]["message"] == "real failure"
    )


def test_native_all_skipped_suite_exits_zero(godot_bin, tmp_path):
    """A suite whose every test skips does not escalate the run."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "all-skip-result.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        {
            "protocol_version": 3,
            "project_root": str(project),
            "runtime": "native",
            "suites": [
                {
                    "name": "NativeSkipSuite",
                    "path": "res://test/skip_suite.gd",
                    "tests": [
                        {"name": "test_skips_with_reason"},
                        {"name": "test_skips_without_reason"},
                        {"name": "test_assertion_after_skip_is_discarded"},
                        {"name": "test_fail_after_skip_is_discarded"},
                        {"name": "test_pending_test_alias"},
                    ],
                }
            ],
            "coverage": {"enabled": False},
        },
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    # Assert the suite actually ran: a suite that fails to load is dropped
    # silently, which would satisfy `all()` over an empty test list.
    assert len(payload["tests"]) == 5, payload["tests"]
    assert all(test["status"] == "skipped" for test in payload["tests"])


def test_native_runner_emits_structured_events(godot_bin, tmp_path):
    """The runner writes parseable NDJSON lifecycle events when requested."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "event-manifest.json"
    result_path = tmp_path / "event-result.json"
    events_path = tmp_path / "events.ndjson"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeFixtureSuite",
                        "path": "res://test/native_suite.gd",
                        "tests": [{"name": "test_pass"}],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    env["GD_TOOLS_NATIVE_EVENTS"] = str(events_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == [
        "run_started",
        "test_started",
        "test_finished",
        "run_finished",
    ]
    assert events[2]["status"] == "passed"
    assert all(event["suite"] == "NativeFixtureSuite" for event in events)
    assert all(event["worker_slot"] == 0 for event in events)


def test_native_runner_events_carry_env_suite_identity(godot_bin, tmp_path):
    """Env-provided suite name and worker slot are stamped into events."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "slot-manifest.json"
    result_path = tmp_path / "slot-result.json"
    events_path = tmp_path / "slot-events.ndjson"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeFixtureSuite",
                        "path": "res://test/native_suite.gd",
                        "tests": [{"name": "test_pass"}],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    env["GD_TOOLS_NATIVE_EVENTS"] = str(events_path)
    env["GD_TOOLS_SUITE_NAME"] = "EnvNamedSuite"
    env["GD_TOOLS_WORKER_SLOT"] = "3"
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
    ]
    assert events, "expected at least one NDJSON event"
    assert all(event["suite"] == "EnvNamedSuite" for event in events)
    assert all(event["worker_slot"] == 3 for event in events)


def test_native_runner_marks_timed_out_tests(godot_bin, tmp_path):
    """A test exceeding its manifest timeout gets a timeout result."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "timeout-manifest.json"
    result_path = tmp_path / "timeout-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeTimeoutSuite",
                        "path": "res://test/timeout_suite.gd",
                        "tests": [
                            {
                                "name": "test_hangs",
                                "timeout_seconds": 0.05,
                            }
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["tests"][0]["status"] == "timeout"
    assert payload["tests"][0]["duration_seconds"] < 1.0


def test_native_runner_retries_failed_test_with_fresh_instance(
    godot_bin, tmp_path
):
    """Retry settings create a fresh attempt and report the attempt count."""
    project = _prepare_project(tmp_path, godot_bin)
    retry_script = project / "test" / "retry_suite.gd"
    # Count attempts through a marker file instead of a script static var:
    # Godot 4.7 intermittently crashes on exit (0xC0000005) when a suite
    # script declares a static var, which would make the process exit code
    # disagree with the passing result.
    retry_script.write_text(
        "extends GdToolsTest\n"
        "\n\n"
        'const MARKER := "res://.retry_attempted"\n'
        "\n\n"
        "func test_retry() -> void:\n"
        "    if FileAccess.file_exists(MARKER):\n"
        "        DirAccess.remove_absolute(MARKER)\n"
        "        assert_true(true)\n"
        "    else:\n"
        "        var marker := FileAccess.open(MARKER, FileAccess.WRITE)\n"
        '        marker.store_line("attempted")\n'
        "        marker.close()\n"
        '        assert_true(false, "first attempt fails")\n',
        encoding="utf-8",
    )
    suite = NativeSuite(
        name="NativeRetrySuite",
        path="res://test/retry_suite.gd",
        tests=[NativeTest(name="test_retry", retries=1)],
    )

    result = run_native_tests(
        project,
        [suite],
        godot_bin,
        work_dir=tmp_path / "retry-orchestrated",
    )

    assert result.status == "passed"
    assert len(result.tests) == 1
    assert result.tests[0].status == "passed"
    assert result.tests[0].attempts == 2


def test_native_runner_supports_async_helpers(godot_bin, tmp_path):
    """Native tests can await process, physics, timer, and signal events."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "async-manifest.json"
    result_path = tmp_path / "async-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeAsyncHelpersSuite",
                        "path": "res://test/async_helpers_suite.gd",
                        "tests": [
                            {"name": "test_process_frame"},
                            {"name": "test_physics_frames"},
                            {"name": "test_timer"},
                            {"name": "test_signal"},
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert len(payload["tests"]) == 4
    assert all(test["status"] == "passed" for test in payload["tests"])


BOUNDED_WAIT_METHODS = [
    "test_wait_for_signal_true_when_emitted",
    "test_wait_for_signal_false_when_never_emitted",
    "test_wait_for_signal_default_budget_when_emitted",
    "test_wait_for_signal_records_no_own_failure",
    "test_wait_for_signal_resolves_before_budget",
]


def test_native_wait_for_signal_is_bounded(godot_bin, tmp_path):
    """A signal wait returns a real bool, resolves early, and records nothing."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest_path = tmp_path / "bounded-wait-manifest.json"
    result_path = tmp_path / "bounded-wait-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeAsyncHelpersSuite",
                        "path": "res://test/async_helpers_suite.gd",
                        "tests": [
                            # Generous per-test budget so a wait that blocked for
                            # its whole 15s window would finish and be reported
                            # rather than being cut short as a timeout.
                            {"name": name, "timeout_seconds": 60.0}
                            for name in BOUNDED_WAIT_METHODS
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert len(payload["tests"]) == len(BOUNDED_WAIT_METHODS)
    assert all(test["status"] == "passed" for test in payload["tests"])

    by_name = {test["name"]: test for test in payload["tests"]}
    early = by_name["test_wait_for_signal_resolves_before_budget"]
    assert early["duration_seconds"] < 5.0, (
        "wait_for_signal blocked for its whole budget instead of resolving "
        f"when the signal fired: {early['duration_seconds']}s"
    )


def _run_suite_timeout_manifest(project, godot_bin, tmp_path, tag, test_specs):
    """Run one manifest over the suite-timeout fixture and return the payload."""
    manifest_path = tmp_path / f"{tag}-manifest.json"
    result_path = tmp_path / f"{tag}-result.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeSuiteTimeoutSuite",
                        "path": "res://test/suite_timeout_suite.gd",
                        "tests": [
                            {"name": name, "timeout_seconds": timeout}
                            for name, timeout in test_specs
                        ],
                    }
                ],
                "coverage": {"enabled": False},
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )
    # 0 pass, 1 test/coverage failure, 2 environment or engine failure. This
    # helper must not require 0: a starved `before_all` legitimately produces
    # exit 1, and treating that as an infrastructure error would hide the very
    # failure the test is looking for.
    assert result.returncode in (0, 1), result.stdout + result.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    # The runner reports hook outcomes as synthetic entries in `tests`
    # (`before_all` appears there with its own status), so the count is not
    # the number of declared tests. Require every declared name instead --
    # that still catches a suite that failed to load, which reports an empty
    # list, without depending on how hooks are surfaced.
    declared = {name for name, _ in test_specs}
    reported = {test.get("name") for test in payload["tests"]}
    assert (
        declared <= reported
    ), f"runner did not report every declared test: missing {declared - reported}"
    return payload


SUITE_TIMEOUT_PROBE = "test_before_all_really_completed"


def test_native_suite_budget_ignores_declaration_order(godot_bin, tmp_path):
    """The suite budget is the maximum declared timeout, not the first one."""
    project = _prepare_project(tmp_path, godot_bin)

    # Same multiset of timeouts, opposite order. `_suite_timeout` returns
    # inside its first loop iteration, so the smallest-first run gets a
    # budget too small for `before_all` and the largest-first run does not.
    # Asserting the two agree is what distinguishes a real fix (max across
    # all tests) from a re-ordering that merely moves the symptom.
    small_first = _run_suite_timeout_manifest(
        project,
        godot_bin,
        tmp_path,
        "small-first",
        [
            ("test_first_short_budget", 0.2),
            ("test_second_long_budget", 5.0),
            (SUITE_TIMEOUT_PROBE, 5.0),
        ],
    )
    large_first = _run_suite_timeout_manifest(
        project,
        godot_bin,
        tmp_path,
        "large-first",
        [
            ("test_second_long_budget", 5.0),
            ("test_first_short_budget", 0.2),
            (SUITE_TIMEOUT_PROBE, 5.0),
        ],
    )

    def probe_outcome(payload):
        by_name = {test["name"]: test for test in payload["tests"]}
        return by_name[SUITE_TIMEOUT_PROBE]["status"]

    assert probe_outcome(small_first) == "passed", (
        "before_all was starved by the first test's declared budget; the "
        "suite budget must be the maximum across all tests"
    )
    assert probe_outcome(small_first) == probe_outcome(large_first)


def test_native_empty_suite_keeps_default_budget(godot_bin, tmp_path):
    """An empty suite still gets the default budget, not a zero floor."""
    project = _prepare_project(tmp_path, godot_bin)

    payload = _run_suite_timeout_manifest(
        project, godot_bin, tmp_path, "empty", []
    )

    # An empty suite produces no test results, so there is nothing in the
    # payload to assert on. `before_all` sleeps past the 0.001 floor, so it
    # only writes its marker if the empty-suite fallback is still the
    # documented 5.0. Asserting on the marker is a real observation; a
    # `status == "passed"` check here would pass either way.
    assert payload["status"] == "passed"
    # Only the synthetic `before_all` hook entry; no test method ran.
    reported = {test.get("name") for test in payload["tests"]}
    assert not any(
        name.startswith("test_") for name in reported
    ), f"an empty suite ran test methods: {reported}"
    assert (
        project / "suite_timeout_completed.log"
    ).exists(), (
        "before_all did not complete; the empty-suite budget is no longer 5.0"
    )


def test_native_orchestrator_runs_multiple_real_suites(godot_bin, tmp_path):
    """The Python orchestrator aggregates isolated real Godot processes."""
    project = _prepare_project(tmp_path, godot_bin)
    suites = [
        NativeSuite(
            name="NativeFixtureSuite",
            path="res://test/native_suite.gd",
            tests=[NativeTest(name="test_pass")],
        ),
        NativeSuite(
            name="NativeAsyncHelpersSuite",
            path="res://test/async_helpers_suite.gd",
            tests=[NativeTest(name="test_process_frame")],
        ),
    ]

    result = run_native_tests(
        project,
        suites,
        godot_bin,
        work_dir=tmp_path / "orchestrated",
    )

    assert result.status == "passed"
    assert len(result.tests) == 2
    assert {test.suite for test in result.tests} == {
        "NativeFixtureSuite",
        "NativeAsyncHelpersSuite",
    }
    assert all(test.status == "passed" for test in result.tests)


def test_native_orchestrator_continues_after_process_crash(godot_bin, tmp_path):
    """A crashed suite is recorded without hiding later suite results."""
    project = _prepare_project(tmp_path, godot_bin)
    crash_script = project / "test" / "native_crash_suite.gd"
    crash_script.write_text(
        "extends GdToolsTest\n\n\n"
        "func test_crashes_process() -> void:\n"
        '    OS.crash("intentional native crash")\n',
        encoding="utf-8",
    )
    suites = [
        NativeSuite(
            name="NativeCrashSuite",
            path="res://test/native_crash_suite.gd",
            tests=[NativeTest(name="test_crashes_process")],
        ),
        NativeSuite(
            name="NativeFixtureSuite",
            path="res://test/native_suite.gd",
            tests=[NativeTest(name="test_pass")],
        ),
    ]

    result = run_native_tests(
        project,
        suites,
        godot_bin,
        work_dir=tmp_path / "crash-orchestrated",
    )

    assert result.status == "error"
    assert any(
        test.suite == "NativeCrashSuite" and test.status == "error"
        for test in result.tests
    )
    assert any(
        test.suite == "NativeFixtureSuite" and test.status == "passed"
        for test in result.tests
    )


def test_native_command_runs_real_suite_and_writes_junit(
    godot_bin, tmp_path, monkeypatch
):
    """The native CLI adapter runs a real suite and produces JUnit output."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )
    junit_path = tmp_path / "native-results.xml"

    result = run_native_test_command(
        config,
        suite="NativeFixtureSuite",
        junit_xml=str(junit_path),
        timeout=30,
    )

    assert result.total == 2
    assert result.failed == 0
    assert result.junit_xml_path == junit_path
    assert junit_path.is_file()
    assert "test_pass" in junit_path.read_text(encoding="utf-8")


def test_native_command_runs_plain_suite_through_preflight(
    godot_bin, tmp_path, monkeypatch
):
    """Plain native suites pass through preflight with default headless mode."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )
    junit_path = tmp_path / "plain-results.xml"

    result = run_native_test_command(
        config,
        suite="NativeFixtureSuite",
        test_name="test_pass",
        tags=["smoke"],
        junit_xml=str(junit_path),
        timeout=30,
    )

    assert (result.total, result.passed, result.failed) == (1, 1, 0)
    junit = junit_path.read_text(encoding="utf-8")
    assert "test_pass" in junit
    assert "test_async" not in junit

    run_dirs = [
        path
        for path in (project / ".gd-tools" / "artifacts").iterdir()
        if path.is_dir()
    ]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    preflight_result = json.loads(
        (run_dir / "preflight" / "preflight.result.json").read_text(
            encoding="utf-8"
        )
    )
    assert preflight_result["status"] == "ok"
    assert preflight_result["suites"][0]["integration"] == {
        "scene": None,
        "resources": {},
        "mode": "headless",
    }
    assert preflight_result["suites"][0]["tests"][0]["integration"] == {
        "scene": None,
        "resources": {},
    }

    suite_manifest = json.loads(
        (run_dir / "native" / "suite-0000.manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert suite_manifest["suites"][0]["integration"]["mode"] == "headless"
    suite_result = json.loads(
        (run_dir / "native" / "suite-0000.result.json").read_text(
            encoding="utf-8"
        )
    )
    assert suite_result["run_id"] == run_dir.name
    assert [test["name"] for test in suite_result["tests"]] == ["test_pass"]


@pytest.mark.e2e_smoke
def test_native_command_runs_real_coverage(godot_bin, tmp_path, monkeypatch):
    """The native CLI adapter reuses the existing coverage report pipeline."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )

    result = run_native_test_command(
        config,
        suite="NativeCoverageSuite",
        coverage=True,
        timeout=30,
    )

    assert result.failed == 0
    assert result.coverage_data_path is not None
    assert result.coverage_data_path.is_file()
    assert (project / ".gd-tools" / "coverage" / "plan.json").is_file()


def test_native_runner_collects_line_and_branch_coverage(godot_bin, tmp_path):
    """Native coverage records statement and branch hits without GUT."""
    project = _prepare_project(tmp_path, godot_bin)
    plan_path = tmp_path / "native-plan.json"
    coverage_path = tmp_path / "native-coverage.json"
    result_path = tmp_path / "coverage-result.json"
    plan_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_by": "gd-tools-test",
                "files": [
                    {
                        "file_id": 0,
                        "path": "res://scripts/coverage_subject.gd",
                        "source_hash": "sha256:test",
                        "lines": [
                            {
                                "line": 5,
                                "id": 0,
                                "type": "branch",
                                "branch_type": "if_true",
                            },
                            {
                                "line": 6,
                                "id": 1,
                                "type": "statement",
                                "branch_type": None,
                            },
                            {
                                "line": 7,
                                "id": 2,
                                "type": "branch",
                                "branch_type": "if_false",
                            },
                            {
                                "line": 8,
                                "id": 3,
                                "type": "statement",
                                "branch_type": None,
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "coverage-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeCoverageSuite",
                        "path": "res://test/coverage_suite.gd",
                        "tests": [
                            {"name": "test_statement_and_branch_coverage"}
                        ],
                    }
                ],
                "coverage": {
                    "enabled": True,
                    "plan_path": str(plan_path),
                    "output_path": str(coverage_path),
                },
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GD_TOOLS_NATIVE_MANIFEST"] = str(manifest_path)
    env["GD_TOOLS_NATIVE_RESULT"] = str(result_path)
    result = subprocess.run(
        [
            godot_bin,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://addons/gd-tools-test/gd_tools_test_runner.gd",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert coverage_path.is_file()
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    assert coverage["version"] == 1
    assert coverage["files"][0]["file_id"] == 0
    hits = coverage["files"][0]["hits"]
    assert hits["0"] > 0
    assert hits["1"] > 0
    assert hits["2"] > 0
    assert hits["3"] > 0


def test_native_coverage_warns_and_continues_past_uninstrumentable_target(
    godot_bin, tmp_path
):
    """A target that cannot be instrumented warns, is skipped, and the rest run.

    Covers spec R1, R2, R3, and R4 in one Godot spawn. Three distinct defects
    are combined in a single plan so the per-spawn flake cost stays low:

    * ``missing_target.gd`` does not exist, so ``load()`` returns null. This is
      a stale plan, and R4 requires a message that says so.
    * ``never_called.gd`` loads and is instrumented successfully but is never
      executed. R3 requires it to appear with an empty ``hits`` object, which
      is what makes ``files[]`` the *instrumented set* rather than the hit set.
      Without that entry an instrumented-but-unexercised file is
      indistinguishable from one that could not be instrumented at all.
    * ``coverage_subject.gd`` is executed normally and must still be reported
      with real hit counts.

    R2 is the sharpest regression here. ``activate()`` used to return on the
    first failing target, leaving ``_active`` false, so ``write()`` bailed out
    and the coverage file was never written at all -- one uncompilable script
    cost the project its entire coverage. R1 is asserted via ``engine_errors``:
    a per-target problem must be a WARNING, never an ERROR, or the runner's
    error promotion escalates the whole run to exit 2.
    """
    project = _prepare_project(tmp_path, godot_bin)
    (project / "scripts" / "never_called.gd").write_text(
        "extends RefCounted\n\n\nfunc unused() -> int:\n\treturn 1\n",
        encoding="utf-8",
    )

    plan_path = tmp_path / "native-plan.json"
    coverage_path = tmp_path / "native-coverage.json"
    result_path = tmp_path / "omission-result.json"
    log_path = tmp_path / "omission.log"
    plan_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_by": "gd-tools-test",
                "files": [
                    {
                        "file_id": 0,
                        "path": "res://scripts/coverage_subject.gd",
                        "source_hash": "sha256:test",
                        "lines": [
                            {
                                "line": 5,
                                "id": 0,
                                "type": "branch",
                                "branch_type": "if_true",
                            },
                            {
                                "line": 6,
                                "id": 1,
                                "type": "statement",
                                "branch_type": None,
                            },
                        ],
                    },
                    {
                        "file_id": 1,
                        "path": "res://scripts/missing_target.gd",
                        "source_hash": "sha256:test",
                        "lines": [{"line": 1, "id": 0, "type": "statement"}],
                    },
                    {
                        "file_id": 2,
                        "path": "res://scripts/never_called.gd",
                        "source_hash": "sha256:test",
                        "lines": [{"line": 5, "id": 0, "type": "statement"}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "omission-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeCoverageSuite",
                        "path": "res://test/coverage_suite.gd",
                        "tests": [
                            {"name": "test_statement_and_branch_coverage"}
                        ],
                    }
                ],
                "coverage": {
                    "enabled": True,
                    "plan_path": str(plan_path),
                    "output_path": str(coverage_path),
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run_native_manifest(
        project,
        godot_bin,
        json.loads(manifest_path.read_text(encoding="utf-8")),
        result_path,
        log_path=log_path,
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    # R1: a per-target problem is a warning, so the run is not escalated.
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["engine_errors"] == [], payload["engine_errors"]

    # R2: the collector continued past the bad target, so coverage was written
    # at all. Before R2 this file did not exist.
    assert coverage_path.is_file(), (
        "the collector aborted on the first uninstrumentable target, so no "
        "coverage was written for any file"
    )
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    by_id = {entry["file_id"]: entry["hits"] for entry in coverage["files"]}

    # The executed subject still reports real hits.
    assert by_id[0]["0"] > 0, by_id[0]
    assert by_id[0]["1"] > 0, by_id[0]

    # R3: instrumented but never executed -> present with an empty hits object.
    # Absent before R3, which made it indistinguishable from file_id 1.
    assert 2 in by_id, "instrumented-but-unexecuted target missing from files[]"
    assert by_id[2] == {}, by_id[2]

    # R3: the uninstrumentable target must NOT appear -- that is what the
    # absence of file_id 1 tells us, now that 2's presence is meaningful.
    assert 1 not in by_id, "an uninstrumentable target must not be reported"

    # R4: the message must name the file and point at a stale plan rather than
    # at gd-tools' own instrumentation.
    combined = result.stdout + result.stderr
    assert "missing_target.gd" in combined, combined
    assert "plan" in combined, combined

    # R5: the additive `omitted` key carries the reason the collector itself
    # derived, so the terminal report never has to guess it back.
    assert coverage["omitted"] == [
        {
            "file_id": 1,
            "path": "res://scripts/missing_target.gd",
            "reason": (
                "The coverage plan references a file that no longer exists: "
                "res://scripts/missing_target.gd"
            ),
            "fix": "The plan is stale. Re-run with --no-cache to regenerate it.",
        }
    ], coverage.get("omitted")

    # AC 9 / R5: the omission reaches the run result through the existing
    # channels -- a warning line and the structured diagnostics dict -- with
    # the protocol version unchanged.
    assert payload["protocol_version"] == 3
    assert any(
        "missing_target.gd" in warning for warning in payload["engine_warnings"]
    ), payload["engine_warnings"]
    assert payload["diagnostics"]["coverage_omissions"] == coverage["omitted"]


def test_native_coverage_demotes_activation_engine_errors_when_target_fails_to_load(
    godot_bin, tmp_path
):
    """A target that loads badly warns and continues; the run still exits 0.

    Covers the load-failure omission class (spec §1.3 calls it the important
    case). ``broken.gd`` exists and parses, but ``preload()`` points at a file
    that does not exist, so the collector's ``load()``/``reload()`` fails and
    Godot *itself* prints ``SCRIPT ERROR:`` and ``ERROR:`` lines into the log
    while the collector attempts instrumentation. The runner must demote those
    activation-window errors to warnings -- they are the omission's evidence,
    not a run failure -- or `:729` escalates the whole run to exit 2 even
    though the collector behaved correctly. Legacy (GUT) exits 0 for the same
    scenario, and the two runtimes must agree.
    """
    project = _prepare_project(tmp_path, godot_bin)
    (project / "scripts" / "broken.gd").write_text(
        'const Gone = preload("res://scripts/gone.gd")\n\n\n'
        "func triple(value: int) -> int:\n\treturn value * 3\n",
        encoding="utf-8",
    )

    plan_path = tmp_path / "loadfail-plan.json"
    coverage_path = tmp_path / "loadfail-coverage.json"
    result_path = tmp_path / "loadfail-result.json"
    log_path = tmp_path / "loadfail.log"
    plan_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_by": "gd-tools-test",
                "files": [
                    {
                        "file_id": 0,
                        "path": "res://scripts/coverage_subject.gd",
                        "source_hash": "sha256:test",
                        "lines": [
                            {
                                "line": 5,
                                "id": 0,
                                "type": "branch",
                                "branch_type": "if_true",
                            },
                            {
                                "line": 6,
                                "id": 1,
                                "type": "statement",
                                "branch_type": None,
                            },
                        ],
                    },
                    {
                        "file_id": 1,
                        "path": "res://scripts/broken.gd",
                        "source_hash": "sha256:test",
                        "lines": [{"line": 5, "id": 0, "type": "statement"}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "loadfail-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol_version": 3,
                "project_root": str(project),
                "runtime": "native",
                "suites": [
                    {
                        "name": "NativeCoverageSuite",
                        "path": "res://test/coverage_suite.gd",
                        "tests": [
                            {"name": "test_statement_and_branch_coverage"}
                        ],
                    }
                ],
                "coverage": {
                    "enabled": True,
                    "plan_path": str(plan_path),
                    "output_path": str(coverage_path),
                },
            }
        ),
        encoding="utf-8",
    )

    result = _run_native_manifest(
        project,
        godot_bin,
        json.loads(manifest_path.read_text(encoding="utf-8")),
        result_path,
        log_path=log_path,
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))

    # R1: instrumentation-attributable engine output is demoted, so the run
    # is not escalated. Before the demotion this exited 2 via :729.
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["engine_errors"] == [], payload["engine_errors"]

    # R2: coverage was still written for the instrumented set.
    assert coverage_path.is_file()
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    by_id = {entry["file_id"]: entry["hits"] for entry in coverage["files"]}
    assert by_id[0]["0"] > 0, by_id[0]

    # R5: the omission declares itself with the broken-script message, not
    # the stale-plan one -- R4 keeps the two causes distinct.
    assert coverage["omitted"] == [
        {
            "file_id": 1,
            "path": "res://scripts/broken.gd",
            "reason": (
                "Trackers could not be injected, so the script did not "
                "reload: res://scripts/broken.gd"
            ),
            "fix": (
                "Fix the script's own syntax, or exclude it from the plan."
            ),
        }
    ], coverage.get("omitted")

    # The demoted engine output lands in the warnings channel.
    assert any(
        "broken.gd" in warning for warning in payload["engine_warnings"]
    ), payload["engine_warnings"]


MOCKING_METHODS = [
    "test_double_returns_instance_extending_target",
    "test_double_accepts_path_string",
    "test_double_unstubbed_variant_method_returns_null",
    "test_double_unstubbed_typed_method_returns_type_default",
    "test_double_does_not_run_real_implementation",
    "test_double_returns_fresh_instance_per_call",
    "test_partial_double_runs_real_implementation",
    "test_partial_double_keeps_side_effects",
]


STUBBING_METHODS = [
    "test_stub_to_return_overrides_double",
    "test_stub_to_return_on_partial_double",
    "test_stub_to_call_super_on_full_double",
    "test_stub_to_call_super_on_partial_runs_real",
    "test_stub_with_exact_arguments_matches_only_those",
    "test_stub_with_any_wildcard_matches_any_value",
    "test_stub_without_arguments_is_default_fallback",
    "test_stub_to_return_null_on_untyped_method",
    "test_stub_to_return_typed_value_on_typed_method",
    "test_stub_applies_only_to_its_own_double",
    "test_stubs_do_not_leak_into_the_next_test",
    "test_double_records_calls_with_arguments",
]


def test_native_stub_matching_and_recording(godot_bin, tmp_path):
    """stub() chains follow the spec's matching precedence and record calls."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "stubbing.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/stubbing_suite.gd",
            STUBBING_METHODS,
            "NativeStubbingSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(STUBBING_METHODS), payload["tests"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


CALL_ASSERTION_METHODS = [
    "test_assert_called_passes_after_a_call",
    "test_assert_not_called_passes_without_calls",
    "test_assert_call_count_matches_exact_number_of_calls",
    "test_assert_call_arguments_matches_recorded_arguments",
    "test_assert_call_arguments_checks_specific_call_index",
    "test_assertions_count_methods_independently",
    "test_assert_called_failure_diagnostic_names_method",
    "test_assert_not_called_failure_diagnostic_shows_count",
    "test_assert_call_count_failure_diagnostic_shows_expected_and_actual",
    "test_assert_call_arguments_failure_diagnostic_shows_both_argument_sets",
    "test_assertions_read_the_call_recorder_not_script_state",
    "test_assertion_on_a_null_target_fails_cleanly",
]


def test_native_call_assertions(godot_bin, tmp_path):
    """assert_called*/assert_call_* assertions read recorded double calls."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "call-assertions.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/call_assertion_suite.gd",
            CALL_ASSERTION_METHODS,
            "NativeCallAssertionSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(CALL_ASSERTION_METHODS), payload[
        "tests"
    ]
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


VALIDATION_METHODS = [
    "test_stub_on_nonexistent_method_fails_the_test",
    "test_stub_on_a_partial_double_missing_method_fails_the_test",
    "test_stub_requires_a_double",
    "test_double_on_a_non_script_value_fails_the_test",
    "test_partial_double_on_a_non_script_value_fails_the_test",
]


def test_native_mock_fail_fast_validation(godot_bin, tmp_path):
    """Invalid mocking usage fails the test immediately with diagnostics."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "validation.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/validation_suite.gd",
            VALIDATION_METHODS,
            "NativeValidationSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(VALIDATION_METHODS), payload["tests"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def test_native_double_and_partial_double_semantics(godot_bin, tmp_path):
    """double()/partial_double() follow GUT semantics for unstubbed calls."""
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "mocking.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        _manifest(
            project,
            "res://test/mocking_suite.gd",
            MOCKING_METHODS,
            "NativeMockingSuite",
        ),
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(payload["tests"]) == len(MOCKING_METHODS), payload["tests"]
    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "passed"
    for entry in payload["tests"]:
        assert entry["status"] == "passed", (entry["name"], entry["message"])


def _parameters_manifest(project, path, suite_name, tests):
    """Build a manifest whose tests carry preflight-resolved parameter metadata."""
    manifest = _manifest(project, path, [], suite_name)
    manifest["suites"][0]["tests"] = tests
    return manifest


def test_native_runner_expands_parameterized_cases(godot_bin, tmp_path):
    """Each value set becomes a first-class case with its own result entry.

    Cases run in declaration order, each with its own lifecycle hooks, and
    a failing case fails only itself.
    """
    project = _prepare_project(tmp_path, godot_bin)
    manifest = _parameters_manifest(
        project,
        "res://test/parameterize_suite.gd",
        "ParameterizeSuite",
        [
            {
                "name": "test_ranked",
                "parameters": {
                    "names": ["value", "label"],
                    "values": [[1, "admin"], [2, "user"]],
                },
            },
            {"name": "test_plain"},
        ],
    )
    result_path = tmp_path / "result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    names = [entry["name"] for entry in payload["tests"]]
    assert names == [
        "test_ranked[1-admin]",
        "test_ranked[2-user]",
        "test_plain",
    ]
    statuses = {entry["name"]: entry["status"] for entry in payload["tests"]}
    assert statuses["test_ranked[1-admin]"] == "passed"
    assert statuses["test_ranked[2-user]"] == "failed"
    assert statuses["test_plain"] == "passed"


def test_native_runner_parameterizes_async_methods_and_unstable_values(
    godot_bin, tmp_path
):
    """Async methods parameterize identically; unstable values use indexes."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = _parameters_manifest(
        project,
        "res://test/parameterize_suite.gd",
        "ParameterizeSuite",
        [
            {
                "name": "test_async_value",
                "parameters": {
                    "names": ["value", "label"],
                    "values": [[1, "a"], [2, "b"]],
                },
            },
            {
                "name": "test_payload",
                "parameters": {
                    "names": ["payload"],
                    "values": [[{"a": 1}], [{"b": 2}]],
                },
            },
        ],
    )
    result_path = tmp_path / "result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in payload["tests"]]
    assert names == [
        "test_async_value[1-a]",
        "test_async_value[2-b]",
        "test_payload[0]",
        "test_payload[1]",
    ]
    assert all(entry["status"] == "passed" for entry in payload["tests"])


def test_native_runner_expands_use_parameters_cases(godot_bin, tmp_path):
    """use_parameters cases resolve the current value inside the test body."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = _parameters_manifest(
        project,
        "res://test/use_parameters_suite.gd",
        "UseParametersSuite",
        [
            {
                "name": "test_item",
                "parameters": {
                    "names": ["value"],
                    "values": [["alpha"], ["beta"]],
                },
            },
            {
                "name": "test_flag",
                "parameters": {
                    "names": ["value"],
                    "values": [["on"], ["off"]],
                },
            },
        ],
    )
    result_path = tmp_path / "result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 1, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    names = [entry["name"] for entry in payload["tests"]]
    assert names == [
        "test_item[alpha]",
        "test_item[beta]",
        "test_flag[on]",
        "test_flag[off]",
    ]
    statuses = {entry["name"]: entry["status"] for entry in payload["tests"]}
    assert statuses["test_item[alpha]"] == "passed"
    assert statuses["test_item[beta]"] == "failed"
    assert statuses["test_flag[on]"] == "passed"
    assert statuses["test_flag[off]"] == "passed"


def test_native_runner_skips_parameterized_test_without_values(
    godot_bin, tmp_path
):
    """An empty values list marks the test skipped with an explicit reason."""
    project = _prepare_project(tmp_path, godot_bin)
    manifest = _parameters_manifest(
        project,
        "res://test/parameterize_suite.gd",
        "ParameterizeSuite",
        [
            {
                "name": "test_ranked",
                "parameters": {"names": ["value", "label"], "values": []},
            },
        ],
    )
    result_path = tmp_path / "result.json"

    process = _run_native_manifest(project, godot_bin, manifest, result_path)

    assert process.returncode == 0, process.stdout + process.stderr
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert len(payload["tests"]) == 1
    entry = payload["tests"][0]
    assert entry["name"] == "test_ranked"
    assert entry["status"] == "skipped"
    assert "No parameter values declared" in entry["message"]


def test_native_command_selects_single_parameterized_case(
    godot_bin, tmp_path, monkeypatch
):
    """``--test name[case]`` runs exactly the matching case end to end."""
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )
    junit_path = tmp_path / "case-results.xml"

    result = run_native_test_command(
        config,
        suite="NativeParameterizeSuite",
        test_name="test_ranked[1-admin]",
        tags=[],
        junit_xml=str(junit_path),
        timeout=30,
    )

    assert (result.total, result.passed, result.failed) == (1, 1, 0)
    junit = junit_path.read_text(encoding="utf-8")
    assert "test_ranked[1-admin]" in junit
    assert "test_ranked[2-user]" not in junit
    assert "test_plain" not in junit


def test_native_command_covers_parameterized_cases(
    godot_bin, tmp_path, monkeypatch
):
    """Coverage data is produced for a run containing parameterized cases.

    Coverage is aggregated per source line across the whole run, so every
    case of a parameterized method contributes hits without per-case
    attribution plumbing. The suite deliberately includes failing cases.
    """
    project = _prepare_project(tmp_path, godot_bin)
    monkeypatch.chdir(project)
    config = GdToolsConfig(
        godot=GodotConfig(binary=godot_bin),
        test=TestConfig(test_dirs=["test"]),
    )

    result = run_native_test_command(
        config,
        suite="NativeParameterizeSuite",
        coverage=True,
        no_exit_code=True,
        timeout=30,
    )

    # test_ranked[2-user] fails by design.
    assert (result.total, result.passed, result.failed) == (7, 6, 1), result
    assert result.coverage_data_path is not None
    assert result.coverage_data_path.is_file()
    payload = json.loads(result.coverage_data_path.read_text(encoding="utf-8"))
    assert payload.get("files"), payload


def test_native_suite_skip_in_before_all_skips_every_test(godot_bin, tmp_path):
    """skip_test() in before_all marks every suite test skipped with the reason.

    Per-test entries are still produced (including each expanded
    parameterized case), no test body or hook ever runs, and a skip
    consumes no retry.
    """
    project = _prepare_project(tmp_path, godot_bin)
    result_path = tmp_path / "suite-skip-result.json"
    result = _run_native_manifest(
        project,
        godot_bin,
        {
            "protocol_version": 3,
            "project_root": str(project),
            "runtime": "native",
            "suites": [
                {
                    "name": "NativeSuiteSkipSuite",
                    "path": "res://test/suite_skip_suite.gd",
                    "tests": [
                        {"name": "test_skipped_by_suite", "retries": 3},
                        {
                            "name": "test_async_case",
                            "retries": 3,
                            "parameters": {
                                "names": ["value"],
                                "values": [[1], [2]],
                            },
                        },
                    ],
                }
            ],
            "coverage": {"enabled": False},
        },
        result_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    entries = payload["tests"]
    by_name = {test["name"]: test for test in entries}

    assert result.returncode == 0, result.stdout + result.stderr
    assert by_name["test_skipped_by_suite"]["status"] == "skipped"
    assert by_name["test_async_case[1]"]["status"] == "skipped"
    assert by_name["test_async_case[2]"]["status"] == "skipped"
    for entry in entries:
        assert entry["message"] == "suite environment unavailable"
        # A suite-level skip is terminal and never consumes a retry.
        assert entry["attempts"] == 1
    # Test bodies and hooks must never have run.
    assert not (project / "suite_skip_hook_ran.txt").exists()
