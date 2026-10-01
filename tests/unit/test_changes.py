"""Unit tests for git change collection (``gd-tools test --changed``)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.changes import collect_changed_files
from gd_tools.errors import GdToolsError

pytestmark = pytest.mark.unit


def _fake_git(responses):
    """Build a subprocess.run side effect from (rc, stdout, stderr) tuples."""
    calls = iter(responses)

    def _run(args, **kwargs):
        returncode, stdout, stderr = next(calls)
        return subprocess.CompletedProcess(
            args, returncode, stdout=stdout, stderr=stderr
        )

    return MagicMock(side_effect=_run)


def test_working_tree_parses_status_porcelain(tmp_path):
    """Working-tree mode returns relative paths for modified, staged,
    untracked, deleted, and renamed entries."""
    porcelain = (
        " M src/enemy.gd\n"
        "M  tests/test_enemy.gd\n"
        "?? src/new.gd\n"
        " D old.gd\n"
        "R  a.gd -> b.gd\n"
    )
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git([(0, porcelain, "")]),
    ):
        result = collect_changed_files(tmp_path)

    assert result == [
        Path("src/enemy.gd"),
        Path("tests/test_enemy.gd"),
        Path("src/new.gd"),
        Path("old.gd"),
        Path("b.gd"),
    ]


def test_working_tree_runs_git_in_project_root(tmp_path):
    """Git is invoked with ``cwd`` set to the project root."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git([(0, "", "")]),
    ) as run:
        collect_changed_files(tmp_path)

    assert run.call_args.kwargs["cwd"] == tmp_path


def test_empty_working_tree_returns_empty_list(tmp_path):
    """A clean working tree yields no changed files."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git([(0, "", "")]),
    ):
        result = collect_changed_files(tmp_path)

    assert result == []


def test_base_mode_diffs_from_merge_base(tmp_path):
    """``--base`` diffs from merge-base(ref, HEAD) instead of the
    working tree."""

    def _run(args, **kwargs):
        if args[1] == "merge-base":
            return subprocess.CompletedProcess(
                args, 0, stdout="abc1234\n", stderr=""
            )
        assert args[1] == "diff"
        assert args[2:5] == ["--name-only", "abc1234", "HEAD"]
        return subprocess.CompletedProcess(
            args, 0, stdout="src/enemy.gd\nsrc/player.gd\n", stderr=""
        )

    with patch("gd_tools.changes.subprocess.run", _run):
        result = collect_changed_files(tmp_path, base="main")

    assert result == [Path("src/enemy.gd"), Path("src/player.gd")]


def test_base_mode_no_changes_returns_empty_list(tmp_path):
    """A base ref with no drift from HEAD yields no changed files."""

    def _run(args, **kwargs):
        if args[1] == "merge-base":
            return subprocess.CompletedProcess(
                args, 0, stdout="abc1234\n", stderr=""
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    with patch("gd_tools.changes.subprocess.run", _run):
        result = collect_changed_files(tmp_path, base="main")

    assert result == []


def test_not_a_git_repo_raises_exit_2(tmp_path):
    """Running outside a git repository is an environment error (exit 2)."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(
            [(128, "", "fatal: not a git repository (or any of the parent\n")]
        ),
    ):
        with pytest.raises(GdToolsError) as exc_info:
            collect_changed_files(tmp_path)

    assert exc_info.value.exit_code == 2
    assert "git repository" in str(exc_info.value)


def test_invalid_base_ref_raises_exit_2(tmp_path):
    """An unknown --base ref is a configuration error (exit 2) naming the ref."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(
            [
                (
                    128,
                    "",
                    "fatal: Not a valid object name 'nosuchref'\n",
                )
            ]
        ),
    ):
        with pytest.raises(GdToolsError) as exc_info:
            collect_changed_files(tmp_path, base="nosuchref")

    assert exc_info.value.exit_code == 2
    assert "nosuchref" in str(exc_info.value)


def test_base_mode_outside_git_repo_raises_exit_2(tmp_path):
    """``--base`` outside a git repository reports the repo, not the ref."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(
            [(128, "", "fatal: not a git repository (or any of the parent\n")]
        ),
    ):
        with pytest.raises(GdToolsError) as exc_info:
            collect_changed_files(tmp_path, base="main")

    assert exc_info.value.exit_code == 2
    assert "git repository" in str(exc_info.value)
    assert "nosuchref" not in str(exc_info.value)
