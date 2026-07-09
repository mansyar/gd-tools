"""Unit tests for the configuration system (Pydantic models)."""

import pytest
from pydantic import ValidationError

from gd_tools.config import (
    DEFAULT_EXCLUDES,
    CoverageConfig,
    FormatConfig,
    GdToolsConfig,
    GodotConfig,
    LintConfig,
    TestConfig,
)

# --- DEFAULT_EXCLUDES constant ---


def test_default_excludes_value():
    """Test DEFAULT_EXCLUDES has the correct value."""
    assert DEFAULT_EXCLUDES == ["addons", ".godot", ".gd-tools", ".git"]


# --- GodotConfig ---


def test_godot_config_default_binary_none():
    """Test GodotConfig defaults to binary=None."""
    config = GodotConfig()
    assert config.binary is None


def test_godot_config_accepts_binary_path():
    """Test GodotConfig accepts a binary path."""
    config = GodotConfig(binary="/usr/local/bin/godot")
    assert config.binary == "/usr/local/bin/godot"


# --- TestConfig ---


def test_test_config_defaults():
    """Test TestConfig has correct default values."""
    config = TestConfig()
    assert config.test_dirs == ["test", "tests"]
    assert config.prefix == "test_"
    assert config.suffix == ".gd"
    assert config.gutconfig == ".gutconfig.json"


# --- LintConfig ---


def test_lint_config_defaults():
    """Test LintConfig defaults to DEFAULT_EXCLUDES."""
    config = LintConfig()
    assert config.exclude == DEFAULT_EXCLUDES


# --- FormatConfig ---


def test_format_config_defaults():
    """Test FormatConfig defaults to DEFAULT_EXCLUDES."""
    config = FormatConfig()
    assert config.exclude == DEFAULT_EXCLUDES


# --- CoverageConfig ---


def test_coverage_config_defaults():
    """Test CoverageConfig has correct default values."""
    config = CoverageConfig()
    assert config.enabled is False
    assert config.min_percent == 0
    assert config.format == "html"
    assert config.output_dir == ".gd-tools/coverage"
    assert config.exclude == DEFAULT_EXCLUDES
    assert config.test_dirs == ["test", "tests"]


# --- GdToolsConfig ---


def test_gd_tools_config_defaults():
    """Test GdToolsConfig has all sections with defaults."""
    config = GdToolsConfig()
    assert isinstance(config.godot, GodotConfig)
    assert isinstance(config.test, TestConfig)
    assert isinstance(config.lint, LintConfig)
    assert isinstance(config.format, FormatConfig)
    assert isinstance(config.coverage, CoverageConfig)
    # Spot-check some defaults
    assert config.godot.binary is None
    assert config.test.prefix == "test_"
    assert config.lint.exclude == DEFAULT_EXCLUDES


@pytest.mark.parametrize("fmt", ["html", "lcov", "cobertura", "text"])
def test_gd_tools_config_valid_coverage_formats(fmt):
    """Test GdToolsConfig accepts all valid coverage format values."""
    config = GdToolsConfig(coverage=CoverageConfig(format=fmt))
    assert config.coverage.format == fmt


@pytest.mark.parametrize("min_pct", [0, 50, 100])
def test_gd_tools_config_valid_min_percent(min_pct):
    """Test GdToolsConfig accepts boundary and mid-range min_percent."""
    config = GdToolsConfig(coverage=CoverageConfig(min_percent=min_pct))
    assert config.coverage.min_percent == min_pct


def test_gd_tools_config_invalid_coverage_format():
    """Test GdToolsConfig rejects invalid coverage format."""
    with pytest.raises(ValidationError):
        GdToolsConfig(coverage=CoverageConfig(format="xml"))


@pytest.mark.parametrize("min_pct", [-1, 101, -100, 200])
def test_gd_tools_config_min_percent_out_of_range(min_pct):
    """Test GdToolsConfig rejects min_percent outside [0, 100]."""
    with pytest.raises(ValidationError):
        GdToolsConfig(coverage=CoverageConfig(min_percent=min_pct))


# --- extra='forbid' ---


@pytest.mark.parametrize(
    "model_class",
    [GodotConfig, TestConfig, LintConfig, FormatConfig, CoverageConfig],
)
def test_extra_forbid_rejects_unknown_keys(model_class):
    """Test that all section models reject unknown keys (extra='forbid')."""
    with pytest.raises(ValidationError):
        model_class(unknown_key="value")


def test_gd_tools_config_extra_forbid():
    """Test GdToolsConfig rejects unknown top-level keys."""
    with pytest.raises(ValidationError):
        GdToolsConfig(unknown_section="value")


# --- Mutability ---


def test_config_mutability():
    """Test config fields can be updated after creation (CLI overrides)."""
    config = GdToolsConfig()
    config.coverage.min_percent = 90
    assert config.coverage.min_percent == 90
    config.coverage.enabled = True
    assert config.coverage.enabled is True
