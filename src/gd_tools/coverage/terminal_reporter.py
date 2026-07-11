"""Terminal reporter using Rich for formatted coverage output."""

import io

from rich import box
from rich.console import Console
from rich.table import Table

from gd_tools.coverage.plan_generator import CoveragePlan
from gd_tools.coverage.reporter import (
    CoverageData,
    FileCoverage,
    compute_file_summary,
    compute_summary,
)

_GREEN_THRESHOLD = 0.80
_YELLOW_THRESHOLD = 0.50


def _color_for_rate(rate: float) -> str:
    """Return Rich color name for a coverage rate.

    Args:
        rate: Coverage rate (0.0-1.0).

    Returns:
        Rich color name: ``"green"``, ``"yellow"``, or ``"red"``.
    """
    if rate >= _GREEN_THRESHOLD:
        return "green"
    elif rate >= _YELLOW_THRESHOLD:
        return "yellow"
    else:
        return "red"


def generate_terminal_report(
    plan: CoveragePlan,
    data: CoverageData,
) -> str:
    """Generate a Rich table coverage report as a string.

    Produces a color-coded table with per-file line and branch
    coverage metrics, followed by an overall summary.  Table borders
    use ASCII characters for terminal compatibility.

    Args:
        plan: The instrumentation plan.
        data: The runtime coverage data.

    Returns:
        A formatted Rich table string with ANSI color codes.
    """
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)

    table = Table(title="Coverage Report", box=box.ASCII)
    table.add_column("File")
    table.add_column("Lines Found", justify="right")
    table.add_column("Lines Hit", justify="right")
    table.add_column("Line %", justify="right")
    table.add_column("Branches Found", justify="right")
    table.add_column("Branches Hit", justify="right")
    table.add_column("Branch %", justify="right")

    summary = compute_summary(plan, data)
    coverage_by_id = {fc.file_id: fc for fc in data.files}

    for file_plan in plan.files:
        file_data = coverage_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        fs = compute_file_summary(file_plan, file_data)

        line_color = _color_for_rate(fs.line_rate)
        branch_color = _color_for_rate(fs.branch_rate)

        table.add_row(
            file_plan.path,
            str(fs.total_lines),
            str(fs.covered_lines),
            f"[{line_color}]{fs.line_rate:.1%}[/{line_color}]",
            str(fs.total_branches),
            str(fs.covered_branches),
            f"[{branch_color}]{fs.branch_rate:.1%}[/{branch_color}]",
        )

    console.print(table)

    # Overall summary
    overall_line_color = _color_for_rate(summary.line_rate)
    overall_branch_color = _color_for_rate(summary.branch_rate)
    console.print()
    console.print(
        f"[bold]Overall Line Coverage:[/bold] "
        f"[{overall_line_color}]{summary.line_rate:.1%}"
        f"[/{overall_line_color}]"
    )
    console.print(
        f"[bold]Overall Branch Coverage:[/bold] "
        f"[{overall_branch_color}]{summary.branch_rate:.1%}"
        f"[/{overall_branch_color}]"
    )

    return buf.getvalue()
