"""Regression tests for native coverage plan exclusions and schema."""

import json
from pathlib import Path

import pytest

from gd_tools.coverage.plan_generator import generate_plan
from gd_tools.coverage.reporter import read_coverage_json

pytestmark = pytest.mark.unit


def test_native_plan_excludes_managed_addon_and_test_directories(tmp_path):
    """Application plans do not include the native addon or test files."""
    (tmp_path / "project.godot").touch()
    for relative_path in (
        "scripts/app.gd",
        "test/native_test.gd",
        "addons/gd-tools-test/runtime.gd",
        ".godot/cache.gd",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("extends Node\n", encoding="utf-8")

    plan = generate_plan(tmp_path)

    assert [file.path for file in plan.files] == ["res://scripts/app.gd"]


def test_native_coverage_data_remains_readable_by_reporter(tmp_path):
    """Native v1 coverage data uses the existing reporter contract."""
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "test",
                "files": [{"file_id": 0, "hits": {"0": 2}}],
            }
        ),
        encoding="utf-8",
    )

    coverage = read_coverage_json(coverage_path)

    assert coverage.version == 1
    assert coverage.files[0].file_id == 0
    assert coverage.files[0].hits == {"0": 2}


def test_native_coverage_data_file_is_not_created_without_output(tmp_path):
    """The reporter's missing-file error remains actionable."""
    from gd_tools.errors import CoveragePlanError

    with pytest.raises(CoveragePlanError, match="Coverage data file not found"):
        read_coverage_json(Path(tmp_path) / "missing-coverage.json")
