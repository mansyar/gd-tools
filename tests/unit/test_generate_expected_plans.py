"""Unit tests for the generate_expected_plans fixture script."""

import importlib.util
import json
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
    "edge_cases_advanced",
    "ternary_anchors",
]


@pytest.fixture(scope="module")
def script():
    """Load the tools script as a module (in-process, once per module)."""
    spec = importlib.util.spec_from_file_location(
        "generate_expected_plans", _SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_regenerates_all_fixtures(tmp_path, script):
    """Script regenerates all expected plan JSON fixtures."""
    generated = script.regenerate_expected_plans(_FIXTURES_DIR, tmp_path)

    assert [path.name for path in generated] == [
        f"{name}.expected.json" for name in _FIXTURE_NAMES
    ]


def test_regenerated_fixtures_match_committed(tmp_path, script):
    """Regenerated fixtures match committed fixtures (no drift)."""
    script.regenerate_expected_plans(_FIXTURES_DIR, tmp_path)

    for name in _FIXTURE_NAMES:
        generated = json.loads(
            (tmp_path / f"{name}.expected.json").read_text(encoding="utf-8")
        )
        committed = json.loads(
            (_PLANS_DIR / f"{name}.expected.json").read_text(encoding="utf-8")
        )
        assert generated == committed, f"Drift detected in {name}.expected.json"
