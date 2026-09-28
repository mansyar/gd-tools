"""Coverage subsystem package.

Re-exports the orchestrator functions for convenient access:

- :func:`generate_coverage_report`: Regenerate reports from existing data.
- :func:`merge_coverage_files`: Merge multiple coverage data files.
- :func:`show_coverage_summary`: Print terminal summary table.
"""

from gd_tools.coverage.orchestrator import (
    generate_coverage_report,
    merge_coverage_files,
    show_coverage_summary,
)

__all__ = [
    "generate_coverage_report",
    "merge_coverage_files",
    "show_coverage_summary",
]
