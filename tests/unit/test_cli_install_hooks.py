"""Unit tests for the ``gd-tools install-hooks`` CLI command.

Covers selection resolution (prompt, --all, --hooks, --non-interactive),
non-TTY default behavior, exit codes (0 installed, 1 nothing-to-do,
2 config/environment error), and generated-file side effects.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml
import pytest
from click.testing import CliRunner

from gd_tools.cli import cli

pytestmark = pytest.mark.unit


def _invoke_in(tmp_path: Path, args: list[str], input: str | None = None):
    """Invoke the CLI inside ``tmp_path`` (cwd switch like other suites)."""
    import os

    runner = CliRunner()
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return runner.invoke(cli, args, input=input)
    finally:
        os.chdir(cwd)


def _hook_ids(config: Path) -> list[str]:
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    ids: list[str] = []
    for repo in data.get("repos", []):
        if repo.get("repo") == "local":
            ids.extend(h["id"] for h in repo.get("hooks", []))
    return ids


# ------------------------------------------------------------------
# Non-TTY default behavior
# ------------------------------------------------------------------


def test_no_tty_no_flags_installs_default_pair(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks"])
    assert result.exit_code == 0
    assert (tmp_path / ".pre-commit-hooks.yaml").exists()
    config = tmp_path / ".pre-commit-config.yaml"
    assert config.exists()
    assert _hook_ids(config) == ["gd-tools-format", "gd-tools-lint"]
    # No prompt was shown.
    assert "Install" not in result.output or result.output.count("?") == 0


def test_no_tty_with_all_installs_three_hooks(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks", "--all"])
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == [
        "gd-tools-format",
        "gd-tools-lint",
        "gd-tools-test",
    ]


# ------------------------------------------------------------------
# Explicit flags
# ------------------------------------------------------------------


def test_hooks_flag_selects_only_named_hooks(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks", "--hooks", "test"])
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == ["gd-tools-test"]


def test_hooks_flag_accepts_comma_separated_values(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks", "--hooks", "format,lint"])
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == ["gd-tools-format", "gd-tools-lint"]


def test_hooks_flag_deduplicates_selection(tmp_path: Path):
    """A repeated hook name installs exactly one entry."""
    result = _invoke_in(tmp_path, ["install-hooks", "--hooks", "format,format"])
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == ["gd-tools-format"]
    hooks_data = yaml.safe_load(
        (tmp_path / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
    )
    assert [h["id"] for h in hooks_data] == ["gd-tools-format"]


def test_hooks_flag_with_unknown_name_exits_2(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks", "--hooks", "bogus"])
    assert result.exit_code == 2
    assert "bogus" in result.output


def test_hooks_flag_with_no_values_exits_1(tmp_path: Path):
    """An explicit-but-empty selection resolves to nothing-to-do (exit 1)."""
    result = _invoke_in(tmp_path, ["install-hooks", "--hooks"])
    assert result.exit_code == 1
    assert not (tmp_path / ".pre-commit-config.yaml").exists()


def test_non_interactive_installs_default_pair(tmp_path: Path):
    result = _invoke_in(tmp_path, ["install-hooks", "--non-interactive"])
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == ["gd-tools-format", "gd-tools-lint"]


# ------------------------------------------------------------------
# Interactive prompt
# ------------------------------------------------------------------


def test_prompt_defaults_accept_format_and_lint_decline_test(tmp_path: Path):
    """y/y/n answers (accepting defaults) install format + lint only."""
    with patch("gd_tools.cli._stdin_is_tty", return_value=True):
        result = _invoke_in(tmp_path, ["install-hooks"], input="y\ny\nn\n")
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == ["gd-tools-format", "gd-tools-lint"]


def test_prompt_accept_all_installs_three_hooks(tmp_path: Path):
    with patch("gd_tools.cli._stdin_is_tty", return_value=True):
        result = _invoke_in(tmp_path, ["install-hooks"], input="y\ny\ny\n")
    assert result.exit_code == 0
    config = tmp_path / ".pre-commit-config.yaml"
    assert _hook_ids(config) == [
        "gd-tools-format",
        "gd-tools-lint",
        "gd-tools-test",
    ]


def test_rerun_reports_present_but_deselected_hooks(tmp_path: Path):
    """A deselected hook still in the config is reported, not removed."""
    _invoke_in(tmp_path, ["install-hooks", "--all"])
    result = _invoke_in(tmp_path, ["install-hooks", "--non-interactive"])
    assert result.exit_code == 0
    assert "Present but not selected: test" in result.output
    config = tmp_path / ".pre-commit-config.yaml"
    assert "gd-tools-test" in _hook_ids(config)


# ------------------------------------------------------------------
# Exit codes and error handling
# ------------------------------------------------------------------


def test_malformed_existing_config_exits_2(tmp_path: Path):
    (tmp_path / ".pre-commit-config.yaml").write_text(
        "repos: [unclosed", encoding="utf-8"
    )
    result = _invoke_in(tmp_path, ["install-hooks", "--non-interactive"])
    assert result.exit_code == 2
    assert "pre-commit-config.yaml" in result.output


def test_rerun_updates_drifted_entries_and_exits_0(tmp_path: Path):
    _invoke_in(tmp_path, ["install-hooks", "--non-interactive"])
    # Drift the format entry by hand.
    config = tmp_path / ".pre-commit-config.yaml"
    data = yaml.safe_load(config.read_text(encoding="utf-8"))
    for repo in data["repos"]:
        if repo.get("repo") == "local":
            for hook in repo["hooks"]:
                if hook["id"] == "gd-tools-format":
                    hook["entry"] = "gd-tools format"
    config.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    result = _invoke_in(tmp_path, ["install-hooks", "--non-interactive"])
    assert result.exit_code == 0
    assert _hook_ids(tmp_path / ".pre-commit-config.yaml") == [
        "gd-tools-format",
        "gd-tools-lint",
    ]


# ------------------------------------------------------------------
# Help
# ------------------------------------------------------------------


def test_help_documents_flags():
    result = _invoke_in(Path.cwd(), ["install-hooks", "--help"])
    assert result.exit_code == 0
    for flag in ["--all", "--hooks", "--non-interactive"]:
        assert flag in result.output
