"""Unit tests for the configuration system.

Covers Pydantic models, project-root discovery, TOML loading,
serialization, and rc-file generation.
"""

import io
import json
from pathlib import Path

import yaml
import pytest
from pydantic import ValidationError

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

from gd_tools.config import (
    DEFAULT_EXCLUDES,
    CoverageConfig,
    FormatConfig,
    GdToolsConfig,
    GodotConfig,
    LintConfig,
    TestConfig,
    find_project_root,
    format_config_json,
    format_config_table,
    format_config_toml,
    generate_gdformatrc,
    generate_gdlintrc,
    load_config,
    save_config,
    set_explicit_project_root,
    validate_paths,
)
from gd_tools.errors import ConfigError

pytestmark = pytest.mark.unit

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


def test_test_config_rejects_removed_gutconfig_key():
    """The removed [test].gutconfig key is rejected as an unknown key.

    The legacy GUT config path was dropped in the v0.6.0 legacy sweep;
    configs still carrying the key must fail validation.
    """
    with pytest.raises(ValidationError):
        TestConfig(gutconfig=".gutconfig.json")


def test_load_config_rejects_removed_gutconfig_key(tmp_path):
    """A TOML containing [test].gutconfig fails validation after removal."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text(
        '[test]\ngutconfig = ".gutconfig.json"\n'
    )
    with pytest.raises(ConfigError):
        load_config(project_root=tmp_path)


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


@pytest.mark.parametrize(
    "fmt",
    ["html", "lcov", "cobertura", "text", "json", "github-actions"],
)
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
    """Test GdToolsConfig rejects invalid coverage format and lists valid values."""
    with pytest.raises(ValidationError) as exc_info:
        GdToolsConfig(coverage=CoverageConfig(format="xml"))
    message = str(exc_info.value)
    for valid_format in (
        "html",
        "lcov",
        "cobertura",
        "text",
        "json",
        "github-actions",
    ):
        assert valid_format in message


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


# --- find_project_root ---


def test_find_project_root_finds_in_cwd(tmp_path):
    """Test find_project_root finds project.godot in start path."""
    (tmp_path / "project.godot").touch()
    result = find_project_root(start_path=tmp_path)
    assert result == tmp_path


def test_find_project_root_walks_up(tmp_path):
    """Test find_project_root walks up directory tree."""
    (tmp_path / "project.godot").touch()
    sub = tmp_path / "sub" / "deep" / "dir"
    sub.mkdir(parents=True)
    result = find_project_root(start_path=sub)
    assert result == tmp_path


def test_find_project_root_not_found_raises(tmp_path):
    """Test find_project_root raises ConfigError when not found."""
    with pytest.raises(ConfigError):
        find_project_root(start_path=tmp_path)


def test_find_project_root_custom_start_path(tmp_path):
    """Test find_project_root uses custom start path."""
    (tmp_path / "project.godot").touch()
    sub = tmp_path / "custom"
    sub.mkdir()
    result = find_project_root(start_path=sub)
    assert result == tmp_path


# --- load_config ---


def test_load_config_full_toml(tmp_path):
    """Test load_config with all sections present."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text(
        '[godot]\nbinary = "/usr/bin/godot"\n\n'
        '[test]\ntest_dirs = ["my_tests"]\n'
        'prefix = "check_"\nsuffix = ".gd"\n\n'
        '[lint]\nexclude = ["addons", "custom"]\n\n'
        '[format]\nexclude = ["build"]\n\n'
        "[coverage]\nenabled = true\nmin_percent = 80\n"
        'format = "lcov"\noutput_dir = "coverage"\n'
        'exclude = ["tmp"]\ntest_dirs = ["tests"]\n'
    )
    config = load_config(project_root=tmp_path)
    assert config.godot.binary == "/usr/bin/godot"
    assert config.test.test_dirs == ["my_tests"]
    assert config.test.prefix == "check_"
    assert config.lint.exclude == ["addons", "custom"]
    assert config.format.exclude == ["build"]
    assert config.coverage.enabled is True
    assert config.coverage.min_percent == 80
    assert config.coverage.format == "lcov"
    assert config.coverage.output_dir == "coverage"
    assert config.coverage.exclude == ["tmp"]
    assert config.coverage.test_dirs == ["tests"]


def test_load_config_partial_sections(tmp_path):
    """Test load_config with partial sections uses defaults."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[coverage]\nmin_percent = 50\n")
    config = load_config(project_root=tmp_path)
    assert config.coverage.min_percent == 50
    assert config.coverage.enabled is False
    assert config.coverage.format == "html"
    assert config.godot.binary is None
    assert config.test.prefix == "test_"
    assert config.lint.exclude == DEFAULT_EXCLUDES


def test_load_config_missing_file_returns_defaults(tmp_path):
    """Test load_config returns defaults when gd-tools.toml is missing."""
    (tmp_path / "project.godot").touch()
    config = load_config(project_root=tmp_path)
    assert isinstance(config, GdToolsConfig)
    assert config.godot.binary is None
    assert config.test.prefix == "test_"
    assert config.lint.exclude == DEFAULT_EXCLUDES


def test_load_config_invalid_toml_raises_config_error(tmp_path):
    """Test load_config raises ConfigError on invalid TOML syntax."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("invalid toml [[[\n")
    with pytest.raises(ConfigError) as exc_info:
        load_config(project_root=tmp_path)
    assert "gd-tools.toml" in str(exc_info.value)


def test_load_config_invalid_min_percent_raises_config_error(tmp_path):
    """Test load_config raises ConfigError for negative min_percent."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[coverage]\nmin_percent = -5\n")
    with pytest.raises(ConfigError):
        load_config(project_root=tmp_path)


def test_load_config_invalid_format_raises_config_error(tmp_path):
    """Test load_config raises ConfigError for invalid format."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text('[coverage]\nformat = "xml"\n')
    with pytest.raises(ConfigError):
        load_config(project_root=tmp_path)


def test_load_config_unknown_key_raises_config_error(tmp_path):
    """Test load_config raises ConfigError for unknown TOML key."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text(
        '[unknown_section]\nkey = "value"\n'
    )
    with pytest.raises(ConfigError):
        load_config(project_root=tmp_path)


def test_load_config_exclude_present_uses_toml_value(tmp_path):
    """Test exclude list present in TOML uses TOML value."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text(
        '[lint]\nexclude = ["custom_dir"]\n'
    )
    config = load_config(project_root=tmp_path)
    assert config.lint.exclude == ["custom_dir"]
    assert "addons" not in config.lint.exclude


def test_load_config_exclude_absent_uses_defaults(tmp_path):
    """Test exclude list absent in TOML uses DEFAULT_EXCLUDES."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[coverage]\nenabled = true\n")
    config = load_config(project_root=tmp_path)
    assert config.lint.exclude == DEFAULT_EXCLUDES
    assert config.format.exclude == DEFAULT_EXCLUDES


# --- Default parameter paths ---


def test_find_project_root_default_cwd(tmp_path, monkeypatch):
    """Test find_project_root uses CWD when no start_path given."""
    (tmp_path / "project.godot").touch()
    monkeypatch.chdir(tmp_path)
    result = find_project_root()
    assert result == tmp_path.resolve()


def test_load_config_default_project_root(tmp_path, monkeypatch):
    """Test load_config discovers project root when not given."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[coverage]\nmin_percent = 42\n")
    monkeypatch.chdir(tmp_path)
    config = load_config()
    assert config.coverage.min_percent == 42


# --- save_config ---


def test_save_config_creates_file(tmp_path):
    """Test save_config writes gd-tools.toml to project root."""
    config = GdToolsConfig()
    save_config(config, project_root=tmp_path)
    assert (tmp_path / "gd-tools.toml").is_file()


def test_save_config_round_trip_default(tmp_path):
    """Test save_config + load_config round-trips with defaults."""
    original = GdToolsConfig()
    save_config(original, project_root=tmp_path)
    loaded = load_config(project_root=tmp_path)
    assert loaded == original


def test_save_config_round_trip_custom(tmp_path):
    """Test save_config + load_config round-trips with custom values."""
    original = GdToolsConfig(
        godot=GodotConfig(binary="/usr/bin/godot"),
        test=TestConfig(test_dirs=["my_tests"], prefix="spec_"),
        lint=LintConfig(exclude=["custom_lint_dir"]),
        format=FormatConfig(exclude=["custom_fmt_dir"]),
        coverage=CoverageConfig(
            enabled=True,
            min_percent=80,
            format="lcov",
        ),
    )
    save_config(original, project_root=tmp_path)
    loaded = load_config(project_root=tmp_path)
    assert loaded == original


# --- generate_gdlintrc ---


def test_generate_gdlintrc_creates_file(tmp_path):
    """Test generate_gdlintrc creates file with exclude entries."""
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    rc_file = tmp_path / "gdlintrc"
    assert rc_file.is_file()
    content = rc_file.read_text()
    for exclude in DEFAULT_EXCLUDES:
        assert exclude in content


def test_generate_gdlintrc_overwrites_existing(tmp_path):
    """Test generate_gdlintrc overwrites existing file."""
    rc_file = tmp_path / "gdlintrc"
    rc_file.write_text("old content\nshould be gone\n")
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    content = rc_file.read_text()
    assert "old content" not in content
    for exclude in DEFAULT_EXCLUDES:
        assert exclude in content


def test_generate_gdlintrc_custom_excludes(tmp_path):
    """Test generate_gdlintrc uses custom exclude list from config."""
    custom_excludes = ["my_dir", "other_dir"]
    config = GdToolsConfig(lint=LintConfig(exclude=custom_excludes))
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    for exclude in custom_excludes:
        assert exclude in content
    assert "addons" not in content


def test_generate_gdlintrc_yaml_set_format(tmp_path):
    """Test generate_gdlintrc writes YAML !!set format."""
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    assert "excluded_directories:" in content
    assert "!!set" in content


def test_generate_gdlintrc_yaml_set_entries(tmp_path):
    """Test each exclude appears as key: null in YAML set."""
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    for exclude in DEFAULT_EXCLUDES:
        assert f"{exclude}: null" in content


def test_generate_gdlintrc_valid_yaml_parseable(tmp_path):
    """Test generated gdlintrc is valid YAML loadable by yaml.Loader."""
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    parsed = yaml.load(content, Loader=yaml.Loader)
    assert "excluded_directories" in parsed
    assert isinstance(parsed["excluded_directories"], set)


def test_generate_gdlintrc_yaml_set_matches_config(tmp_path):
    """Test YAML set contains exactly the config exclude list."""
    config = GdToolsConfig()
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    parsed = yaml.load(content, Loader=yaml.Loader)
    assert parsed["excluded_directories"] == set(DEFAULT_EXCLUDES)


def test_generate_gdlintrc_custom_excludes_yaml(tmp_path):
    """Test custom excludes produce correct YAML set format."""
    custom_excludes = ["my_dir", "other_dir"]
    config = GdToolsConfig(lint=LintConfig(exclude=custom_excludes))
    generate_gdlintrc(config, project_root=tmp_path)
    content = (tmp_path / "gdlintrc").read_text()
    parsed = yaml.load(content, Loader=yaml.Loader)
    assert parsed["excluded_directories"] == {"my_dir", "other_dir"}


# --- generate_gdformatrc ---


def test_generate_gdformatrc_creates_file(tmp_path):
    """Test generate_gdformatrc creates file with exclude entries."""
    config = GdToolsConfig()
    generate_gdformatrc(config, project_root=tmp_path)
    rc_file = tmp_path / "gdformatrc"
    assert rc_file.is_file()
    content = rc_file.read_text()
    for exclude in DEFAULT_EXCLUDES:
        assert exclude in content


def test_generate_gdformatrc_overwrites_existing(tmp_path):
    """Test generate_gdformatrc overwrites existing file."""
    rc_file = tmp_path / "gdformatrc"
    rc_file.write_text("old content\nshould be gone\n")
    config = GdToolsConfig()
    generate_gdformatrc(config, project_root=tmp_path)
    content = rc_file.read_text()
    assert "old content" not in content
    for exclude in DEFAULT_EXCLUDES:
        assert exclude in content


def test_generate_gdformatrc_custom_excludes(tmp_path):
    """Test generate_gdformatrc uses custom exclude list from config."""
    custom_excludes = ["fmt_dir", "skip_dir"]
    config = GdToolsConfig(format=FormatConfig(exclude=custom_excludes))
    generate_gdformatrc(config, project_root=tmp_path)
    content = (tmp_path / "gdformatrc").read_text()
    for exclude in custom_excludes:
        assert exclude in content
    assert "addons" not in content


# --- Path Validation ---


def test_path_validation_all_valid(tmp_path):
    """Test validate_paths returns no warnings when all paths exist."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        godot=GodotConfig(binary=str(tmp_path / "godot")),
    )
    (tmp_path / "godot").touch()
    warnings = validate_paths(config, tmp_path)
    assert warnings == []


def test_path_validation_test_dirs_nonexistent(tmp_path):
    """Test validate_paths warns about nonexistent test_dirs."""
    config = GdToolsConfig()
    warnings = validate_paths(config, tmp_path)
    assert len(warnings) > 0
    assert any("test" in w.lower() for w in warnings)


def test_path_validation_godot_binary_missing(tmp_path):
    """Test validate_paths warns when godot.binary is set but missing."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        godot=GodotConfig(binary="/nonexistent/godot"),
    )
    warnings = validate_paths(config, tmp_path)
    assert any("godot" in w.lower() for w in warnings)


def test_path_validation_godot_binary_none(tmp_path):
    """Test validate_paths does not warn when godot.binary is None."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig()
    warnings = validate_paths(config, tmp_path)
    assert not any("godot" in w.lower() for w in warnings)


def test_path_validation_coverage_output_parent_missing(tmp_path):
    """Test validate_paths warns when coverage.output_dir parent missing."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        coverage=CoverageConfig(output_dir="nonexistent_dir/coverage"),
    )
    warnings = validate_paths(config, tmp_path)
    assert any("coverage" in w.lower() for w in warnings)


def test_path_validation_lint_exclude_nonexistent(tmp_path):
    """Test validate_paths warns about nonexistent lint exclude dirs."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        lint=LintConfig(exclude=["nonexistent_lint_dir"]),
    )
    warnings = validate_paths(config, tmp_path)
    assert any("lint" in w.lower() for w in warnings)


def test_path_validation_format_exclude_nonexistent(tmp_path):
    """Test validate_paths warns about nonexistent format exclude dirs."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        format=FormatConfig(exclude=["nonexistent_format_dir"]),
    )
    warnings = validate_paths(config, tmp_path)
    assert any("format" in w.lower() for w in warnings)


def test_path_validation_coverage_exclude_nonexistent(tmp_path):
    """Test validate_paths warns about nonexistent coverage exclude dirs."""
    for d in ("test", "tests", "addons", ".godot", ".gd-tools", ".git"):
        (tmp_path / d).mkdir()
    config = GdToolsConfig(
        coverage=CoverageConfig(exclude=["nonexistent_cov_dir"]),
    )
    warnings = validate_paths(config, tmp_path)
    assert any("coverage" in w.lower() for w in warnings)


# --- Config Formatting Helpers ---


def test_format_config_table_has_all_sections():
    """Test format_config_table returns a Rich Table with all 5 sections."""
    config = GdToolsConfig()
    table = format_config_table(config)
    assert table is not None
    # Rich Table stores column headers
    headers = [col.header for col in table.columns]
    assert "Section" in headers
    assert "Key" in headers
    assert "Value" in headers


def test_format_config_table_contains_section_keys():
    """Test format_config_table includes keys from all config sections."""
    config = GdToolsConfig()
    table = format_config_table(config)
    # Render the table to text to check content
    from rich.console import Console

    console = Console(file=io.StringIO(), width=200, record=True)
    console.print(table)
    output = console.export_text()
    assert "godot" in output.lower()
    assert "test" in output.lower()
    assert "lint" in output.lower()
    assert "format" in output.lower()
    assert "coverage" in output.lower()


def test_format_config_toml_valid_toml():
    """Test format_config_toml produces valid parseable TOML."""
    config = GdToolsConfig(
        godot=GodotConfig(binary="/usr/bin/godot"),
        coverage=CoverageConfig(enabled=True, min_percent=80),
    )
    toml_str = format_config_toml(config)
    parsed = tomllib.loads(toml_str)
    assert parsed["godot"]["binary"] == "/usr/bin/godot"
    assert parsed["coverage"]["enabled"] is True
    assert parsed["coverage"]["min_percent"] == 80


def test_format_config_toml_roundtrip():
    """Test format_config_toml round-trips through GdToolsConfig."""
    original = GdToolsConfig(
        godot=GodotConfig(binary="/usr/bin/godot"),
        test=TestConfig(test_dirs=["my_tests"]),
        lint=LintConfig(exclude=["node_modules"]),
        format=FormatConfig(max_line_length=120),
        coverage=CoverageConfig(enabled=True, min_percent=90),
    )
    toml_str = format_config_toml(original)
    parsed = tomllib.loads(toml_str)
    restored = GdToolsConfig(**parsed)
    assert restored == original


def test_format_config_json_valid_json():
    """Test format_config_json produces valid parseable JSON."""
    config = GdToolsConfig(
        godot=GodotConfig(binary="/usr/bin/godot"),
        coverage=CoverageConfig(enabled=True, min_percent=80),
    )
    json_str = format_config_json(config)
    parsed = json.loads(json_str)
    assert parsed["godot"]["binary"] == "/usr/bin/godot"
    assert parsed["coverage"]["enabled"] is True
    assert parsed["coverage"]["min_percent"] == 80


def test_format_config_json_defaults():
    """Test format_config_json includes all default values."""
    config = GdToolsConfig()
    json_str = format_config_json(config)
    parsed = json.loads(json_str)
    assert "godot" in parsed
    assert "test" in parsed
    assert "lint" in parsed
    assert "format" in parsed
    assert "coverage" in parsed
    assert parsed["test"]["test_dirs"] == ["test", "tests"]
    assert parsed["format"]["max_line_length"] == 100


def test_format_config_toml_defaults():
    """Test format_config_toml shows defaults when no config file."""
    config = GdToolsConfig()
    toml_str = format_config_toml(config)
    parsed = tomllib.loads(toml_str)
    assert "godot" in parsed
    assert "test" in parsed
    assert "lint" in parsed
    assert "format" in parsed
    assert "coverage" in parsed
    assert parsed["test"]["test_dirs"] == ["test", "tests"]
    assert parsed["format"]["max_line_length"] == 100


# --- Parallel execution config ---


def test_test_config_parallel_defaults_to_none():
    """Test TestConfig defaults parallel to None (sequential)."""
    config = TestConfig()
    assert config.parallel is None


@pytest.mark.parametrize("value", [1, 2, 4, 32])
def test_test_config_parallel_valid_values(value):
    """Test TestConfig accepts parallel values within [1, 32]."""
    config = TestConfig(parallel=value)
    assert config.parallel == value


@pytest.mark.parametrize("value", [0, -1, 33, 100])
def test_test_config_parallel_out_of_range(value):
    """Test TestConfig rejects parallel outside [1, 32]."""
    with pytest.raises(ValidationError):
        TestConfig(parallel=value)


def test_test_config_parallel_rejects_non_integer():
    """Test TestConfig rejects a non-integer parallel value."""
    with pytest.raises(ValidationError):
        TestConfig(parallel="four")


def test_load_config_parallel_present(tmp_path):
    """Test load_config reads [test] parallel from TOML."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[test]\nparallel = 4\n")
    config = load_config(project_root=tmp_path)
    assert config.test.parallel == 4


def test_load_config_parallel_absent_is_none(tmp_path):
    """Test load_config leaves parallel None when absent from TOML."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text('[test]\nprefix = "check_"\n')
    config = load_config(project_root=tmp_path)
    assert config.test.parallel is None


def test_load_config_parallel_out_of_range_raises(tmp_path):
    """Test load_config raises ConfigError for out-of-range parallel."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text("[test]\nparallel = 33\n")
    with pytest.raises(ConfigError):
        load_config(project_root=tmp_path)


def test_save_config_parallel_round_trip(tmp_path):
    """Test save_config + load_config round-trips a parallel value."""
    original = GdToolsConfig(test=TestConfig(parallel=4))
    save_config(original, project_root=tmp_path)
    loaded = load_config(project_root=tmp_path)
    assert loaded.test.parallel == 4


def test_save_config_parallel_none_omitted(tmp_path):
    """Test save_config omits parallel=None from the TOML file."""
    original = GdToolsConfig()
    save_config(original, project_root=tmp_path)
    content = (tmp_path / "gd-tools.toml").read_text()
    assert "parallel" not in content


def test_format_config_toml_parallel_roundtrip():
    """Test format_config_toml round-trips a parallel value."""
    original = GdToolsConfig(test=TestConfig(parallel=8))
    toml_str = format_config_toml(original)
    parsed = tomllib.loads(toml_str)
    restored = GdToolsConfig(**parsed)
    assert restored == original


def test_format_config_json_includes_parallel():
    """Test format_config_json includes the parallel key."""
    config = GdToolsConfig(test=TestConfig(parallel=4))
    json_str = format_config_json(config)
    parsed = json.loads(json_str)
    assert parsed["test"]["parallel"] == 4


# --- explicit project root (--project anchor) ---


@pytest.fixture()
def reset_explicit_root():
    """Reset the explicit project root after each test."""
    yield
    set_explicit_project_root(None)


@pytest.mark.usefixtures("reset_explicit_root")
def test_find_project_root_explicit_overrides_start_path(tmp_path):
    """Test an explicit project root wins over any start path."""
    other = tmp_path / "other"
    other.mkdir()
    (other / "project.godot").touch()
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (explicit / "project.godot").touch()
    set_explicit_project_root(explicit)
    result = find_project_root(start_path=other)
    assert result == explicit


@pytest.mark.usefixtures("reset_explicit_root")
def test_find_project_root_explicit_used_without_start_path(
    tmp_path, monkeypatch
):
    """Test an explicit project root short-circuits the cwd walk."""
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (explicit / "project.godot").touch()
    set_explicit_project_root(explicit)
    empty = tmp_path / "elsewhere"
    empty.mkdir()
    monkeypatch.chdir(empty)
    result = find_project_root()
    assert result == explicit


@pytest.mark.usefixtures("reset_explicit_root")
def test_find_project_root_explicit_missing_project_godot_raises(tmp_path):
    """Test an explicit root without project.godot raises ConfigError."""
    set_explicit_project_root(tmp_path)
    with pytest.raises(ConfigError):
        find_project_root()


@pytest.mark.usefixtures("reset_explicit_root")
def test_find_project_root_explicit_reset_restores_walk(tmp_path):
    """Test clearing the explicit root restores cwd-based discovery."""
    set_explicit_project_root(None)
    (tmp_path / "project.godot").touch()
    result = find_project_root(start_path=tmp_path)
    assert result == tmp_path


@pytest.mark.usefixtures("reset_explicit_root")
def test_set_explicit_project_root_resolves_relative_path(
    tmp_path, monkeypatch
):
    """Test a relative explicit root is resolved against the cwd."""
    nested = tmp_path / "proj"
    nested.mkdir()
    (nested / "project.godot").touch()
    monkeypatch.chdir(tmp_path)
    set_explicit_project_root(Path("proj"))
    result = find_project_root()
    assert result == nested


# ---------------------------------------------------------------------------
# $schema key support
# ---------------------------------------------------------------------------


def test_load_config_accepts_schema_key(tmp_path):
    """A gd-tools.toml with a $schema key loads without validation errors."""
    (tmp_path / "project.godot").touch()
    (tmp_path / "gd-tools.toml").write_text(
        '"$schema" = "gd-tools.schema.json"\n'
        "[coverage]\n"
        "min_percent = 50\n"
    )
    config = load_config(project_root=tmp_path)
    assert config.coverage.min_percent == 50


def test_gdtools_config_schema_key_not_in_dump():
    """The $schema key is accepted and ignored (never enters the model)."""
    config = GdToolsConfig(**{"$schema": "./gd-tools.schema.json"})
    dumped = config.model_dump()
    assert "$schema" not in dumped
    assert "schema_" not in dumped


def test_gdtools_config_schema_key_round_trips_clean(tmp_path):
    """save_config of a model that consumed $schema writes no $schema key."""
    config = GdToolsConfig(**{"$schema": "./gd-tools.schema.json"})
    save_config(config, tmp_path)
    written = (tmp_path / "gd-tools.toml").read_text(encoding="utf-8")
    assert "$schema" not in written
    # The written file reloads cleanly through load_config.
    (tmp_path / "project.godot").touch()
    reloaded = load_config(project_root=tmp_path)
    assert reloaded == GdToolsConfig()


def test_gdtools_config_unknown_key_still_rejected():
    """extra='forbid' still rejects typo'd keys other than $schema."""
    with pytest.raises(ValidationError):
        GdToolsConfig(**{"$schema": "./gd-tools.schema.json", "typo_key": 1})


def test_gdtools_config_unknown_section_still_rejected():
    """Unknown top-level sections remain forbidden."""
    with pytest.raises(ValidationError):
        GdToolsConfig(**{"covrage": {"min_percent": 50}})
