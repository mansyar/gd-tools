"""Unit tests for the format runner module.

Covers FormatResult dataclass, run_format function with all modes
(default, --check, --diff), mutual exclusion, syntax error handling,
and no-files-found edge case.
"""

from gd_tools.config import GdToolsConfig
from gd_tools.errors import FormatError
from gd_tools.format_runner import FormatResult, run_format

import pytest

pytestmark = pytest.mark.unit

# --- FormatResult dataclass ---


def test_format_result_defaults():
    """Test FormatResult instantiation with default values."""
    result = FormatResult()
    assert result.files_checked == 0
    assert result.files_formatted == 0
    assert result.files_needing_format == 0
    assert result.files_needing_format_paths == []
    assert result.diffs == []


def test_format_result_all_fields():
    """Test FormatResult with all fields populated."""
    result = FormatResult(
        files_checked=10,
        files_formatted=7,
        files_needing_format=3,
        files_needing_format_paths=["a.gd", "b.gd", "c.gd"],
        diffs=["diff1", "diff2"],
    )
    assert result.files_checked == 10
    assert result.files_formatted == 7
    assert result.files_needing_format == 3
    assert result.files_needing_format_paths == ["a.gd", "b.gd", "c.gd"]
    assert result.diffs == ["diff1", "diff2"]


# --- run_format default mode (format in place) ---


def test_run_format_formats_unformatted_file(tmp_path):
    """Test run_format formats an unformatted .gd file in place."""
    # Unformatted: missing blank lines, wrong indentation
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    assert result.files_checked == 1
    assert result.files_formatted == 1
    assert result.files_needing_format == 0
    assert result.diffs == []
    # File should have been changed
    content = (tmp_path / "player.gd").read_text()
    assert content != "extends Node\nfunc _ready():\n    pass\n"


def test_run_format_already_formatted_file(tmp_path):
    """Test run_format on already-formatted files makes no changes."""
    from gdtoolkit.formatter import format_code

    # Format the content first, then write it
    formatted = format_code(
        "extends Node\nfunc _ready():\n    pass\n", max_line_length=100
    )
    (tmp_path / "player.gd").write_text(formatted)
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    assert result.files_checked == 1
    assert result.files_formatted == 0
    assert result.files_needing_format == 0
    # File should be unchanged
    assert (tmp_path / "player.gd").read_text() == formatted


def test_run_format_multiple_files(tmp_path):
    """Test run_format with multiple .gd files."""
    (tmp_path / "a.gd").write_text("extends Node\nfunc _ready():\n    pass\n")
    (tmp_path / "b.gd").write_text("extends Node2D\nfunc _init():\n    pass\n")
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    assert result.files_checked == 2
    assert result.files_formatted == 2


def test_run_format_uses_discover_gd_files(tmp_path):
    """Test run_format uses discover_gd_files for file enumeration."""
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    # Non-.gd file should be ignored
    (tmp_path / "readme.txt").write_text("hello\n")
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    assert result.files_checked == 1


# --- run_format --check mode ---


def test_run_format_check_reports_unformatted(tmp_path):
    """Test --check reports files_needing_format count for unformatted files."""
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), check=True)

    assert result.files_checked == 1
    assert result.files_needing_format == 1
    assert result.files_formatted == 0
    assert len(result.files_needing_format_paths) == 1
    assert "player.gd" in result.files_needing_format_paths[0]


def test_run_format_check_already_formatted(tmp_path):
    """Test --check returns 0 files_needing_format for already-formatted files."""
    from gdtoolkit.formatter import format_code

    formatted = format_code(
        "extends Node\nfunc _ready():\n    pass\n", max_line_length=100
    )
    (tmp_path / "player.gd").write_text(formatted)
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), check=True)

    assert result.files_checked == 1
    assert result.files_needing_format == 0
    assert result.files_needing_format_paths == []


def test_run_format_check_does_not_modify(tmp_path):
    """Test --check does not modify files on disk."""
    original = "extends Node\nfunc _ready():\n    pass\n"
    (tmp_path / "player.gd").write_text(original)
    config = GdToolsConfig()

    run_format(config, str(tmp_path), check=True)

    assert (tmp_path / "player.gd").read_text() == original


# --- run_format --diff mode ---


def test_run_format_diff_returns_diffs(tmp_path):
    """Test --diff returns list of unified diff strings."""
    (tmp_path / "player.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), diff=True)

    assert result.files_checked == 1
    assert len(result.diffs) == 1
    assert isinstance(result.diffs[0], str)
    assert "player.gd" in result.diffs[0]


def test_run_format_diff_does_not_modify(tmp_path):
    """Test --diff does not modify files on disk."""
    original = "extends Node\nfunc _ready():\n    pass\n"
    (tmp_path / "player.gd").write_text(original)
    config = GdToolsConfig()

    run_format(config, str(tmp_path), diff=True)

    assert (tmp_path / "player.gd").read_text() == original


def test_run_format_diff_already_formatted(tmp_path):
    """Test --diff returns empty diffs list for already-formatted files."""
    from gdtoolkit.formatter import format_code

    formatted = format_code(
        "extends Node\nfunc _ready():\n    pass\n", max_line_length=100
    )
    (tmp_path / "player.gd").write_text(formatted)
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), diff=True)

    assert result.files_checked == 1
    assert result.diffs == []


# --- run_format mutual exclusion ---


def test_run_format_mutual_exclusion_raises(tmp_path):
    """Test check=True and diff=True raises FormatError with exit_code=2."""
    config = GdToolsConfig()

    try:
        run_format(config, str(tmp_path), check=True, diff=True)
        assert False, "Should have raised FormatError"
    except FormatError as e:
        assert e.exit_code == 2
        assert "mutually exclusive" in str(e)


# --- run_format syntax error handling ---


def test_run_format_syntax_error_continues(tmp_path, capsys):
    """Test syntax-error .gd file does not crash, continues processing."""
    # Valid file
    (tmp_path / "valid.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    # Syntax error file (missing function name)
    (tmp_path / "broken.gd").write_text("extends Node\nfunc ():\n    pass\n")
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    # Valid file should still be formatted
    assert result.files_checked == 2
    assert result.files_formatted == 1
    # Syntax error should be reported to stderr with file path
    captured = capsys.readouterr()
    assert "broken.gd" in captured.err
    assert "Warning" in captured.err


def test_run_format_syntax_error_in_check_mode(tmp_path):
    """Test syntax error handling in --check mode."""
    (tmp_path / "valid.gd").write_text(
        "extends Node\nfunc _ready():\n    pass\n"
    )
    (tmp_path / "broken.gd").write_text("extends Node\nfunc ():\n    pass\n")
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), check=True)

    assert result.files_checked == 2
    assert result.files_needing_format == 1
    assert len(result.files_needing_format_paths) == 1
    assert "valid.gd" in result.files_needing_format_paths[0]


# --- run_format no files found ---


def test_run_format_no_files(tmp_path):
    """Test run_format on empty directory returns FormatResult with all zeros."""
    (tmp_path / "readme.txt").write_text("hello\n")
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path))

    assert result.files_checked == 0
    assert result.files_formatted == 0
    assert result.files_needing_format == 0
    assert result.diffs == []


def test_run_format_no_files_check_mode(tmp_path):
    """Test run_format --check on empty directory returns zeros."""
    config = GdToolsConfig()

    result = run_format(config, str(tmp_path), check=True)

    assert result.files_checked == 0
    assert result.files_needing_format == 0
