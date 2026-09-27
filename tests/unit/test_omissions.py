"""Tests for coverage-target omission reconciliation (spec R3, R5).

R3 makes the instrumented set derivable because both collectors seed an empty
hit entry for every file they successfully instrument. That is what lets a
plan-versus-data diff separate the two cases this track exists to tell apart:

- a target that could **not** be instrumented, which is an omission, and
- a target that **was** instrumented but never executed, which is not.

A naive diff gets the second one wrong, because both are absent from a
coverage file that only records files which were hit. These tests pin the
distinction, and pin the fallback so the two can never silently disagree
about *what* happened.

The `omitted` key added to the coverage data JSON (spec R5) is authoritative
for **reasons only**. Which targets were omitted stays derived from
``plan.files - data.files``, because that is the definition R3 made reliable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gd_tools.coverage.omissions import OmissionReport, reconcile_omissions
from gd_tools.coverage.plan_generator import read_plan_json
from gd_tools.coverage.reporter import (
    CoverageData,
    CoveragePlanError,
    FileCoverage,
    OmittedTarget,
    read_coverage_json,
)

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PLAN_FIXTURE = _FIXTURES_DIR / "coverage_plans" / "test_plan.json"

# The fixture plan has two files: `res://player.gd` (file_id 0, five lines) and
# `res://enemy.gd` (file_id 1, three lines).
_PLAYER = "res://player.gd"
_ENEMY = "res://enemy.gd"


@pytest.fixture
def plan():
    """A two-file plan: player.gd (file_id 0) and enemy.gd (file_id 1)."""
    return read_plan_json(_PLAN_FIXTURE)


def _player_hits() -> dict[str, int]:
    return {"0": 3, "1": 2, "2": 1, "3": 1, "4": 3}


def _entry(file_id: int, hits: dict[str, int]) -> FileCoverage:
    """A coverage data entry. An empty `hits` is the R3 seeding signal."""
    return FileCoverage(file_id=file_id, hits=hits)


# --- No omissions -----------------------------------------------------------


def test_no_omissions_when_every_plan_target_was_instrumented(plan):
    """Every plan target is present in the data, so nothing is omitted."""
    data = CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[
            # Both files seeded. The empty hits entry is the R3 signal that this
            # file was instrumented but never executed -- still not an omission.
            _entry(0, _player_hits()),
            _entry(1, {}),
        ],
    )

    report = reconcile_omissions(plan, data)

    assert report.omitted == []
    assert report.has_omissions is False
    assert report.plan_count == 2
    assert report.instrumented_count == 2


# --- Some omitted -----------------------------------------------------------


def test_omitted_target_is_identified_with_its_reason(plan):
    """A target absent from the data and declared in `omitted` is reported."""
    data = CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[_entry(0, _player_hits())],
        omitted=[
            OmittedTarget(
                file_id=1,
                path=_ENEMY,
                reason="the coverage plan references a file that no longer exists",
                fix="the plan is stale; re-run with --no-cache to regenerate it",
            )
        ],
    )

    report = reconcile_omissions(plan, data)

    assert report.has_omissions is True
    assert report.plan_count == 2
    assert report.instrumented_count == 1
    assert [t.path for t in report.omitted] == [_ENEMY]
    assert report.omitted[0].reason.startswith("the coverage plan references")
    assert "--no-cache" in report.omitted[0].fix


def test_stale_plan_and_broken_script_stay_distinguishable(plan):
    """R4: the two omissions keep their distinct reasons through reconciliation.

    A stale plan and a broken script are different bugs with different fixes, so
    collapsing them into one generic message would discard exactly the
    information R4 exists to preserve.
    """
    data = CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[],
        omitted=[
            OmittedTarget(
                file_id=0,
                path=_PLAYER,
                reason="the coverage plan references a file that no longer exists",
                fix="re-run with --no-cache",
            ),
            OmittedTarget(
                file_id=1,
                path=_ENEMY,
                reason="the file exists but does not load as GDScript",
                fix="fix the script, or exclude it from the plan",
            ),
        ],
    )

    report = reconcile_omissions(plan, data)

    by_path = {t.path: t for t in report.omitted}
    assert set(by_path) == {_PLAYER, _ENEMY}
    assert "no longer exists" in by_path[_PLAYER].reason
    assert "--no-cache" in by_path[_PLAYER].fix
    assert "does not load" in by_path[_ENEMY].reason
    # The broken-script case must not send the user off to regenerate the plan.
    assert "--no-cache" not in by_path[_ENEMY].fix


def test_every_omission_carries_a_reason_and_a_fix(plan):
    """R4/R5: an omission with no reason would be a silence, so fall back."""
    data = CoverageData(version=1, generated_at="2026-09-28T00:00:00Z", files=[])

    report = reconcile_omissions(plan, data)

    assert len(report.omitted) == 2
    for target in report.omitted:
        assert target.reason.strip(), f"{target.path} has no reason"
        assert target.fix.strip(), f"{target.path} has no fix hint"


def test_omission_undeclared_in_the_key_is_still_reported(plan):
    """A target missing from the data AND from `omitted` is still an omission.

    `omitted` supplies reasons, not identity. If the two ever disagreed about
    which files were instrumented, the definition R3 made reliable has to win,
    or a broken file could be reported as clean.
    """
    data = CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[_entry(0, _player_hits())],
        omitted=[
            # Declares file 0, which the data shows was instrumented. The data
            # wins: file 0 is not an omission.
            OmittedTarget(file_id=0, path=_PLAYER, reason="stale", fix="regen"),
        ],
    )

    report = reconcile_omissions(plan, data)

    assert [t.path for t in report.omitted] == [_ENEMY]
    assert report.instrumented_count == 1


# --- The critical case (R3) -------------------------------------------------


def test_instrumented_but_never_executed_is_not_an_omission(plan):
    """The case a naive plan-versus-data diff gets wrong.

    An instrumented file that nothing executed has empty hits. Before R3 it was
    absent from the coverage file, exactly like a file that failed to
    instrument, so a diff would have reported it as an omission. The collectors
    now seed an empty entry, so it is present and is correctly not an omission.
    """
    data = CoverageData(
        version=1,
        generated_at="2026-09-28T00:00:00Z",
        files=[_entry(0, _player_hits()), _entry(1, {})],
    )

    report = reconcile_omissions(plan, data)

    assert report.omitted == []
    assert report.instrumented_count == 2, (
        "the empty-hits entry is the R3 signal that enemy.gd was instrumented"
    )


# --- Parsing the additive `omitted` key ------------------------------------


def test_read_coverage_json_parses_the_omitted_key(tmp_path):
    """The additive key is read when present."""
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00Z",
                "files": [{"file_id": 0, "hits": {"0": 1}}],
                "omitted": [
                    {
                        "file_id": 1,
                        "path": _ENEMY,
                        "reason": "no longer exists",
                        "fix": "re-run with --no-cache",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    data = read_coverage_json(path)

    assert len(data.omitted) == 1
    assert data.omitted[0].file_id == 1
    assert data.omitted[0].path == _ENEMY
    assert data.omitted[0].fix.endswith("--no-cache")


def test_read_coverage_json_defaults_to_no_omissions_when_the_key_is_absent(
    tmp_path,
):
    """R5 backward compatibility: data written by an older gd-tools still parses."""
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00Z",
                "files": [{"file_id": 0, "hits": {"0": 1}}],
            }
        ),
        encoding="utf-8",
    )

    data = read_coverage_json(path)

    assert data.omitted == []


def test_read_coverage_json_tolerates_an_omitted_entry_without_a_fix(tmp_path):
    """`fix` is optional; `reason` is not. A reasonless omission is a silence."""
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00Z",
                "files": [],
                "omitted": [{"file_id": 1, "path": _ENEMY, "reason": "broken"}],
            }
        ),
        encoding="utf-8",
    )

    data = read_coverage_json(path)

    assert data.omitted[0].reason == "broken"
    assert data.omitted[0].fix == ""


def test_read_coverage_json_rejects_a_malformed_omitted_key(tmp_path):
    """The new field is validated like every other field, not trusted."""
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00Z",
                "files": [],
                "omitted": {"not": "a list"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CoveragePlanError, match="omitted"):
        read_coverage_json(path)


def test_read_coverage_json_rejects_an_omission_without_a_reason(tmp_path):
    """A reasonless entry is rejected rather than silently defaulted."""
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "generated_at": "2026-09-28T00:00:00Z",
                "files": [],
                "omitted": [{"file_id": 1, "path": _ENEMY}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CoveragePlanError, match="reason"):
        read_coverage_json(path)


# --- Report shape -----------------------------------------------------------


def test_omission_report_is_falsy_when_empty_and_truthy_when_not(plan):
    """Call sites should be able to branch on the report without inspecting it."""
    empty = reconcile_omissions(
        plan,
        CoverageData(
            version=1,
            generated_at="2026-09-28T00:00:00Z",
            files=[_entry(0, _player_hits()), _entry(1, {})],
        ),
    )
    populated = reconcile_omissions(
        plan, CoverageData(version=1, generated_at="2026-09-28T00:00:00Z", files=[])
    )

    assert not empty
    assert populated
    assert isinstance(populated, OmissionReport)
