"""Unit tests for native test configuration fields."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gd_tools.config import GdToolsConfig, TestConfig, load_config, save_config

pytestmark = pytest.mark.unit


def test_native_test_config_defaults_to_native_runtime():
    """Native execution and conservative async defaults are configured."""
    config = TestConfig()

    assert config.runtime == "native"
    assert config.timeout_seconds == 5.0
    assert config.retries == 0
    assert config.tags == []


def test_native_test_config_accepts_migration_and_execution_overrides():
    """Runtime, timeout, and retry overrides remain available in TOML."""
    config = TestConfig(
        runtime="gut",
        timeout_seconds=1.25,
        retries=2,
    )

    assert config.runtime == "gut"
    assert config.timeout_seconds == 1.25
    assert config.retries == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime", "pytest"),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("retries", -1),
    ],
)
def test_native_test_config_rejects_invalid_values(field, value):
    """Invalid native execution settings fail validation."""
    with pytest.raises(ValidationError):
        TestConfig(**{field: value})


def test_native_test_config_round_trips_through_toml(tmp_path):
    """Native settings survive config serialization and loading."""
    (tmp_path / "project.godot").touch()
    config = GdToolsConfig(
        test=TestConfig(
            runtime="gut",
            timeout_seconds=2.5,
            retries=1,
            tags=["smoke", "native"],
        )
    )

    save_config(config, tmp_path)
    loaded = load_config(tmp_path)

    assert loaded.test.runtime == "gut"
    assert loaded.test.timeout_seconds == 2.5
    assert loaded.test.retries == 1
    assert loaded.test.tags == ["smoke", "native"]
    assert Path(tmp_path / "gd-tools.toml").is_file()
