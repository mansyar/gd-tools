"""Unit tests for the coverage orchestrator module.

Tests the four orchestration functions that coordinate plan_generator ->
test_runner -> reporter:

- run_coverage_test(): full coverage flow (plan -> run -> report)
- generate_coverage_report(): regenerate reports from existing data
- merge_coverage_files(): merge multiple coverage data files
- show_coverage_summary(): print terminal summary table
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.coverage.orchestrator import (
    generate_coverage_report,
    merge_coverage_files,
    run_coverage_test,
    show_coverage_summary,
)
from gd_tools.coverage.plan_generator import CoveragePlan, FilePlan, LinePlan
from gd_tools.coverage.reporter import (
    CoverageData,
    CoverageSummary,
    FileCoverage,
    ReportResult,
)
from gd_tools.errors import (
    CoveragePlanError,
    CoverageThresholdError,
    TestFailureError,
)
from gd_tools.test_runner import TestResult

# --- Helpers ---


def _make_config(output_dir: str = ".gd-tools/coverage") -> GdToolsConfig:
    """Create a GdToolsConfig with coverage settings."""
    config = GdToolsConfig()
    config.coverage.output_dir = output_dir
    return config


def _make_plan() -> CoveragePlan:
    """Create a minimal CoveragePlan for testing."""
    return CoveragePlan(
        version=1,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://script.gd",
                source_hash="sha256:abc123",
                lines=[
                    LinePlan(line=1, id=0, type="statement", branch_type=None)
                ],
            )
        ],
    )


def _make_coverage_data() -> CoverageData:
    """Create minimal CoverageData for testing."""
    return CoverageData(
        version=1,
        generated_at="2025-01-01T00:00:00",
        files=[FileCoverage(file_id=0, hits={"0": 3})],
    )


def _make_test_result() -> TestResult:
    """Create a minimal TestResult for testing."""
    return TestResult(
        total=1,
        passed=1,
        failed=0,
        skipped=0,
        duration=0.1,
        junit_xml_path=None,
        coverage_data_path=Path("/fake/coverage.json"),
        stdout="",
        stderr="",
    )


def _make_report_result() -> ReportResult:
    """Create a minimal ReportResult for testing."""
    return ReportResult(
        output_path=Path("/fake/report.html"),
        format="html",
        summary=CoverageSummary(
            line_rate=0.8,
            branch_rate=1.0,
            covered_lines=1,
            total_lines=1,
            covered_branches=0,
            total_branches=0,
        ),
        file_summaries=[],
        threshold_met=True,
    )


@pytest.fixture
def mock_deps(tmp_path):
    """Patch all orchestrator dependencies for testing.

    Yields a dict of mock objects keyed by function name.
    """
    with (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root"
        ) as mock_find_root,
        patch(
            "gd_tools.coverage.orchestrator.plan_generator.generate_plan"
        ) as mock_gen_plan,
        patch(
            "gd_tools.coverage.orchestrator.plan_generator.write_plan_json"
        ) as mock_write_plan,
        patch("gd_tools.coverage.orchestrator.run_tests") as mock_run_tests,
        patch(
            "gd_tools.coverage.orchestrator.reporter.read_coverage_json"
        ) as mock_read_cov,
        patch(
            "gd_tools.coverage.orchestrator.plan_generator.read_plan_json"
        ) as mock_read_plan,
        patch(
            "gd_tools.coverage.orchestrator.reporter.generate_report"
        ) as mock_gen_report,
        patch(
            "gd_tools.coverage.orchestrator.reporter.compute_summary"
        ) as mock_compute_summary,
    ):
        mock_find_root.return_value = tmp_path
        mock_gen_plan.return_value = _make_plan()
        mock_run_tests.return_value = _make_test_result()
        mock_read_cov.return_value = _make_coverage_data()
        mock_read_plan.return_value = _make_plan()
        mock_gen_report.return_value = _make_report_result()
        mock_compute_summary.return_value = CoverageSummary(
            line_rate=0.8,
            branch_rate=1.0,
            covered_lines=4,
            total_lines=5,
            covered_branches=0,
            total_branches=0,
        )

        yield {
            "find_project_root": mock_find_root,
            "generate_plan": mock_gen_plan,
            "write_plan_json": mock_write_plan,
            "run_tests": mock_run_tests,
            "read_coverage_json": mock_read_cov,
            "read_plan_json": mock_read_plan,
            "generate_report": mock_gen_report,
            "compute_summary": mock_compute_summary,
        }


# --- run_coverage_test() ---


@pytest.mark.unit
def test_run_coverage_test_generates_plan(mock_deps):
    """run_coverage_test() generates a plan via plan_generator.generate_plan()."""
    run_coverage_test(_make_config())

    mock_deps["generate_plan"].assert_called_once()


@pytest.mark.unit
def test_run_coverage_test_writes_plan_json(mock_deps):
    """run_coverage_test() writes plan to <output_dir>/plan.json."""
    run_coverage_test(_make_config())

    mock_deps["write_plan_json"].assert_called_once()
    plan_path = mock_deps["write_plan_json"].call_args[0][1]
    assert plan_path.endswith("plan.json")
    assert "coverage" in plan_path


@pytest.mark.unit
def test_run_coverage_test_calls_run_tests_with_coverage(mock_deps):
    """run_coverage_test() calls run_tests() with coverage=True."""
    run_coverage_test(_make_config())

    mock_deps["run_tests"].assert_called_once()
    kwargs = mock_deps["run_tests"].call_args.kwargs
    assert kwargs.get("coverage") is True


@pytest.mark.unit
def test_run_coverage_test_reads_coverage_data(mock_deps):
    """run_coverage_test() reads coverage data via reporter.read_coverage_json()."""
    run_coverage_test(_make_config())

    mock_deps["read_coverage_json"].assert_called_once()
    cov_path = mock_deps["read_coverage_json"].call_args[0][0]
    assert str(cov_path).endswith("coverage.json")


@pytest.mark.unit
def test_run_coverage_test_min_percent_converted(mock_deps):
    """run_coverage_test() converts min_percent (0-100) to min_threshold (0.0-1.0)."""
    run_coverage_test(_make_config(), min_percent=80)

    mock_deps["generate_report"].assert_called_once()
    kwargs = mock_deps["generate_report"].call_args.kwargs
    assert kwargs.get("min_threshold") == 0.8


@pytest.mark.unit
def test_run_coverage_test_error_precedence_test_failure_first(mock_deps):
    """When both TestFailureError and CoverageThresholdError occur, TestFailureError is re-raised."""
    mock_deps["run_tests"].side_effect = TestFailureError("Tests failed")
    mock_deps["generate_report"].side_effect = CoverageThresholdError(
        "Below threshold"
    )

    with pytest.raises(TestFailureError):
        run_coverage_test(_make_config())


@pytest.mark.unit
def test_run_coverage_test_raises_coverage_threshold_error(mock_deps):
    """When only CoverageThresholdError occurs, it is raised."""
    mock_deps["generate_report"].side_effect = CoverageThresholdError(
        "Below threshold"
    )

    with pytest.raises(CoverageThresholdError):
        run_coverage_test(_make_config())


@pytest.mark.unit
def test_run_coverage_test_returns_test_result(mock_deps):
    """When no errors occur, TestResult is returned."""
    expected = _make_test_result()
    mock_deps["run_tests"].return_value = expected

    result = run_coverage_test(_make_config())

    assert result == expected


@pytest.mark.unit
def test_run_coverage_test_re_raises_test_failure(mock_deps):
    """When TestFailureError occurs but coverage is above threshold, TestFailureError is re-raised."""
    mock_deps["run_tests"].side_effect = TestFailureError("Tests failed")

    with pytest.raises(TestFailureError):
        run_coverage_test(_make_config())


@pytest.mark.unit
def test_run_coverage_test_no_exit_code_passes_flag(mock_deps):
    """When no_exit_code=True, the flag is passed to run_tests and reports are still generated."""
    run_coverage_test(_make_config(), no_exit_code=True)

    kwargs = mock_deps["run_tests"].call_args.kwargs
    assert kwargs.get("no_exit_code") is True
    mock_deps["generate_report"].assert_called_once()


# --- generate_coverage_report() ---


@pytest.mark.unit
def test_generate_coverage_report_reads_plan(mock_deps):
    """generate_coverage_report() reads plan from <output_dir>/plan.json."""
    generate_coverage_report(_make_config())

    mock_deps["read_plan_json"].assert_called_once()
    plan_path = mock_deps["read_plan_json"].call_args[0][0]
    assert plan_path.endswith("plan.json")
    assert "coverage" in plan_path


@pytest.mark.unit
def test_generate_coverage_report_reads_coverage_data(mock_deps):
    """generate_coverage_report() reads coverage data from <output_dir>/coverage.json."""
    generate_coverage_report(_make_config())

    mock_deps["read_coverage_json"].assert_called_once()
    cov_path = mock_deps["read_coverage_json"].call_args[0][0]
    assert str(cov_path).endswith("coverage.json")


@pytest.mark.unit
def test_generate_coverage_report_calls_generate_report(mock_deps):
    """generate_coverage_report() calls reporter.generate_report() with correct parameters."""
    generate_coverage_report(_make_config())

    mock_deps["generate_report"].assert_called_once()
    call_args = mock_deps["generate_report"].call_args
    # positional args: (plan, data, output_dir, format)
    assert isinstance(call_args[0][2], Path)  # output_dir
    assert call_args[0][3] == "html"  # default format from config


@pytest.mark.unit
def test_generate_coverage_report_format_override(mock_deps):
    """--format flag overrides config.coverage.format."""
    generate_coverage_report(_make_config(), report_format="lcov")

    format_arg = mock_deps["generate_report"].call_args[0][3]
    assert format_arg == "lcov"


@pytest.mark.unit
def test_generate_coverage_report_output_dir_override(mock_deps):
    """--output-dir flag overrides config.coverage.output_dir."""
    generate_coverage_report(_make_config(), output_dir=".gd-tools/custom")

    plan_path = mock_deps["read_plan_json"].call_args[0][0]
    assert "custom" in plan_path


@pytest.mark.unit
def test_generate_coverage_report_missing_coverage_raises_plan_error(
    mock_deps,
):
    """Missing coverage.json raises CoveragePlanError (exit code 2)."""
    mock_deps["read_coverage_json"].side_effect = CoveragePlanError(
        "File not found"
    )

    with pytest.raises(CoveragePlanError):
        generate_coverage_report(_make_config())


@pytest.mark.unit
def test_generate_coverage_report_missing_plan_raises_plan_error(mock_deps):
    """Missing plan.json raises CoveragePlanError (exit code 2)."""
    mock_deps["read_plan_json"].side_effect = CoveragePlanError(
        "File not found"
    )

    with pytest.raises(CoveragePlanError):
        generate_coverage_report(_make_config())


# --- merge_coverage_files() tests ---


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_calls_merge_coverage_data(mock_merge):
    """merge_coverage_files delegates to reporter.merge_coverage_data."""
    mock_merge.return_value = _make_coverage_data()
    files = [Path("a.json"), Path("b.json")]

    merge_coverage_files(files)

    mock_merge.assert_called_once_with(files)


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_writes_json_to_default_output(
    mock_merge, tmp_path
):
    """Merged data is written to .gd-tools/coverage/coverage.json by default."""
    merged = CoverageData(
        version=1,
        generated_at="2025-01-01T00:00:00",
        files=[FileCoverage(file_id=0, hits={"0": 3, "1": 0})],
    )
    mock_merge.return_value = merged

    with patch(
        "gd_tools.coverage.orchestrator.Path.cwd", return_value=tmp_path
    ):
        merge_coverage_files([Path("a.json")])

    output_file = tmp_path / ".gd-tools" / "coverage" / "coverage.json"
    assert output_file.exists()

    import json

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["generated_at"] == "2025-01-01T00:00:00"
    assert len(data["files"]) == 1
    assert data["files"][0]["file_id"] == 0
    assert data["files"][0]["hits"] == {"0": 3, "1": 0}


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_writes_json_to_custom_output(
    mock_merge, tmp_path
):
    """Merged data is written to the custom --output path."""
    mock_merge.return_value = _make_coverage_data()
    custom_output = tmp_path / "merged" / "result.json"

    merge_coverage_files([Path("a.json")], output_path=custom_output)

    assert custom_output.exists()


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_returns_merged_data(mock_merge):
    """The merged CoverageData is returned."""
    merged = _make_coverage_data()
    mock_merge.return_value = merged

    result = merge_coverage_files(
        [Path("a.json")], output_path=Path("out.json")
    )

    assert result is merged


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_creates_output_dir(mock_merge, tmp_path):
    """Parent directories of the output path are created if missing."""
    mock_merge.return_value = _make_coverage_data()
    output = tmp_path / "deep" / "nested" / "dir" / "coverage.json"

    merge_coverage_files([Path("a.json")], output_path=output)

    assert output.exists()


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_empty_list(mock_merge, tmp_path):
    """Empty file list still writes an (empty) output."""
    mock_merge.return_value = CoverageData(version=1, files=[])

    with patch(
        "gd_tools.coverage.orchestrator.Path.cwd", return_value=tmp_path
    ):
        result = merge_coverage_files([], output_path=None)

    output_file = tmp_path / ".gd-tools" / "coverage" / "coverage.json"
    assert output_file.exists()
    assert result.files == []


@pytest.mark.unit
@patch("gd_tools.coverage.orchestrator.find_project_root")
@patch("gd_tools.coverage.orchestrator.reporter.merge_coverage_data")
def test_merge_coverage_files_with_config_no_output(
    mock_merge, mock_find_root, tmp_path
):
    """When output is None but config is provided, output path uses config.coverage.output_dir."""
    mock_merge.return_value = _make_coverage_data()
    mock_find_root.return_value = tmp_path
    config = _make_config(output_dir="custom_cov")

    merge_coverage_files([Path("a.json")], output_path=None, config=config)

    output_file = tmp_path / "custom_cov" / "coverage.json"
    assert output_file.exists()
    mock_find_root.assert_called_once()


# --- show_coverage_summary() tests ---


@pytest.mark.unit
def test_show_coverage_summary_reads_plan(mock_deps):
    """show_coverage_summary() reads plan from <output_dir>/plan.json."""
    show_coverage_summary(_make_config())

    mock_deps["read_plan_json"].assert_called_once()
    plan_path = mock_deps["read_plan_json"].call_args[0][0]
    assert plan_path.endswith("plan.json")
    assert "coverage" in plan_path


@pytest.mark.unit
def test_show_coverage_summary_reads_coverage_data(mock_deps):
    """show_coverage_summary() reads coverage data from <output_dir>/coverage.json."""
    show_coverage_summary(_make_config())

    mock_deps["read_coverage_json"].assert_called_once()
    cov_path = mock_deps["read_coverage_json"].call_args[0][0]
    assert str(cov_path).endswith("coverage.json")


@pytest.mark.unit
def test_show_coverage_summary_calls_compute_summary(mock_deps):
    """show_coverage_summary() calls reporter.compute_summary(plan, data)."""
    show_coverage_summary(_make_config())

    mock_deps["compute_summary"].assert_called_once()


@pytest.mark.unit
def test_show_coverage_summary_prints_rich_table(mock_deps, capsys):
    """show_coverage_summary() prints a Rich terminal summary table."""
    show_coverage_summary(_make_config())

    captured = capsys.readouterr()
    assert "Coverage Summary" in captured.out
    assert "Lines" in captured.out
    assert "Branches" in captured.out


@pytest.mark.unit
def test_show_coverage_summary_threshold_below_raises_error(mock_deps):
    """--min N threshold raises CoverageThresholdError when below threshold."""
    # summary.line_rate = 0.8 (80%), min_percent = 90 → should raise
    with pytest.raises(CoverageThresholdError):
        show_coverage_summary(_make_config(), min_percent=90)


@pytest.mark.unit
def test_show_coverage_summary_threshold_at_or_above_no_error(mock_deps):
    """--min N threshold passes when at or above threshold."""
    # summary.line_rate = 0.8 (80%), min_percent = 80 → should NOT raise
    result = show_coverage_summary(_make_config(), min_percent=80)

    assert isinstance(result, CoverageSummary)


@pytest.mark.unit
def test_show_coverage_summary_missing_coverage_raises_plan_error(mock_deps):
    """Missing coverage.json raises CoveragePlanError."""
    mock_deps["read_coverage_json"].side_effect = CoveragePlanError(
        "File not found"
    )

    with pytest.raises(CoveragePlanError):
        show_coverage_summary(_make_config())


# --- Coverage summary display in run_coverage_test() ---


@pytest.mark.unit
def test_run_coverage_test_coverage_summary_on_success(mock_deps, capsys):
    """run_coverage_test() prints coverage inline summary on success (no --min)."""
    run_coverage_test(_make_config())

    captured = capsys.readouterr()
    assert "Coverage:" in captured.out
    assert "80.0%" in captured.out  # line_rate = 0.8 = 80%


@pytest.mark.unit
def test_run_coverage_test_coverage_summary_threshold_met(mock_deps, capsys):
    """run_coverage_test() prints coverage inline summary when --min threshold is met."""
    run_coverage_test(_make_config(), min_percent=80)

    captured = capsys.readouterr()
    assert "Coverage:" in captured.out
    assert "80.0%" in captured.out


@pytest.mark.unit
def test_run_coverage_test_coverage_summary_before_threshold_error(
    mock_deps,
    capsys,
):
    """run_coverage_test() prints coverage inline summary before raising CoverageThresholdError."""
    err = CoverageThresholdError(
        "Below threshold", report_result=_make_report_result()
    )
    mock_deps["generate_report"].side_effect = err

    with pytest.raises(CoverageThresholdError):
        run_coverage_test(_make_config(), min_percent=90)

    captured = capsys.readouterr()
    assert "Coverage:" in captured.out


@pytest.mark.unit
def test_run_coverage_test_no_coverage_summary_on_plan_error(mock_deps, capsys):
    """run_coverage_test() does NOT print coverage summary when coverage data is unavailable."""
    mock_deps["read_coverage_json"].side_effect = CoveragePlanError(
        "File not found"
    )

    with pytest.raises(CoveragePlanError):
        run_coverage_test(_make_config())

    captured = capsys.readouterr()
    assert "Coverage:" not in captured.out
    assert "Coverage Summary" not in captured.out


@pytest.mark.unit
def test_coverage_summary_table_format_matches_show_summary(mock_deps, capsys):
    """show_coverage_summary() table has columns: Metric, Found, Hit, Rate."""
    show_coverage_summary(_make_config())

    captured = capsys.readouterr()
    assert "Coverage Summary" in captured.out
    assert "Metric" in captured.out
    assert "Found" in captured.out
    assert "Hit" in captured.out
    assert "Rate" in captured.out


# --- Coverage output color-coding and summary footer ---


@pytest.mark.unit
def test_show_coverage_summary_summary_footer(mock_deps, capsys):
    """show_coverage_summary() prints a summary footer with coverage percentage."""
    show_coverage_summary(_make_config())

    captured = capsys.readouterr()
    assert "80.0%" in captured.out  # line_rate = 0.8 = 80%


@pytest.mark.unit
def test_show_coverage_summary_color_coded_above_threshold(
    mock_deps,
    monkeypatch,
    capsys,
):
    """show_coverage_summary() color-codes rate cells green when at or above threshold."""
    from rich.console import Console

    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    show_coverage_summary(_make_config(), min_percent=80)

    captured = capsys.readouterr()
    # Green ANSI code for rates at or above threshold
    assert "\x1b[32" in captured.out  # green


@pytest.mark.unit
def test_show_coverage_summary_color_coded_below_threshold(
    mock_deps,
    monkeypatch,
    capsys,
):
    """show_coverage_summary() color-codes rate cells red when below threshold."""
    from rich.console import Console

    monkeypatch.setattr("gd_tools.output.console", Console(force_terminal=True))
    with pytest.raises(CoverageThresholdError):
        show_coverage_summary(_make_config(), min_percent=90)

    captured = capsys.readouterr()
    # Red ANSI code for rates below threshold
    assert "\x1b[31" in captured.out  # red


@pytest.mark.unit
def test_run_coverage_test_inline_summary_content(mock_deps, capsys):
    """run_coverage_test() inline summary shows line and branch coverage percentages."""
    run_coverage_test(_make_config())

    captured = capsys.readouterr()
    assert "Coverage:" in captured.out
    assert "80.0%" in captured.out  # line_rate = 0.8 = 80%
    assert "100.0%" in captured.out  # branch_rate = 1.0 = 100%
