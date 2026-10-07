"""Unit tests for the terminal flaky-test panel.

The panel lists tests that passed only after a retry.  It renders inside
the native run summary whenever at least one flaky test exists, and is
suppressed entirely otherwise (zero flaky tests must not change today's
output).
"""

from io import StringIO

import pytest
from rich.console import Console

from gd_tools import output
from gd_tools.test_results import (
    TestDetail,
    TestResult,
    format_test_results,
)
from gd_tools.verbosity import Verbosity, set_verbosity

pytestmark = pytest.mark.unit


def _detail(**overrides) -> TestDetail:
    """Build a minimal passing single-attempt test detail."""
    fields: dict = {
        "name": "test_example",
        "suite": "ExampleSuite",
        "status": "pass",
        "message": "",
        "duration": 0.1,
    }
    fields.update(overrides)
    return TestDetail(**fields)


def _result(details: list[TestDetail]) -> TestResult:
    """Build a passing run result wrapping the given details."""
    return TestResult(
        total=len(details),
        passed=len(details),
        failed=0,
        skipped=0,
        duration=1.0,
        junit_xml_path=None,
        coverage_data_path=None,
        stdout="",
        stderr="",
        test_details=details,
    )


def _capture(monkeypatch) -> StringIO:
    """Swap the shared console for a wide, non-terminal StringIO."""
    stream = StringIO()
    monkeypatch.setattr(
        output,
        "console",
        Console(file=stream, width=200, force_terminal=False),
    )
    return stream


def test_flaky_panel_lists_suite_name_attempt_and_message(monkeypatch):
    """One flaky test renders a panel with suite, attempt count, message."""
    stream = _capture(monkeypatch)
    result = _result(
        [
            _detail(
                attempts=2,
                first_failure_message="expected 1 to be 2",
            )
        ]
    )

    format_test_results(result)

    text = stream.getvalue()
    assert "Flaky tests" in text
    assert "ExampleSuite.test_example" in text
    assert "passed on attempt 2" in text
    assert "expected 1 to be 2" in text


def test_flaky_panel_collapses_and_truncates_message(monkeypatch):
    """Multi-line messages collapse to a first line truncated at 120."""
    stream = _capture(monkeypatch)
    long_line = "x" * 130
    result = _result(
        [
            _detail(
                attempts=3,
                first_failure_message=long_line + "\nsecond line",
            )
        ]
    )

    format_test_results(result)

    text = stream.getvalue()
    assert ("x" * 119 + "\u2026") in text
    assert "second line" not in text


def test_no_flaky_tests_renders_no_panel(monkeypatch):
    """A run without flaky tests renders no panel at all."""
    stream = _capture(monkeypatch)
    result = _result([_detail(attempts=1)])

    format_test_results(result)

    assert "Flaky tests" not in stream.getvalue()


def test_flaky_panel_suppressed_in_quiet_mode(monkeypatch):
    """QUIET verbosity suppresses the panel like other info output."""
    stream = _capture(monkeypatch)
    set_verbosity(Verbosity.QUIET)
    try:
        result = _result([_detail(attempts=2)])
        format_test_results(result)
    finally:
        set_verbosity(Verbosity.DEFAULT)

    assert "Flaky tests" not in stream.getvalue()


def test_flaky_panel_skips_empty_first_failure_message(monkeypatch):
    """A flaky test without a captured message renders without one."""
    stream = _capture(monkeypatch)
    result = _result([_detail(attempts=2, first_failure_message="")])

    format_test_results(result)

    text = stream.getvalue()
    assert "ExampleSuite.test_example" in text
    assert "passed on attempt 2" in text
