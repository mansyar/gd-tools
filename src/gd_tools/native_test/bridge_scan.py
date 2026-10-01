"""Static detection of GUT constructs the native runtime cannot run.

This catalog previously gated the GUT compatibility bridge (removed in
v0.6.0). It is retained as the construct source for the migration report:
``gd_tools.migration`` scans legacy GUT suites against it so users see
exactly which calls have no native equivalent.
"""

from __future__ import annotations

import re

# Longest names first so regex alternation captures the full construct name
# (``assert_property_with_backing_variable`` rather than ``assert_property``).
#
# Mocking constructs (``double``, ``partial_double``, ``stub``,
# ``assert_called*``) are NOT listed: the native runtime implements them.
# Parameterization (``parameterize``/``use_parameters``) is native now, so it
# is not listed either.
_UNSUPPORTED_NAMES: tuple[str, ...] = sorted(
    (
        # Property, orphan, and interactive assertions.
        "assert_setget",
        "assert_accessors",
        "assert_exports",
        "assert_property",
        "assert_freed",
        "assert_no_new_orphans",
        "pause_before_teardown",
        # Engine error and push diagnostics.
        "assert_engine_error",
        "assert_push_",
    ),
    key=len,
    reverse=True,
)

_UNSUPPORTED_CALL_RE = re.compile(
    rf"(?<![\w.])((?:{'|'.join(re.escape(name) for name in _UNSUPPORTED_NAMES)})"
    r"\w*)\s*\("
)


def find_unsupported_constructs(source: str) -> list[tuple[str, int]]:
    """Return every unsupported construct call in ``source`` with its line."""
    return [
        (match.group(1), source.count("\n", 0, match.start()) + 1)
        for match in _UNSUPPORTED_CALL_RE.finditer(source)
    ]
