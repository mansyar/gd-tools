"""Unit tests for patch-coverage CLI integration and gating.

Covers the ``coverage diff --patch`` wiring (option validation, exit
codes) and the orchestrator flow ``diff_coverage_patch`` (loading the
current plan/data pair, rendering, gate, and combined regression
check) per the Patch Coverage track specification (FR-1, FR-4, FR-8,
AC-7, AC-8, AC-9).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gd_tools.cli import cli
from gd_tools.coverage.orchestrator import diff_coverage_patch
from gd_tools.coverage.plan_generator import (
    CoveragePlan,
    PLAN_VERSION,
    FilePlan,
    LinePlan,
    write_plan_json,
)
from gd_tools.coverage.reporter import (
    CoverageData,
    FileCoverage,
    write_coverage_json,
)
from gd_tools.errors import CoveragePlanError, CoverageThresholdError

pytestmark = pytest.mark.unit


# --- Helpers ---


def _plan() -> CoveragePlan:
    """One file with statements on lines 5 and 10."""
    return CoveragePlan(
        version=PLAN_VERSION,
        generated_by="gd-tools",
        files=[
            FilePlan(
                file_id=0,
                path="res://player.gd",
                source_hash="sha256:abc",
                lines=[
                    LinePlan(line=5, id=0, type="statement"),
                    LinePlan(line=10, id=1, type="statement"),
                ],
            )
        ],
    )


def _data(hits: dict[str, int]) -> CoverageData:
    return CoverageData(
        version=1,
        generated_at=None,
        files=[FileCoverage(file_id=0, hits=hits)],
    )


def _setup_project(tmp_path: Path, plan: CoveragePlan, data: CoverageData):
    """Write plan.json + coverage.json into tmp_path/cov-out."""
    out = tmp_path / "cov-out"
    out.mkdir(exist_ok=True)
    write_plan_json(plan, str(out / "plan.json"))
    write_coverage_json(data, out / "coverage.json")
    return out


def _mock_config():
    config = MagicMock()
    config.coverage.output_dir = "cov-out"
    return config


_PATCH_CHANGED = {Path("player.gd"): [(5, 10)]}


def _patched_env(tmp_path: Path, changed=None):
    """Context patches for project root and changed-line collection."""
    return (
        patch(
            "gd_tools.coverage.orchestrator.find_project_root",
            return_value=tmp_path,
        ),
        patch(
            "gd_tools.coverage.orchestrator.collect_changed_lines",
            return_value=(_PATCH_CHANGED if changed is None else changed),
        ),
    )


# --- Orchestrator flow ---


def test_diff_coverage_patch_renders_table(tmp_path, capsys):
    """Text mode prints the per-file patch table with a TOTAL row."""
    _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 0}))
    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        diff_coverage_patch(_mock_config(), "main")

    out = capsys.readouterr().out
    assert "Patch coverage" in out
    assert "player.gd" in out
    assert "TOTAL" in out
    assert "1/2 (50%)" in out


def test_diff_coverage_patch_json_format(tmp_path, capsys):
    """JSON mode prints a pure, parseable patch payload."""
    _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 0}))
    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        diff_coverage_patch(_mock_config(), "main", report_format="json")

    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["totals"]["total"] == 2
    assert payload["totals"]["covered"] == 1
    assert payload["verdict"] == "informational"
    assert payload["files"][0]["path"] == "player.gd"


def test_diff_coverage_patch_gate_fail_below_threshold(tmp_path):
    """A patch rate below --patch-fail-under raises (CLI exit 1)."""
    _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 0}))
    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        with pytest.raises(CoverageThresholdError):
            diff_coverage_patch(_mock_config(), "main", fail_under=80.0)


def test_diff_coverage_patch_gate_passes_at_threshold(tmp_path):
    """A patch rate exactly at the threshold does not raise."""
    _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 1}))
    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        diff_coverage_patch(_mock_config(), "main", fail_under=100.0)


def test_diff_coverage_patch_empty_patch_never_fails(tmp_path):
    """No changed lines prints the notice and skips the gate vacuously."""
    _setup_project(tmp_path, _plan(), _data({}))
    root_patch, changed_patch = _patched_env(tmp_path, changed={})
    with root_patch, changed_patch:
        diff_coverage_patch(_mock_config(), "main", fail_under=100.0)


def test_diff_coverage_patch_combined_regression_raises(tmp_path):
    """Combined mode: regression vs baseline also produces exit 1."""
    out = _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 0}))
    # Baseline with the same plan but both lines covered -> head regressed.
    from gd_tools.coverage.diff_reporter import save_baseline

    baseline_plan = _plan()
    write_plan_json(baseline_plan, str(out / "plan_base.json"))
    write_coverage_json(_data({"0": 1, "1": 1}), out / "coverage_base.json")
    save_baseline(
        out / "plan_base.json",
        out / "coverage_base.json",
        out / "baseline.json",
    )

    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        with pytest.raises(CoverageThresholdError):
            diff_coverage_patch(
                _mock_config(),
                "main",
                fail_under=100.0,
                fail_on_regression=True,
            )


def test_diff_coverage_patch_regression_without_baseline_exit_2(tmp_path):
    """--fail-on-regression without a saved baseline is a config error."""
    _setup_project(tmp_path, _plan(), _data({"0": 1, "1": 0}))
    root_patch, changed_patch = _patched_env(tmp_path)
    with root_patch, changed_patch:
        with pytest.raises(CoveragePlanError):
            diff_coverage_patch(_mock_config(), "main", fail_on_regression=True)


# --- CLI wiring ---


def test_coverage_diff_patch_calls_orchestrator():
    """--patch delegates to diff_coverage_patch with the git-ref base."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch(
            "gd_tools.cli.diff_coverage_patch", return_value=None
        ) as mock_patch_cmd,
    ):
        result = runner.invoke(
            cli, ["coverage", "diff", "--patch", "--base", "main"]
        )
    assert result.exit_code == 0
    mock_patch_cmd.assert_called_once_with(
        mock_config,
        "main",
        report_format="text",
        fail_under=None,
        annotations=None,
        fail_on_regression=False,
    )


def test_coverage_diff_patch_options_forwarded():
    """--patch-fail-under/--patch-annotations/--report-format forward."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.diff_coverage_patch", return_value=None) as m,
    ):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "diff",
                "--patch",
                "--base",
                "main",
                "--patch-fail-under",
                "80",
                "--patch-annotations",
                "false",
                "--report-format",
                "json",
            ],
        )
    assert result.exit_code == 0
    m.assert_called_once_with(
        mock_config,
        "main",
        report_format="json",
        fail_under=80.0,
        annotations=False,
        fail_on_regression=False,
    )


def test_coverage_diff_patch_fail_under_requires_patch():
    """--patch-fail-under without --patch is a config error (exit 2)."""
    runner = CliRunner()
    with patch("gd_tools.cli.load_config", return_value=MagicMock()):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "diff",
                "--base",
                "b.json",
                "--patch-fail-under",
                "80",
            ],
        )
    assert result.exit_code == 2
    assert "--patch" in result.output


def test_coverage_diff_patch_annotations_requires_patch():
    """--patch-annotations without --patch is a config error (exit 2)."""
    runner = CliRunner()
    with patch("gd_tools.cli.load_config", return_value=MagicMock()):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "diff",
                "--base",
                "b.json",
                "--patch-annotations",
                "true",
            ],
        )
    assert result.exit_code == 2
    assert "--patch" in result.output


def test_coverage_diff_patch_show_lines_conflict():
    """--show-lines has no meaning in patch mode and is rejected."""
    runner = CliRunner()
    with patch("gd_tools.cli.load_config", return_value=MagicMock()):
        result = runner.invoke(
            cli,
            ["coverage", "diff", "--patch", "--base", "main", "--show-lines"],
        )
    assert result.exit_code == 2
    assert "--show-lines" in result.output


def test_coverage_diff_patch_fail_under_range():
    """--patch-fail-under outside 0-100 is a usage error (exit 2)."""
    runner = CliRunner()
    with patch("gd_tools.cli.load_config", return_value=MagicMock()):
        result = runner.invoke(
            cli,
            [
                "coverage",
                "diff",
                "--patch",
                "--base",
                "main",
                "--patch-fail-under",
                "150",
            ],
        )
    assert result.exit_code == 2


def test_coverage_diff_patch_threshold_error_exit_1():
    """CoverageThresholdError from the orchestrator maps to exit 1."""
    runner = CliRunner()
    with (
        patch("gd_tools.cli.load_config", return_value=MagicMock()),
        patch(
            "gd_tools.cli.diff_coverage_patch",
            side_effect=CoverageThresholdError("below threshold"),
        ),
    ):
        result = runner.invoke(
            cli, ["coverage", "diff", "--patch", "--base", "main"]
        )
    assert result.exit_code == 1


def test_coverage_diff_without_patch_unchanged():
    """Non-patch mode still delegates to the baseline diff orchestrator."""
    runner = CliRunner()
    mock_config = MagicMock()
    with (
        patch("gd_tools.cli.load_config", return_value=mock_config),
        patch("gd_tools.cli.diff_coverage", return_value=None) as mock_diff,
    ):
        result = runner.invoke(cli, ["coverage", "diff", "--base", "b.json"])
    assert result.exit_code == 0
    mock_diff.assert_called_once_with(
        mock_config,
        "b.json",
        show_lines=False,
        report_format="text",
        fail_on_regression=False,
    )
