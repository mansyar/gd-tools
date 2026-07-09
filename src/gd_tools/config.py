"""Configuration system for gd-tools.

Provides Pydantic v2 models for typed loading, validation, and
default resolution of ``gd-tools.toml`` configuration files.
See TDD §3.2 for model definitions and PRD §6 for config format.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

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
