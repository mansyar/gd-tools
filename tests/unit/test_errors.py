"""Tests for the gd_tools exception hierarchy."""

import pytest

from gd_tools.errors import (
    ConfigError,
    CoveragePlanError,
    CoverageThresholdError,
    FormatError,
    GdToolsError,
    GUTNotInstalledError,
    GodotNotFoundError,
    LintError,
    TestFailureError,
)


def test_gd_tools_error_is_exception():
    """Test that GdToolsError is a subclass of Exception."""
    assert issubclass(GdToolsError, Exception)


def test_gd_tools_error_default_exit_code():
    """Test that GdToolsError has a default exit_code of 2."""
    error = GdToolsError("test")
    assert error.exit_code == 2


def test_gd_tools_error_custom_exit_code():
    """Test that GdToolsError accepts a custom exit_code."""
    error = GdToolsError("test", exit_code=1)
    assert error.exit_code == 1


def test_gd_tools_error_message():
    """Test that GdToolsError stores the message."""
    error = GdToolsError("something went wrong")
    assert str(error) == "something went wrong"


@pytest.mark.parametrize(
    "exception_class",
    [
        ConfigError,
        GodotNotFoundError,
        GUTNotInstalledError,
        CoveragePlanError,
    ],
)
def test_config_errors_exit_code_2(exception_class):
    """Test that config-type errors have exit_code 2."""
    error = exception_class("test")
    assert error.exit_code == 2
    assert issubclass(exception_class, GdToolsError)


@pytest.mark.parametrize(
    "exception_class",
    [
        CoverageThresholdError,
        TestFailureError,
        LintError,
        FormatError,
    ],
)
def test_failure_errors_exit_code_1(exception_class):
    """Test that failure-type errors have exit_code 1."""
    error = exception_class("test")
    assert error.exit_code == 1
    assert issubclass(exception_class, GdToolsError)
