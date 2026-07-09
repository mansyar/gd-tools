"""Configuration system for gd-tools.

Provides Pydantic v2 models for typed loading, validation, and
default resolution of ``gd-tools.toml`` configuration files.
See TDD §3.2 for model definitions and PRD §6 for config format.
"""

import sys
from pathlib import Path

import tomli_w
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)

from gd_tools.errors import ConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

DEFAULT_EXCLUDES = ["addons", ".godot", ".gd-tools", ".git"]


class GodotConfig(BaseModel):
    """Configuration for the Godot binary.

    Attributes:
        binary: Path to the Godot binary. If None, auto-detection
            is used (Track 4).
    """

    model_config = ConfigDict(extra="forbid")

    binary: str | None = None


class TestConfig(BaseModel):
    """Configuration for test discovery and GUT.

    Attributes:
        test_dirs: Directories containing test files.
        prefix: Test file prefix (GUT convention).
        suffix: Test file suffix.
        gutconfig: Path to the GUT config file.
    """

    __test__ = False

    model_config = ConfigDict(extra="forbid")

    test_dirs: list[str] = Field(default_factory=lambda: ["test", "tests"])
    prefix: str = "test_"
    suffix: str = ".gd"
    gutconfig: str = ".gutconfig.json"


class LintConfig(BaseModel):
    """Configuration for linting.

    Attributes:
        exclude: List of directories excluded from linting.
    """

    model_config = ConfigDict(extra="forbid")

    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())


class FormatConfig(BaseModel):
    """Configuration for formatting.

    Attributes:
        exclude: List of directories excluded from formatting.
    """

    model_config = ConfigDict(extra="forbid")

    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())


class CoverageConfig(BaseModel):
    """Configuration for code coverage.

    Attributes:
        enabled: Whether coverage is enabled.
        min_percent: Minimum coverage percentage threshold.
        format: Report format (html, lcov, cobertura, text).
        output_dir: Directory for coverage data and reports.
        exclude: Directories excluded from coverage measurement.
        test_dirs: Directories containing test files.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    min_percent: int = 0
    format: str = "html"
    output_dir: str = ".gd-tools/coverage"
    exclude: list[str] = Field(default_factory=lambda: DEFAULT_EXCLUDES.copy())
    test_dirs: list[str] = Field(default_factory=lambda: ["test", "tests"])


class GdToolsConfig(BaseModel):
    """Root configuration model for gd-tools.

    Contains all configuration sections and a field validator
    that enforces coverage format and min_percent constraints.

    Attributes:
        godot: Godot binary configuration.
        test: Test discovery configuration.
        lint: Linting configuration.
        format: Formatting configuration.
        coverage: Coverage configuration.
    """

    model_config = ConfigDict(extra="forbid")

    godot: GodotConfig = Field(default_factory=GodotConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    lint: LintConfig = Field(default_factory=LintConfig)
    format: FormatConfig = Field(default_factory=FormatConfig)
    coverage: CoverageConfig = Field(default_factory=CoverageConfig)

    @field_validator("coverage")
    @classmethod
    def validate_coverage(cls, v: CoverageConfig) -> CoverageConfig:
        """Validate coverage format and min_percent constraints.

        Args:
            v: The coverage configuration to validate.

        Returns:
            The validated coverage configuration.

        Raises:
            ValueError: If format is not in {html, lcov,
                cobertura, text} or min_percent is outside
                [0, 100].
        """
        if v.format not in (
            "html",
            "lcov",
            "cobertura",
            "text",
        ):
            raise ValueError(f"Invalid coverage format: {v.format}")
        if not 0 <= v.min_percent <= 100:
            raise ValueError(
                f"min_percent must be 0-100, got " f"{v.min_percent}"
            )
        return v


def find_project_root(
    start_path: Path | None = None,
) -> Path:
    """Walk up from start_path to find the nearest project.godot.

    Args:
        start_path: Directory to start searching from.
            Defaults to the current working directory.

    Returns:
        The directory containing ``project.godot``.

    Raises:
        ConfigError: If ``project.godot`` is not found in any
            parent directory.
    """
    if start_path is None:
        start_path = Path.cwd()
    current = start_path.resolve()
    while True:
        if (current / "project.godot").is_file():
            return current
        if current == current.parent:
            raise ConfigError(
                "project.godot not found in any parent "
                f"directory starting from {start_path}"
            )
        current = current.parent


def load_config(
    project_root: Path | None = None,
) -> GdToolsConfig:
    """Load gd-tools.toml configuration from the project root.

    If ``project_root`` is None, discovers it via
    :func:`find_project_root`.

    Args:
        project_root: Path to the project root directory.
            If None, the project root is discovered
            automatically.

    Returns:
        A typed ``GdToolsConfig`` object. If
        ``gd-tools.toml`` is missing, returns an object
        with all default values.

    Raises:
        ConfigError: If the TOML file is invalid or contains
            values that fail Pydantic validation.
    """
    if project_root is None:
        project_root = find_project_root()

    config_file = project_root / "gd-tools.toml"
    if not config_file.is_file():
        return GdToolsConfig()

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {config_file}: {exc}") from exc

    try:
        return GdToolsConfig(**data)
    except ValidationError as exc:
        raise ConfigError(
            f"Invalid configuration in {config_file}: " f"{exc}"
        ) from exc


def save_config(
    config: GdToolsConfig,
    project_root: Path,
) -> None:
    """Write a GdToolsConfig to gd-tools.toml in the project root.

    Produces valid TOML that round-trips through
    :func:`load_config`.

    Args:
        config: The configuration to serialize.
        project_root: Path to the project root directory.
    """
    config_file = project_root / "gd-tools.toml"
    data = config.model_dump(exclude_none=True)
    with open(config_file, "wb") as f:
        tomli_w.dump(data, f)


def generate_gdlintrc(
    config: GdToolsConfig,
    project_root: Path,
) -> None:
    """Generate a gdlintrc file from the lint exclude list.

    Writes one exclude path per line to ``gdlintrc`` in
    the project root. Overwrites the file if it already
    exists.

    Args:
        config: The configuration to read excludes from.
        project_root: Path to the project root directory.
    """
    rc_file = project_root / "gdlintrc"
    content = "\n".join(config.lint.exclude) + "\n"
    rc_file.write_text(content)


def generate_gdformatrc(
    config: GdToolsConfig,
    project_root: Path,
) -> None:
    """Generate a gdformatrc file from the format exclude list.

    Writes one exclude path per line to ``gdformatrc`` in
    the project root. Overwrites the file if it already
    exists.

    Args:
        config: The configuration to read excludes from.
        project_root: Path to the project root directory.
    """
    rc_file = project_root / "gdformatrc"
    content = "\n".join(config.format.exclude) + "\n"
    rc_file.write_text(content)
