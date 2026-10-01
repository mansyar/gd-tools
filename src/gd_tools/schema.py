"""JSON Schema generation for ``gd-tools.toml``.

Generates a JSON Schema (draft 2020-12) from the Pydantic
configuration model so editors can provide autocomplete and inline
validation for ``gd-tools.toml``. The schema is always derived from
the live model of the installed gd-tools version — never hardcoded.
"""

import json

from pydantic import BaseModel

from .config import GdToolsConfig
from . import __version__ as _gd_tools_version

SCHEMA_DRAFT_URL = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_ID = (
    "https://raw.githubusercontent.com/mansyar/gd-tools/main/"
    "docs/gd-tools.schema.json"
)


def generate_schema(
    model: type[BaseModel] = GdToolsConfig,
) -> dict:
    """Generate a JSON Schema dict from a Pydantic config model.

    Args:
        model: The Pydantic model to describe. Defaults to the
            root :class:`GdToolsConfig`.

    Returns:
        A JSON Schema (draft 2020-12) dict with ``$id`` set and a
        description naming the gd-tools version that produced it.
    """
    schema = model.model_json_schema()
    schema["$schema"] = SCHEMA_DRAFT_URL
    schema["$id"] = SCHEMA_ID
    schema["title"] = "gd-tools configuration (gd-tools.toml)"
    schema["description"] = (
        f"Configuration schema for gd-tools.toml "
        f"(gd-tools {_gd_tools_version})."
    )
    return schema


def generate_schema_text(
    model: type[BaseModel] = GdToolsConfig,
) -> str:
    """Serialize the generated schema as pretty-printed JSON.

    Args:
        model: The Pydantic model to describe. Defaults to the
            root :class:`GdToolsConfig`.

    Returns:
        A JSON string with a trailing newline.
    """
    return json.dumps(generate_schema(model), indent=2) + "\n"
