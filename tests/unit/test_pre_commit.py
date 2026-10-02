"""Unit tests for the ``gd-tools install-hooks`` core module
(``gd_tools.pre_commit``).

Covers the hook file generation contract from the track spec:
- per-hook entries (format / lint / test) with correct id, name, entry,
  and args,
- ``language: system`` and ``files: \\.gd$`` filters,
- ``pass_filenames: false`` for the test hook,
- selection filtering (``--hooks test`` alone → test entry only),
- idempotent file writes,
- deselected-but-present detection.

The merge-by-id logic in ``.pre-commit-config.yaml`` is covered by the
test classes at the bottom of this module.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from gd_tools.pre_commit import (
    STATUS_ADDED,
    STATUS_UPDATED,
    install_hooks,
)


def _read_yaml(path: Path):
    """Load a YAML file and return the parsed data."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# .pre-commit-hooks.yaml generation
# ---------------------------------------------------------------------------


def test_format_hook_entry_fields(tmp_path: Path):
    install_hooks(selection=("format",), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-hooks.yaml")
    entries = {hook["id"]: hook for hook in data}
    hook = entries["gd-tools-format"]
    assert hook["name"] == "gd-tools format --check"
    assert hook["entry"] == "gd-tools format --check"
    assert hook["language"] == "system"
    assert hook["files"] == r"\.gd$"


def test_lint_hook_entry_fields(tmp_path: Path):
    install_hooks(selection=("lint",), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-hooks.yaml")
    entries = {hook["id"]: hook for hook in data}
    hook = entries["gd-tools-lint"]
    assert hook["name"] == "gd-tools lint"
    assert hook["entry"] == "gd-tools lint"
    assert hook["language"] == "system"
    assert hook["files"] == r"\.gd$"


def test_test_hook_entry_fields(tmp_path: Path):
    install_hooks(selection=("test",), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-hooks.yaml")
    entries = {hook["id"]: hook for hook in data}
    hook = entries["gd-tools-test"]
    assert hook["name"] == "gd-tools test"
    assert hook["entry"] == "gd-tools test"
    assert hook["language"] == "system"
    # The test hook must not receive filenames; it runs the full suite.
    assert hook["pass_filenames"] is False
    assert "files" not in hook


def test_selection_filtering_only_test(tmp_path: Path):
    """Selecting only the test hook emits exactly that entry."""
    install_hooks(selection=("test",), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-hooks.yaml")
    ids = [hook["id"] for hook in data]
    assert ids == ["gd-tools-test"]


def test_selection_all_three_hooks(tmp_path: Path):
    install_hooks(selection=("format", "lint", "test"), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-hooks.yaml")
    ids = [hook["id"] for hook in data]
    assert ids == [
        "gd-tools-format",
        "gd-tools-lint",
        "gd-tools-test",
    ]


def test_hooks_file_write_is_idempotent(tmp_path: Path):
    """Re-running with the same selection rewrites the same content."""
    install_hooks(selection=("format",), project_root=tmp_path)
    first = (tmp_path / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    install_hooks(selection=("format",), project_root=tmp_path)
    second = (tmp_path / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    assert first == second


def test_invalid_hook_name_raises(tmp_path: Path):
    with pytest.raises(Exception):
        install_hooks(selection=("bogus",), project_root=tmp_path)


# ---------------------------------------------------------------------------
# .pre-commit-config.yaml merge-by-id
# ---------------------------------------------------------------------------

FRESH_CONFIG = "repos:\n- repo: local\n  hooks:\n"


def _foreign_config() -> str:
    return textwrap.dedent("""\
        repos:
        - repo: https://github.com/example/some-hook
          rev: v1.0.0
          hooks:
          - id: some-hook
            name: Some Hook
        """)


def test_fresh_config_creates_local_repo_block(tmp_path: Path):
    install_hooks(selection=("format", "lint"), project_root=tmp_path)
    data = _read_yaml(tmp_path / ".pre-commit-config.yaml")
    repos = data["repos"]
    local = [r for r in repos if r.get("repo") == "local"]
    assert len(local) == 1
    ids = [h["id"] for h in local[0]["hooks"]]
    assert ids == ["gd-tools-format", "gd-tools-lint"]


def test_existing_config_keeps_foreign_hooks(tmp_path: Path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(_foreign_config(), encoding="utf-8")
    install_hooks(selection=("format",), project_root=tmp_path)
    data = _read_yaml(config)
    repos = data["repos"]
    foreign = [r for r in repos if r.get("repo") != "local"]
    assert len(foreign) == 1
    assert foreign[0]["hooks"][0]["id"] == "some-hook"
    local = [r for r in repos if r.get("repo") == "local"]
    assert len(local) == 1
    assert [h["id"] for h in local[0]["hooks"]] == ["gd-tools-format"]


def test_existing_local_block_updates_drifted_entries(tmp_path: Path):
    """A drifted gd-tools entry is corrected in place, not duplicated."""
    config = tmp_path / ".pre-commit-config.yaml"
    drifted = textwrap.dedent("""\
        repos:
        - repo: local
          hooks:
          - id: gd-tools-format
            name: gd-tools format --check
            entry: gd-tools format
            language: system
            files: \\.gd$
        """)
    config.write_text(drifted, encoding="utf-8")
    result = install_hooks(selection=("format",), project_root=tmp_path)
    data = _read_yaml(config)
    hooks = data["repos"][0]["hooks"]
    assert len(hooks) == 1
    assert hooks[0]["entry"] == "gd-tools format --check"
    assert result.hooks[0].status == STATUS_UPDATED


def test_new_entries_added_alongside_existing_gd_tools_entries(
    tmp_path: Path,
):
    config = tmp_path / ".pre-commit-config.yaml"
    existing = textwrap.dedent("""\
        repos:
        - repo: local
          hooks:
          - id: gd-tools-format
            name: gd-tools format --check
            entry: gd-tools format --check
            language: system
            files: \\.gd$
        """)
    config.write_text(existing, encoding="utf-8")
    result = install_hooks(selection=("format", "test"), project_root=tmp_path)
    data = _read_yaml(config)
    hooks = data["repos"][0]["hooks"]
    ids = [h["id"] for h in hooks]
    assert ids == ["gd-tools-format", "gd-tools-test"]
    by_status = {h.name: h.status for h in result.hooks}
    assert by_status["format"] == STATUS_UPDATED
    assert by_status["test"] == STATUS_ADDED


def test_deselected_but_present_hooks_are_reported_and_kept(
    tmp_path: Path,
):
    """A previously-added hook left out of the new selection is kept."""
    config = tmp_path / ".pre-commit-config.yaml"
    existing = textwrap.dedent("""\
        repos:
        - repo: local
          hooks:
          - id: gd-tools-lint
            name: gd-tools lint
            entry: gd-tools lint
            language: system
            files: \\.gd$
        """)
    config.write_text(existing, encoding="utf-8")
    result = install_hooks(selection=("format",), project_root=tmp_path)
    data = _read_yaml(config)
    ids = [h["id"] for h in data["repos"][0]["hooks"]]
    assert ids == ["gd-tools-lint", "gd-tools-format"]
    assert result.deselected_present == ("lint",)


def test_malformed_config_yaml_raises_config_error(tmp_path: Path):
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("repos: [unclosed", encoding="utf-8")
    from gd_tools.errors import GdToolsError

    with pytest.raises(GdToolsError) as excinfo:
        install_hooks(selection=("format",), project_root=tmp_path)
    assert excinfo.value.exit_code == 2


def test_invalid_selection_returns_nothing_to_do(tmp_path: Path):
    """An empty selection reports nothing-to-do (exit 1 status)."""
    result = install_hooks(selection=(), project_root=tmp_path)
    assert result.status == "nothing-to-do"


def test_install_result_reports_written_paths(tmp_path: Path):
    result = install_hooks(selection=("format",), project_root=tmp_path)
    assert result.hooks_file == tmp_path / ".pre-commit-hooks.yaml"
    assert result.config_file == tmp_path / ".pre-commit-config.yaml"
    assert result.status == "installed"


def test_empty_existing_config_file_treated_as_fresh(tmp_path: Path):
    """An empty (or whitespace) existing config parses as None → fresh."""
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("", encoding="utf-8")
    install_hooks(selection=("lint",), project_root=tmp_path)
    data = _read_yaml(config)
    ids = [h["id"] for h in data["repos"][0]["hooks"]]
    assert ids == ["gd-tools-lint"]


def test_config_with_scalar_body_normalized(tmp_path: Path):
    """A non-mapping config body is replaced with a valid skeleton."""
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("- just\n- a\n- list\n", encoding="utf-8")
    install_hooks(selection=("lint",), project_root=tmp_path)
    data = _read_yaml(config)
    ids = [h["id"] for h in data["repos"][0]["hooks"]]
    assert ids == ["gd-tools-lint"]


def test_config_with_scalar_repos_normalized(tmp_path: Path):
    """A config whose ``repos`` key is not a list is normalized."""
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("repos: bogus\n", encoding="utf-8")
    install_hooks(selection=("lint",), project_root=tmp_path)
    data = _read_yaml(config)
    ids = [h["id"] for h in data["repos"][0]["hooks"]]
    assert ids == ["gd-tools-lint"]


def test_local_block_without_hooks_key_normalized(tmp_path: Path):
    """A ``repo: local`` block missing its hooks list gains one."""
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("repos:\n- repo: local\n", encoding="utf-8")
    install_hooks(selection=("lint",), project_root=tmp_path)
    data = _read_yaml(config)
    ids = [h["id"] for h in data["repos"][0]["hooks"]]
    assert ids == ["gd-tools-lint"]
