"""Unit tests for the configuration system.

Covers Pydantic models, project-root discovery, TOML loading,
serialization, and rc-file generation.
"""

import yaml
import pytest
from pydantic import ValidationError

from gd_tools import config as config_module
from gd_tools.config import (
    DEFAULT_EXCLUDES,
    CoverageConfig,
    DeprecatedField,
    FormatConfig,
    GdToolsConfig,
    GodotConfig,
    LintConfig,
    TestConfig,
    check_deprecated_settings,
    find_project_root,
    generate_gdformatrc,
    generate_gdlintrc,
    load_config,
    save_config,
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
        'prefix = "check_"\nsuffix = ".gd"\n'
        'gutconfig = ".gutconfig.json"\n\n'
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


# --- Deprecation Infrastructure ---


def test_deprecation_field_dataclass_fields():
    """Test DeprecatedField dataclass has all required fields."""
    df = DeprecatedField(
        field_path="coverage.min_percent",
        since_version="0.2.0",
        replacement="coverage.threshold",
        migration_message="Use coverage.threshold instead.",
    )
    assert df.field_path == "coverage.min_percent"
    assert df.since_version == "0.2.0"
    assert df.replacement == "coverage.threshold"
    assert df.migration_message == "Use coverage.threshold instead."


def test_deprecation_registry_empty_by_default():
    """Test _DEPRECATED_FIELDS is empty by default (no fields deprecated)."""
    assert config_module._DEPRECATED_FIELDS == {}


def test_deprecation_check_empty_registry():
    """Test check_deprecated_settings returns empty list with empty registry."""
    result = check_deprecated_settings({"coverage": {"min_percent": 80}})
    assert result == []


def test_deprecation_check_key_present(monkeypatch):
    """Test check_deprecated_settings finds a deprecated key in raw TOML."""
    fake_dep = DeprecatedField(
        field_path="coverage.min_percent",
        since_version="0.2.0",
        replacement="coverage.threshold",
        migration_message="Use coverage.threshold instead.",
    )
    monkeypatch.setitem(
        config_module._DEPRECATED_FIELDS, "coverage.min_percent", fake_dep
    )
    result = check_deprecated_settings({"coverage": {"min_percent": 80}})
    assert len(result) == 1
    assert result[0].field_path == "coverage.min_percent"


def test_deprecation_check_key_absent(monkeypatch):
    """Test check_deprecated_settings returns empty when key is absent."""
    fake_dep = DeprecatedField(
        field_path="coverage.min_percent",
        since_version="0.2.0",
        replacement="coverage.threshold",
        migration_message="Use coverage.threshold instead.",
    )
    monkeypatch.setitem(
        config_module._DEPRECATED_FIELDS, "coverage.min_percent", fake_dep
    )
    result = check_deprecated_settings({"coverage": {"enabled": True}})
    assert result == []


def test_deprecation_check_multiple_keys(monkeypatch):
    """Test check_deprecated_settings finds multiple deprecated keys."""
    dep1 = DeprecatedField(
        field_path="coverage.min_percent",
        since_version="0.2.0",
        replacement="coverage.threshold",
        migration_message="Use coverage.threshold instead.",
    )
    dep2 = DeprecatedField(
        field_path="test.gutconfig",
        since_version="0.3.0",
        replacement=None,
        migration_message="gutconfig is no longer supported.",
    )
    monkeypatch.setitem(
        config_module._DEPRECATED_FIELDS, "coverage.min_percent", dep1
    )
    monkeypatch.setitem(
        config_module._DEPRECATED_FIELDS, "test.gutconfig", dep2
    )
    result = check_deprecated_settings(
        {
            "coverage": {"min_percent": 80},
            "test": {"gutconfig": "custom.json"},
        }
    )
    assert len(result) == 2
    paths = {r.field_path for r in result}
    assert "coverage.min_percent" in paths
    assert "test.gutconfig" in paths


def test_deprecation_check_replacement_none(monkeypatch):
    """Test check_deprecated_settings handles replacement=None."""
    fake_dep = DeprecatedField(
        field_path="test.gutconfig",
        since_version="0.3.0",
        replacement=None,
        migration_message="gutconfig is no longer supported.",
    )
    monkeypatch.setitem(
        config_module._DEPRECATED_FIELDS, "test.gutconfig", fake_dep
    )
    result = check_deprecated_settings({"test": {"gutconfig": "custom.json"}})
    assert len(result) == 1
    assert result[0].replacement is None


def test_deprecation_check_empty_data():
    """Test check_deprecated_settings with empty dict returns empty list."""
    result = check_deprecated_settings({})
    assert result == []
