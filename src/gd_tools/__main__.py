"""Module entry point for gd-tools.

Allows running gd-tools via ``python -m gd_tools``.
"""

import sys

from .cli import cli
from .errors import GdToolsError


def main() -> None:
    """Run the gd-tools CLI.

    Calls the Click CLI group and catches any :class:`GdToolsError`,
    printing the error message to stderr and exiting with the
    exception's ``exit_code``.

    Raises:
        SystemExit: When the CLI exits or a :class:`GdToolsError` is
            caught.
    """
    try:
        cli()
    except GdToolsError as e:
        print(str(e), file=sys.stderr)
        sys.exit(e.exit_code)


if __name__ == "__main__":
    main()
