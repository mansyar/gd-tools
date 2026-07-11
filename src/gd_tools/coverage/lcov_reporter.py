"""LCOV format coverage reporter.

Generates LCOV ``.info`` files compatible with codecov.io, coveralls,
and ``genhtml``.
"""

from pathlib import Path

from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan
from gd_tools.coverage.reporter import CoverageData, FileCoverage

_TEST_NAME = "gd-tools"


def generate_lcov_report(
    plan: CoveragePlan,
    data: CoverageData,
    output_path: Path,
) -> Path:
    """Generate an LCOV ``.info`` file from plan and coverage data.

    Args:
        plan: The instrumentation plan.
        data: The runtime coverage data.
        output_path: Path where the ``.info`` file is written.

    Returns:
        The path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    coverage_by_id = {fc.file_id: fc for fc in data.files}

    lines: list[str] = [f"TN:{_TEST_NAME}"]

    for file_plan in plan.files:
        file_data = coverage_by_id.get(
            file_plan.file_id,
            FileCoverage(file_id=file_plan.file_id, hits={}),
        )
        lines.extend(_generate_file_records(file_plan, file_data))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _generate_file_records(
    file_plan: FilePlan,
    file_data: FileCoverage,
) -> list[str]:
    """Generate LCOV records for a single file.

    Args:
        file_plan: The file's instrumentation plan.
        file_data: The file's coverage data.

    Returns:
        A list of LCOV record strings for this file section.
    """
    records: list[str] = [f"SF:{file_plan.path}"]

    total_lines = 0
    hit_lines = 0
    total_branches = 0
    hit_branches = 0
    brda_records: list[str] = []

    for line_plan in file_plan.lines:
        hit_count = file_data.hits.get(str(line_plan.id), 0)
        records.append(f"DA:{line_plan.line},{hit_count}")

        total_lines += 1
        if hit_count > 0:
            hit_lines += 1

        if line_plan.type == "branch":
            total_branches += 1
            if hit_count > 0:
                hit_branches += 1
            brda_records.append(f"BRDA:{line_plan.line},0,0,{hit_count}")

    records.extend(brda_records)
    records.append(f"BRF:{total_branches}")
    records.append(f"BRH:{hit_branches}")
    records.append(f"LF:{total_lines}")
    records.append(f"LH:{hit_lines}")
    records.append("end_of_record")

    return records
