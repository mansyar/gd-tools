"""Flaky test classification for native test runs.

A test is *flaky* when it ultimately reported ``passed`` but required more
than one attempt (pytest-rerunfailures semantics).  The helpers here are a
pure derivation over a :class:`NativeRunResult`; rendering the terminal
panel lives with the reporters.
"""

from dataclasses import dataclass

from gd_tools.native_test.protocol import NativeRunResult


@dataclass(frozen=True)
class FlakyTest:
    """One test that passed only after a retry."""

    suite: str
    name: str
    attempts: int
    first_failure_message: str


def collect_flaky_tests(run_result: NativeRunResult) -> list[FlakyTest]:
    """Return the run's flaky tests in run order.

    A test qualifies when its final status is ``passed`` and it needed more
    than one attempt.  Non-passing outcomes are never flaky, regardless of
    how many attempts were made.

    Args:
        run_result: The parsed native run result.

    Returns:
        The flaky tests, ordered as they appear in the run result.
    """
    return [
        FlakyTest(
            suite=result.suite,
            name=result.name,
            attempts=result.attempts,
            first_failure_message=result.first_failure_message,
        )
        for result in run_result.tests
        if result.status == "passed" and result.attempts > 1
    ]