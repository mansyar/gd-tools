"""Format runner module for gd-tools.

Wraps ``gdformat`` (via the gdtoolkit Python API) with config-driven
excludes and clean, formatted output. Discovers ``.gd`` files,
invokes the formatter programmatically, and returns structured results.
"""

import difflib
import time
from dataclasses import dataclass, field

import click
from gdtoolkit.formatter import format_code
from lark.exceptions import LarkError

from gd_tools import output
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
        files_skipped: Number of files skipped due to I/O or
            syntax errors.
        diffs: List of unified diff strings for files that differ.
            Only populated in --diff mode.
    """

    files_checked: int = 0
    files_formatted: int = 0
    files_needing_format: int = 0
    files_needing_format_paths: list[str] = field(default_factory=list)
    files_skipped: int = 0
    diffs: list[str] = field(default_factory=list)


def run_format(
    config: GdToolsConfig,
    paths: list[str] | None = None,
    check: bool = False,
    diff: bool = False,
) -> FormatResult:
    """Format ``.gd`` files in ``paths`` using the gdtoolkit formatter.

    Args:
        config: Project configuration with format excludes.
        paths: Root directories to search for .gd files. Defaults to
            ``["."]``.
        check: If True, report files needing format without modifying.
        diff: If True, show unified diffs without modifying.

    Returns:
        FormatResult with counts and diffs.

    Raises:
        FormatError: If both check and diff are True (mutually exclusive).
    """
    if not paths:
        paths = ["."]

    if check and diff:
        raise FormatError(
            "--check and --diff are mutually exclusive",
            exit_code=2,
        )

    excludes = config.format.exclude
    gd_files: list[str] = []
    for p in paths:
        gd_files.extend(discover_gd_files(p, excludes))
    gd_files = list(dict.fromkeys(gd_files))

    if not gd_files:
        return FormatResult()

    files_checked = len(gd_files)
    files_formatted = 0
    files_needing_format = 0
    files_needing_format_paths: list[str] = []
    files_skipped = 0
    diffs_list: list[str] = []

    start_time = time.perf_counter()
    for file_path in gd_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            output.print_verbose(f"Formatting: {file_path}")
            formatted_code = format_code(
                original_code,
                max_line_length=config.format.max_line_length,
            )

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
        except LarkError as e:
            # Syntax error: report file path and description, then skip
            click.echo(f"Warning: Skipping {file_path}: {e}", err=True)
            files_skipped += 1
            continue
        except (OSError, UnicodeDecodeError) as e:
            click.echo(f"Warning: Skipping {file_path}: {e}", err=True)
            files_skipped += 1
            continue

    elapsed = time.perf_counter() - start_time
    output.print_verbose(f"Elapsed: {elapsed:.2f}s")

    return FormatResult(
        files_checked=files_checked - files_skipped,
        files_formatted=files_formatted,
        files_needing_format=files_needing_format,
        files_needing_format_paths=files_needing_format_paths,
        files_skipped=files_skipped,
        diffs=diffs_list,
    )
