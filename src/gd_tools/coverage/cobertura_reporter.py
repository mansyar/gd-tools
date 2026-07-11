"""Cobertura XML coverage reporter.

Generates Cobertura XML files compatible with Jenkins and GitLab CI
coverage parsers using the standard library ``xml.etree.ElementTree``.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan
from gd_tools.coverage.reporter import CoverageData, FileCoverage


def generate_cobertura_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_path: Path,
) -> Path:
    """Generate a Cobertura XML file from plan and coverage data.

    Args:
        plan: The instrumentation plan.
        data: The runtime coverage data.
        output_path: Path where the XML file is written.

    Returns:
        The path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    coverage_by_id = {fc.file_id: fc for fc in data.files}

    total_lines = 0
    hit_lines = 0
    total_branches = 0
    hit_branches = 0

    root = ET.Element("coverage")
    packages_elem = ET.SubElement(root, "packages")
    package_elem = ET.SubElement(packages_elem, "package")
    classes_elem = ET.SubElement(package_elem, "classes")

    for file_plan in plan.files:
        file_data = coverage_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        cls_lines, cls_hit, cls_br, cls_hit_br = _build_class_element(
            file_plan, file_data, classes_elem
        )
        total_lines += cls_lines
        hit_lines += cls_hit
        total_branches += cls_br
        hit_branches += cls_hit_br

    root.set("line-rate", _format_rate(total_lines, hit_lines))
    root.set("branch-rate", _format_rate(total_branches, hit_branches))
    root.set("lines-covered", str(hit_lines))
    root.set("lines-valid", str(total_lines))
    root.set("branches-covered", str(hit_branches))
    root.set("branches-valid", str(total_branches))

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def _build_class_element(
    file_plan: FilePlan,
    file_data: FileCoverage,
    classes_elem: ET.Element,
) -> tuple[int, int, int, int]:
    """Build a ``<class>`` element for a single file.

    Args:
        file_plan: The file's instrumentation plan.
        file_data: The file's coverage data.
        classes_elem: The parent ``<classes>`` element.

    Returns:
        A tuple of (total_lines, hit_lines, total_branches, hit_branches).
    """
    cls_elem = ET.SubElement(classes_elem, "class")
    cls_elem.set("filename", file_plan.path)

    lines_elem = ET.SubElement(cls_elem, "lines")

    total_lines = 0
    hit_lines = 0
    total_branches = 0
    hit_branches = 0

    for line_plan in file_plan.lines:
        hit_count = file_data.hits.get(str(line_plan.id), 0)
        line_elem = ET.SubElement(lines_elem, "line")
        line_elem.set("number", str(line_plan.line))
        line_elem.set("hits", str(hit_count))

        total_lines += 1
        if hit_count > 0:
            hit_lines += 1

        if line_plan.type == "branch":
            line_elem.set("branch", "true")
            total_branches += 1
            if hit_count > 0:
                hit_branches += 1
            coverage_pct = 100 if hit_count > 0 else 0
            line_elem.set(
                "condition-coverage",
                f"{coverage_pct}% ({1 if hit_count > 0 else 0}/1)",
            )
        else:
            line_elem.set("branch", "false")

    cls_elem.set("line-rate", _format_rate(total_lines, hit_lines))
    cls_elem.set("branch-rate", _format_rate(total_branches, hit_branches))

    return total_lines, hit_lines, total_branches, hit_branches


def _format_rate(total: int, hit: int) -> str:
    """Format a coverage rate as a decimal string.

    Args:
        total: Total count of items.
        hit: Count of covered items.

    Returns:
        A string like ``"0.625"`` or ``"0.0"``.
    """
    if total == 0:
        return "0.0"
    return f"{hit / total:.4f}".rstrip("0").rstrip(".") or "0"
