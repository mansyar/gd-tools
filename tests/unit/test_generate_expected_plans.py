"""Unit tests for the generate_expected_plans fixture script."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "tools"
    / "generate_expected_plans.py"
)
_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "gdscript"
_PLANS_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "plans"

_FIXTURE_NAMES = [
    "simple",
    "branches",
    "loops",
    "match_stmt",
    "nested",
    "edge_cases",
]


def test_script_regenerates_all_fixtures(tmp_path):
    """Script runs and regenerates all 6 expected plan JSON fixtures."""
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--fixtures-dir",
            str(_FIXTURES_DIR),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    for name in _FIXTURE_NAMES:
        json_file = tmp_path / f"{name}.expected.json"
        assert json_file.exists(), f"Missing {json_file}"


def test_regenerated_fixtures_match_committed(tmp_path):
    """Regenerated fixtures match committed fixtures (no drift)."""
    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--fixtures-dir",
            str(_FIXTURES_DIR),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    for name in _FIXTURE_NAMES:
        generated = json.loads(
            (tmp_path / f"{name}.expected.json").read_text(encoding="utf-8")
        )
        committed = json.loads(
            (_PLANS_DIR / f"{name}.expected.json").read_text(encoding="utf-8")
        )
        assert generated == committed, f"Drift detected in {name}.expected.json"
