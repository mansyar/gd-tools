"""Unit tests for changed-line-range extraction (patch coverage)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gd_tools.changes import collect_changed_lines
from gd_tools.errors import GitChangeError

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


def _diff_output(*bodies):
    """Join per-file unified-diff bodies into one ``git diff -U0`` stdout."""
    return "\n".join(bodies)


MODIFIED_TWO_HUNKS = _diff_output(
    """diff --git a/src/enemy.gd b/src/enemy.gd
--- a/src/enemy.gd
+++ b/src/enemy.gd
@@ -10,0 +11,2 @@ func take_damage(amount):
+new line one
+new line two
@@ -40,0 +43,2 @@ func heal():
+heal line one
+heal line two
""",
)

NEW_FILE = _diff_output(
    """diff --git a/src/new.gd b/src/new.gd
new file mode 100644
--- /dev/null
+++ b/src/new.gd
@@ -0,0 +1,3 @@
+extends Node
+
+func ready() -> void:
""",
)

DELETED_FILE = _diff_output(
    """diff --git a/src/old.gd b/src/old.gd
deleted file mode 100644
--- a/src/old.gd
+++ /dev/null
@@ -1,3 +0,0 @@
-extends Node
-
-func gone() -> void:
""",
)

NON_GD_FILE = _diff_output(
    """diff --git a/scene.tscn b/scene.tscn
--- a/scene.tscn
+++ b/scene.tscn
@@ -1,0 +2,1 @@
+extra = true
""",
)

PURE_DELETION_HUNK = _diff_output(
    """diff --git a/src/prune.gd b/src/prune.gd
--- a/src/prune.gd
+++ b/src/prune.gd
@@ -5,3 +4,0 @@ func gone():
-dead one
-dead two
-dead three
""",
)


def _merge_base_then_diff(diff_stdout, diff_rc=0):
    """Responses for merge-base followed by ``git diff -U0``."""
    return [(0, "abc1234\n", ""), (diff_rc, diff_stdout, "")]


def test_modified_file_parses_added_line_ranges(tmp_path):
    """Added lines from each hunk become inclusive (start, end) ranges."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(MODIFIED_TWO_HUNKS)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {
        Path("src/enemy.gd"): [(11, 12), (43, 44)],
    }


def test_new_file_counts_every_line(tmp_path):
    """A brand-new file's full content is one added-line range."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(NEW_FILE)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {Path("src/new.gd"): [(1, 3)]}


def test_deleted_file_is_excluded(tmp_path):
    """Deleted files have no added side and must not appear."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(DELETED_FILE)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {}


def test_non_gd_files_are_filtered_out(tmp_path):
    """Only .gd files contribute to the patch."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(NON_GD_FILE)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {}


def test_pure_deletion_hunk_contributes_nothing(tmp_path):
    """A hunk that only removes lines yields no added range."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(PURE_DELETION_HUNK)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {Path("src/prune.gd"): []}


def test_multiple_files_keep_all_ranges(tmp_path):
    """Ranges from several files are collected in one pass."""
    combined = _diff_output(NEW_FILE, MODIFIED_TWO_HUNKS, DELETED_FILE)
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff(combined)),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {
        Path("src/new.gd"): [(1, 3)],
        Path("src/enemy.gd"): [(11, 12), (43, 44)],
    }


def test_empty_diff_returns_empty_dict(tmp_path):
    """No changes since the merge-base yields no entries."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff("")),
    ):
        result = collect_changed_lines(tmp_path, "main")

    assert result == {}


def test_unknown_base_ref_raises(tmp_path):
    """A resolvable-failure merge-base raises GitChangeError."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git([(1, "", "fatal: bad revision 'nope'")]),
    ):
        with pytest.raises(GitChangeError) as excinfo:
            collect_changed_lines(tmp_path, "nope")

    assert "nope" in str(excinfo.value)


def test_git_runs_in_project_root(tmp_path):
    """Git is invoked with ``cwd`` set to the project root."""
    with patch(
        "gd_tools.changes.subprocess.run",
        _fake_git(_merge_base_then_diff("")),
    ) as run:
        collect_changed_lines(tmp_path, "main")

    assert run.call_args.kwargs["cwd"] == tmp_path
