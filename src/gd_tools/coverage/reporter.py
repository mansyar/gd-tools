"""Coverage reporter module.

Reads instrumentation plan JSON (from the plan generator) and coverage
data JSON (from the GDScript runtime hooks), cross-references them by
``file_id`` to compute line and branch coverage metrics, and dispatches
to format-specific reporters (HTML, LCOV, Cobertura, terminal).

This module is the final reporting layer of the hybrid coverage system
(Architecture C: Python plan gen -> GDScript runtime instrumentation ->
Python reporting).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from gd_tools.errors import CoveragePlanError

# --- Data structures (FR-1, FR-2, FR-3) ---


@dataclass
class FileCoverage:
    """Coverage data for a single file from the runtime tracker.

    Attributes:
        file_id: Sequential identifier matching the plan's ``file_id``.
        hits: Mapping of line ID (string key) to hit count.
    """

    file_id: int
    hits: dict[str, int]


@dataclass
class CoverageData:
    """Top-level container for runtime coverage data.

    Attributes:
        version: Schema version (currently 1).
        generated_at: ISO timestamp from the runtime tracker, or None.
        files: List of per-file coverage data.
    """

    version: int
    generated_at: str | None = None
    files: list[FileCoverage] = field(default_factory=list)


@dataclass
class CoverageSummary:
    """Overall coverage summary across all files.

    Attributes:
        line_rate: Fraction of executable lines covered (0.0-1.0).
        branch_rate: Fraction of branch points covered (0.0-1.0).
        covered_lines: Count of lines with hit count > 0.
        total_lines: Total executable lines in the plan.
        covered_branches: Count of branches with hit count > 0.
        total_branches: Total branch points in the plan.
    """

    line_rate: float
    branch_rate: float
    covered_lines: int
    total_lines: int
    covered_branches: int
    total_branches: int


@dataclass
class FileSummary:
    """Per-file coverage summary.

    Attributes:
        file_id: Sequential identifier from the plan.
        path: Godot resource path (``res://``) from the plan.
        line_rate: Fraction of executable lines covered (0.0-1.0).
        branch_rate: Fraction of branch points covered (0.0-1.0).
        covered_lines: Count of lines with hit count > 0.
        total_lines: Total executable lines in this file's plan.
        covered_branches: Count of branches with hit count > 0.
        total_branches: Total branch points in this file's plan.
        uncovered_lines: Line numbers with zero hits.
    """

    file_id: int
    path: str
    line_rate: float
    branch_rate: float
    covered_lines: int
    total_lines: int
    covered_branches: int
    total_branches: int
    uncovered_lines: list[int]


@dataclass
class ReportResult:
    """Result of a report generation operation.

    Attributes:
        output_path: Path to the generated report file or directory.
        format: Report format (``"html"``, ``"lcov"``, ``"cobertura"``,
            ``"terminal"``).
        summary: Overall coverage summary.
        file_summaries: Per-file coverage breakdowns.
        threshold_met: Whether coverage met the minimum threshold.
    """

    output_path: Path
    format: str
    summary: CoverageSummary
    file_summaries: list[FileSummary]
    threshold_met: bool


# --- JSON I/O (FR-1) ---


def read_coverage_json(path: Path) -> CoverageData:
    """Read a coverage data JSON file produced by the runtime tracker.

    The expected format matches Track 11's runtime output: each file
    entry has ``file_id`` (int) and ``hits`` (dict with string keys).
    A ``path`` field is NOT required in the coverage data — path
    resolution happens at report-generation time via the plan.

    Args:
        path: Path to the coverage data JSON file.

    Returns:
        The deserialized :class:`CoverageData`.

    Raises:
        CoveragePlanError: If the file is missing, contains invalid
            JSON, or has a version mismatch.
    """
    cov_path = Path(path)
    if not cov_path.exists():
        raise CoveragePlanError(f"Coverage data file not found: {path}")

    try:
        data = json.loads(cov_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CoveragePlanError(
            f"Invalid JSON in coverage data file: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise CoveragePlanError("Coverage data JSON must be a JSON object")

    version = data.get("version")
    if version != 1:
        raise CoveragePlanError(
            f"Unsupported coverage data version: {version} (expected 1)"
        )

    if "files" not in data:
        raise CoveragePlanError("Missing required field: files")

    files_data = data["files"]
    if not isinstance(files_data, list):
        raise CoveragePlanError("Coverage data 'files' field must be a list")

    files: list[FileCoverage] = []
    for fdata in files_data:
        if not isinstance(fdata, dict):
            raise CoveragePlanError(
                "Each coverage file entry must be a JSON object"
            )
        if "file_id" not in fdata:
            raise CoveragePlanError(
                "Missing required field in coverage file entry: file_id"
            )
        if "hits" not in fdata:
            raise CoveragePlanError(
                "Missing required field in coverage file entry: hits"
            )
        hits_data = fdata["hits"]
        if not isinstance(hits_data, dict):
            raise CoveragePlanError("Coverage 'hits' field must be a dict")

        # Ensure all hit counts are ints (JSON may produce them as such,
        # but we normalize for safety)
        hits = {str(k): int(v) for k, v in hits_data.items()}

        files.append(FileCoverage(file_id=fdata["file_id"], hits=hits))

    return CoverageData(
        version=data["version"],
        generated_at=data.get("generated_at"),
        files=files,
    )


def merge_coverage_data(files: list[Path]) -> CoverageData:
    """Merge multiple coverage data files (for parallel CI shards).

    Sums hit counts per ``file_id``/``line_id`` across all input files.
    Files that appear in only one shard are included as-is.

    Args:
        files: List of paths to coverage data JSON files.

    Returns:
        A merged :class:`CoverageData` with summed hit counts.
    """
    if not files:
        return CoverageData(version=1)

    merged_files: dict[int, dict[str, int]] = {}
    generated_at: str | None = None

    for fpath in files:
        data = read_coverage_json(fpath)
        if generated_at is None:
            generated_at = data.generated_at

        for fc in data.files:
            if fc.file_id not in merged_files:
                merged_files[fc.file_id] = {}
            for line_id, count in fc.hits.items():
                merged_files[fc.file_id][line_id] = (
                    merged_files[fc.file_id].get(line_id, 0) + count
                )

    result_files = [
        FileCoverage(file_id=fid, hits=hits)
        for fid, hits in merged_files.items()
    ]

    return CoverageData(
        version=1,
        generated_at=generated_at,
        files=result_files,
    )
