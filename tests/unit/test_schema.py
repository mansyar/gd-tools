"""Unit tests for the gd-tools.toml JSON Schema generation."""

import json
from pathlib import Path

import pytest

from gd_tools.config import GdToolsConfig
from gd_tools.schema import (
    SCHEMA_DRAFT_URL,
    generate_schema,
    generate_schema_text,
)

pytestmark = pytest.mark.unit


def test_generate_schema_declares_draft_2020_12():
    """The generated schema declares the JSON Schema draft 2020-12."""
    schema = generate_schema()
    assert schema["$schema"] == SCHEMA_DRAFT_URL


def test_generate_schema_has_id():
    """The generated schema carries a stable $id."""
    schema = generate_schema()
    assert schema["$id"] == (
        "https://raw.githubusercontent.com/mansyar/gd-tools/main/"
        "docs/gd-tools.schema.json"
    )


def test_generate_schema_description_names_version():
    """The schema description mentions the gd-tools version that made it."""
    from gd_tools import __version__

    schema = generate_schema()
    assert __version__ in schema["description"]


def test_generate_schema_has_config_sections():
    """Top-level properties match the five config sections."""
    schema = generate_schema()
    props = schema["properties"]
    for section in ("godot", "test", "lint", "format", "coverage"):
        assert section in props


def test_generate_schema_reflects_live_model_fields():
    """The schema is derived from the passed model, not hardcoded."""
    schema = generate_schema()
    test_props = schema["$defs"]["TestConfig"]["properties"]
    assert "test_dirs" in test_props
    assert "parallel" in test_props


def test_generate_schema_tracks_model_changes():
    """Passing a modified model produces a schema that reflects it."""
    from pydantic import create_model

    Extended = create_model(
        "ExtendedConfig",
        __base__=GdToolsConfig,
        experimental_flag=(bool | None, None),
    )
    schema = generate_schema(model=Extended)
    assert "experimental_flag" in schema["properties"]


def test_generate_schema_forbids_extra_keys():
    """The schema mirrors extra='forbid' so editors flag unknown keys."""
    schema = generate_schema()
    assert schema["additionalProperties"] is False


def test_generate_schema_serializes_to_json():
    """The schema dict round-trips through json.dumps."""
    text = json.dumps(generate_schema())
    assert json.loads(text)["title"]


def test_checked_in_schema_snapshot_is_current():
    """docs/gd-tools.schema.json is byte-identical to the generated schema.

    If this fails, the checked-in snapshot has drifted from the config
    model. Regenerate it with:
        gd-tools config schema --output docs/gd-tools.schema.json
    and commit the result.
    """
    repo_root = Path(__file__).resolve().parents[2]
    snapshot = repo_root / "docs" / "gd-tools.schema.json"
    assert snapshot.exists(), (
        "docs/gd-tools.schema.json is missing. Regenerate it with:\n"
        "    gd-tools config schema --output docs/gd-tools.schema.json"
    )
    assert snapshot.read_text(encoding="utf-8") == generate_schema_text(), (
        "docs/gd-tools.schema.json is out of date with the config model. "
        "Regenerate it with:\n"
        "    gd-tools config schema --output docs/gd-tools.schema.json"
    )
