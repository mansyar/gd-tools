"""Format runner module for gd-tools.

Wraps ``gdformat`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes the formatter programmatically, and returns structured results.
"""

import difflib
from dataclasses import dataclass, field

from gdtoolkit.formatter import format_code
from lark.exceptions import LarkError

from gd_tools.config import GdToolsConfig
from gd_tools.errors import FormatError
from gd_tools.file_discovery import discover_gd_files


@dataclass
class FormatResult:
    """Result of a format run.

    Attributes:
        files_checked: Total number of .gd files examined.
        files_formatted: Number of files that were reformatted
            (written with changes). Only non-zero in default mode.
        files_needing_format: Number of files whose formatted
            version differs from the original. Non-zero in --check
            and --diff modes.
        files_needing_format_paths: List of file paths that need
            formatting. Only populated in --check mode.
        diffs: List of unified diff strings for files that differ.
            Only populated in --diff mode.
    """

    files_checked: int = 0
    files_formatted: int = 0
    files_needing_format: int = 0
    files_needing_format_paths: list[str] = field(default_factory=list)
    diffs: list[str] = field(default_factory=list)


def run_format(
    config: GdToolsConfig,
    path: str = ".",
    check: bool = False,
    diff: bool = False,
) -> FormatResult:
    """Format ``.gd`` files in ``path`` using the gdtoolkit formatter.

    Args:
        config: Project configuration with format excludes.
        path: Root directory to search for .gd files.
        check: If True, report files needing format without modifying.
        diff: If True, show unified diffs without modifying.

    Returns:
        FormatResult with counts and diffs.

    Raises:
        FormatError: If both check and diff are True (mutually exclusive).
    """
    if check and diff:
        raise FormatError(
            "--check and --diff are mutually exclusive",
            exit_code=2,
        )

    excludes = config.format.exclude
    gd_files = discover_gd_files(path, excludes)

    if not gd_files:
        return FormatResult()

    files_checked = len(gd_files)
    files_formatted = 0
    files_needing_format = 0
    files_needing_format_paths: list[str] = []
    diffs_list: list[str] = []

    for file_path in gd_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            formatted_code = format_code(original_code, max_line_length=100)

            if formatted_code != original_code:
                if check:
                    files_needing_format += 1
                    files_needing_format_paths.append(file_path)
                elif diff:
                    diff_str = "".join(
                        difflib.unified_diff(
                            original_code.splitlines(keepends=True),
                            formatted_code.splitlines(keepends=True),
                            fromfile=file_path,
                            tofile=file_path,
                        )
                    )
                    diffs_list.append(diff_str)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(formatted_code)
                    files_formatted += 1
        except LarkError:
            # Syntax error: skip this file, continue processing
            continue

    return FormatResult(
        files_checked=files_checked,
        files_formatted=files_formatted,
        files_needing_format=files_needing_format,
        files_needing_format_paths=files_needing_format_paths,
        diffs=diffs_list,
    )
