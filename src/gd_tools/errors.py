"""Exception hierarchy for gd-tools.

All gd-tools exceptions inherit from :class:`GdToolsError`, which carries an
``exit_code`` attribute.  The CLI entry point uses this code when the error
propagates to the top level, so every failure mode maps to a deterministic
process exit code.

Exit-code convention:
    - ``2`` — configuration / environment problems (missing Godot, missing
      GUT, bad config).  These are "fix your setup" errors.
    - ``1`` — tool failures (tests failed, lint found issues, coverage below
      threshold).  These are "your code has a problem" errors.
"""


class GdToolsError(Exception):
    """Base exception for all gd-tools errors.

    Attributes:
        exit_code: The exit code to use when this error causes the
            program to terminate. Defaults to 2 (config error).
    """

    exit_code: int = 2

    def __init__(
        self, message: str = "", *, exit_code: int | None = None
    ) -> None:
        """Initialize the error.

        Args:
            message: The error message.
            exit_code: Override the class default exit code. If None,
                the class-level ``exit_code`` is used. Defaults to None.
        """
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class ConfigError(GdToolsError):
    """Raised when there is a configuration error."""


class GodotNotFoundError(GdToolsError):
    """Raised when the Godot binary cannot be found."""


class GUTNotInstalledError(GdToolsError):
    """Raised when GUT is not installed in the project."""


class CoveragePlanError(GdToolsError):
    """Raised when there is an error generating the coverage plan."""


class CoverageThresholdError(GdToolsError):
    """Raised when coverage falls below the required threshold."""

    exit_code: int = 1


class TestFailureError(GdToolsError):
    """Raised when tests fail."""

    __test__ = False
    exit_code: int = 1


class LintError(GdToolsError):
    """Raised when linting finds issues."""

    exit_code: int = 1


class FormatError(GdToolsError):
    """Raised when formatting issues are found."""

    exit_code: int = 1
