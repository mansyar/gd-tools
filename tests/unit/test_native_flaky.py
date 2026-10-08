"""Unit tests for flaky test classification.

A flaky test is one that ultimately reported ``passed`` but required more
than one attempt (pytest-rerunfailures semantics).  The helper under test
is a pure derivation over a :class:`NativeRunResult`.
"""

import pytest

from gd_tools.native_test.flaky import FlakyTest, collect_flaky_tests
from gd_tools.native_test.protocol import NativeRunResult, NativeTestResult

pytestmark = pytest.mark.unit


def _result(**overrides) -> NativeTestResult:
    """Build a minimal passed single-attempt test result."""
    fields: dict = {
        "suite": "ExampleSuite",
        "name": "test_example",
        "status": "passed",
    }
    fields.update(overrides)
    return NativeTestResult(**fields)


def _run(tests: list[NativeTestResult]) -> NativeRunResult:
    """Build a minimal run result wrapping the given tests."""
    return NativeRunResult(run_id="run-1", status="passed", tests=tests)


def test_passed_after_assertion_recovery_is_flaky():
    """A test that passed on attempt 2 after an assertion failure is flaky."""
    run = _run(
        [
            _result(
                attempts=2,
                message="second attempt passed",
                first_failure_message="expected 1 to be 2",
            )
        ]
    )

    flaky = collect_flaky_tests(run)

    assert flaky == [
        FlakyTest(
            suite="ExampleSuite",
            name="test_example",
            attempts=2,
            first_failure_message="expected 1 to be 2",
        )
    ]


def test_passed_after_timeout_recovery_is_flaky():
    """A test that passed after recovering from a timeout is flaky."""
    run = _run(
        [
            _result(
                attempts=3,
                first_failure_message="Test timed out after 0.500 seconds",
            )
        ]
    )

    flaky = collect_flaky_tests(run)

    assert len(flaky) == 1
    assert flaky[0].attempts == 3
    assert flaky[0].first_failure_message == (
        "Test timed out after 0.500 seconds"
    )


def test_single_attempt_pass_is_not_flaky():
    """A test that passed on its only attempt is not flaky."""
    run = _run([_result(attempts=1)])

    assert collect_flaky_tests(run) == []


def test_non_passed_results_are_never_flaky():
    """Failed, timed out, and skipped tests are never flaky."""
    run = _run(
        [
            _result(name="test_failed", status="failed", attempts=3),
            _result(name="test_timeout", status="timeout", attempts=3),
            _result(name="test_skipped", status="skipped", attempts=3),
            _result(name="test_error", status="error", attempts=3),
        ]
    )

    assert collect_flaky_tests(run) == []


def test_flaky_tests_preserve_run_order():
    """Flaky tests are reported in the order they appear in the run."""
    run = _run(
        [
            _result(name="test_clean", attempts=1),
            _result(name="test_flaky_late", attempts=2),
            _result(name="test_failed", status="failed", attempts=2),
            _result(
                name="test_flaky_early",
                suite="OtherSuite",
                attempts=2,
            ),
        ]
    )

    flaky = collect_flaky_tests(run)

    assert [(entry.suite, entry.name) for entry in flaky] == [
        ("ExampleSuite", "test_flaky_late"),
        ("OtherSuite", "test_flaky_early"),
    ]
