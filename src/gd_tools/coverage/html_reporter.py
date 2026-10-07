"""HTML coverage reporter using Jinja2 templates.

Generates an ``index.html`` summary page and one per-file HTML page
with line-level coverage highlighting (green/red/yellow).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan, LinePlan
from gd_tools.coverage.reporter import (
    _BRANCH_TYPE_DISPLAY,
    _format_line_ranges,
    CoverageData,
    FileCoverage,
    compute_file_summary,
    compute_summary,
)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True
)

_EXCLUSION_ANNOTATION = "# gd-tools: no cover"

#: Terminal-parity labels for branch types. The five original types come
#: from ``reporter._BRANCH_TYPE_DISPLAY`` so the HTML and terminal reports
#: never diverge; the expression-level types (ternary, short-circuit
#: ``and``/``or``, ``assert``) get human-readable labels here and fall
#: back to the raw type string when unknown (same fallback as terminal).
_BRANCH_TYPE_LABELS: dict[str, str] = {
    **_BRANCH_TYPE_DISPLAY,
    "ternary_true": "ternary true",
    "ternary_false": "ternary false",
    "and_site": "and site",
    "and_right": "and right operand",
    "and_short": "and short-circuit arm",
    "or_site": "or site",
    "or_right": "or right operand",
    "or_short": "or short-circuit arm",
}


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
        res_path = res_path[len("res://") :]
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

    Creates ``index.html`` with a summary dashboard (sortable, filterable
    file table with missed counts, zero-branch notes, and omitted targets)
    and one ``file_<id>.html`` per source file showing line-by-line
    coverage status with CSS highlighting (covered=green, uncovered=red,
    partial=yellow), inline branch-arm badges, exclusion chips for
    ``# gd-tools: no cover`` lines, and an uncovered-branch panel with
    terminal-parity arm labels and anchor links.

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

    branch_flags = {
        file_plan.file_id: file_has_branch_points(file_plan)
        for file_plan in plan.files
    }

    index_template = _env.get_template("index.html")
    index_content = index_template.render(
        summary=summary,
        file_summaries=file_summaries,
        branch_flags=branch_flags,
        omitted=data.omitted,
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

        line_views = build_line_views(
            file_plan, file_data, source_lines=source_lines
        )
        uncovered_branches = [
            {"line": line_num, "label": _arm_label(branch_type)}
            for line_num, branch_type in zip(
                fs.uncovered_branches, fs.uncovered_branch_types
            )
        ]
        file_content = file_template.render(
            file_summary=fs,
            lines=line_views,
            uncovered_line_ranges=_format_line_ranges(fs.uncovered_lines),
            uncovered_branches=uncovered_branches,
        )
        file_path = output_dir / f"file_{file_plan.file_id}.html"
        file_path.write_text(file_content, encoding="utf-8")

    return index_path


# --- Enriched view model (HTML report overhaul) ---


def _arm_label(branch_type: str) -> str:
    """Return the display label for a branch type.

    Falls back to the raw type string for unknown types, matching the
    terminal reporter's behavior.

    Args:
        branch_type: Raw branch type string from the plan.

    Returns:
        Human-readable label for display.
    """
    return _BRANCH_TYPE_LABELS.get(branch_type, branch_type)


def file_has_branch_points(file_plan: FilePlan) -> bool:
    """Return whether a file's plan contains any branch points.

    Files without branch points are flagged in the report so the
    dashboard can show a "no branch points" note instead of an empty
    branch percentage.

    Args:
        file_plan: The file's instrumentation plan.

    Returns:
        ``True`` if at least one line plan entry has type ``"branch"``.
    """
    return any(lp.type == "branch" for lp in file_plan.lines)


def build_line_views(
    file_plan: FilePlan,
    file_data: FileCoverage,
    source_lines: list[str] | None = None,
) -> list[dict]:
    """Build enriched per-line view dictionaries for HTML rendering.

    Produces one entry per source line that hosts a plan point or an
    exclusion annotation, sorted by line number. Statement and branch
    points sharing a line are merged: the statement (or first) point
    supplies the line-level hit count, and branch points are exposed as
    per-arm entries with terminal-parity labels and covered state.
    Excluded lines (``# gd-tools: no cover``) carry the ``excluded``
    flag and the annotation context; they stay out of coverage totals.

    Args:
        file_plan: The file's instrumentation plan.
        file_data: The file's runtime coverage data.
        source_lines: Optional source lines (1-indexed order) used to
            populate each entry's ``source`` text.

    Returns:
        List of dicts with keys ``number``, ``hits``, ``source``,
        ``css_class``, ``excluded``, ``annotation``, and ``branches``.
        ``branches`` is a list of dicts with keys ``branch_type``,
        ``label``, ``hits``, and ``covered``.
    """
    branch_points: dict[int, list[LinePlan]] = {}
    primary: dict[int, LinePlan] = {}
    for lp in file_plan.lines:
        if lp.type == "branch":
            branch_points.setdefault(lp.line, []).append(lp)
        else:
            primary.setdefault(lp.line, lp)
    for line, points in branch_points.items():
        if line not in primary:
            primary[line] = points[0]

    excluded = set(file_plan.excluded_lines)
    annotation_text = f'Excluded via "{_EXCLUSION_ANNOTATION}" annotation'

    views: dict[int, dict] = {}
    for line, lp in primary.items():
        hits = file_data.hits.get(str(lp.id), 0)
        arms = []
        for bp in branch_points.get(line, []):
            arm_hits = file_data.hits.get(str(bp.id), 0)
            arm_type = bp.branch_type or "unknown"
            arms.append(
                {
                    "branch_type": arm_type,
                    "label": _arm_label(arm_type),
                    "hits": arm_hits,
                    "covered": arm_hits > 0,
                }
            )
        is_excluded = line in excluded
        if is_excluded:
            css_class = "excluded"
            hits = None
        elif arms and hits > 0:
            css_class = "partial"
        elif hits > 0:
            css_class = "covered"
        else:
            css_class = "uncovered"
        views[line] = {
            "number": line,
            "hits": hits,
            "source": "",
            "css_class": css_class,
            "excluded": is_excluded,
            "annotation": annotation_text if is_excluded else "",
            "branches": arms,
        }

    # Excluded lines with no plan point still render (greyed out).
    for line in sorted(excluded - views.keys()):
        views[line] = {
            "number": line,
            "hits": None,
            "source": "",
            "css_class": "excluded",
            "excluded": True,
            "annotation": annotation_text,
            "branches": [],
        }

    if source_lines:
        for view in views.values():
            number = view["number"]
            if 1 <= number <= len(source_lines):
                view["source"] = source_lines[number - 1]

    return [views[line] for line in sorted(views)]
