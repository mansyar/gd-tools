"""HTML coverage reporter using Jinja2 templates.

Generates an ``index.html`` summary page and one per-file HTML page
with line-level coverage highlighting (green/red/yellow).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gd_tools.coverage.plan_generator import CoveragePlan
from gd_tools.coverage.reporter import (
    CoverageData,
    FileCoverage,
    compute_file_summary,
    compute_summary,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True
)


def _read_source_lines(res_path: str) -> list[str]:
    """Read source lines from a ``res://`` path for HTML display.

    Strips the ``res://`` prefix and resolves the path relative
    to the current working directory (typically the project root
    when running gd-tools). Returns an empty list if the file
    cannot be read.

    Args:
        res_path: A ``res://`` path (e.g., ``res://scripts/player.gd``).

    Returns:
        List of source code lines (without trailing newlines),
        or an empty list if the file is not accessible.
    """
    if res_path.startswith("res://"):
        res_path = res_path[len("res://"):]
    fs_path = Path(res_path)
    if not fs_path.exists():
        return []
    try:
        return fs_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def generate_html_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_dir: Path,
) -> Path:
    """Generate an HTML coverage report with index and per-file pages.

    Creates ``index.html`` with a summary table and one ``file_<id>.html``
    per source file showing line-by-line coverage status with CSS
    highlighting (covered=green, uncovered=red, partial=yellow).

    Args:
        plan: The instrumentation plan defining tracked lines.
        data: The runtime coverage data with hit counts.
        output_dir: Directory where HTML files are written.

    Returns:
        Path to the generated ``index.html``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = compute_summary(plan, data)

    coverage_by_id = {fc.file_id: fc for fc in data.files}
    file_summaries = []
    for file_plan in plan.files:
        file_data = coverage_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        file_summaries.append(compute_file_summary(file_plan, file_data))

    index_template = _env.get_template("index.html")
    index_content = index_template.render(
        summary=summary, file_summaries=file_summaries
    )
    index_path = output_dir / "index.html"
    index_path.write_text(index_content, encoding="utf-8")

    file_template = _env.get_template("file.html")
    for file_plan, fs in zip(plan.files, file_summaries):
        file_data = coverage_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )

        # Resolve res:// path to filesystem path for source display
        source_lines = _read_source_lines(file_plan.path)

        lines = []
        for line_plan in file_plan.lines:
            hit_count = file_data.hits.get(str(line_plan.id), 0)
            if hit_count > 0 and line_plan.type == "branch":
                css_class = "partial"
            elif hit_count > 0:
                css_class = "covered"
            else:
                css_class = "uncovered"
            line_num = line_plan.line
            source_text = ""
            if source_lines and 1 <= line_num <= len(source_lines):
                source_text = source_lines[line_num - 1]
            lines.append(
                {
                    "number": line_num,
                    "hits": hit_count,
                    "source": source_text,
                    "css_class": css_class,
                }
            )
        file_content = file_template.render(file_summary=fs, lines=lines)
        file_path = output_dir / f"file_{file_plan.file_id}.html"
        file_path.write_text(file_content, encoding="utf-8")

    return index_path
