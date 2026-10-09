"""The ``config`` command group (show, validate, schema)."""

import sys
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console

from ..config import (
    GdToolsConfig,
    ConfigError,
    find_project_root,
    format_config_json,
    format_config_table,
    format_config_toml,
    load_config,
    validate_paths,
)
from ..schema import generate_schema_text

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib


@click.group()
def config():
    """Configuration management commands."""


@config.command(name="show")
@click.option(
    "--format",
    type=click.Choice(["toml"]),
    default=None,
    help="Output format (currently only 'toml').",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
def config_show(format, as_json):
    """Show the resolved configuration.

    By default, prints a Rich table of all configuration sections.
    Use ``--format toml`` for TOML output or ``--json`` for JSON
    output. These two options are mutually exclusive.
    """
    if format is not None and as_json:
        click.echo(
            "Error: --format and --json are mutually exclusive.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    try:
        resolved_config = load_config()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    if as_json:
        click.echo(format_config_json(resolved_config))
    elif format == "toml":
        click.echo(format_config_toml(resolved_config))
    else:
        console = Console()
        console.print(format_config_table(resolved_config))

    ctx = click.get_current_context()
    ctx.exit(0)


def _get_valid_keys_for_section(section: str) -> list[str] | None:
    """Get valid field names for a config section.

    If *section* is a known top-level section (e.g. ``test``),
    returns its valid field names.  If the section itself is
    unknown, returns the valid top-level section names so the user
    can see what sections exist.

    Args:
        section: The top-level section name extracted from a
            Pydantic error ``loc``.

    Returns:
        List of valid field or section names, or ``None`` if no
        suggestion is available.
    """
    section_fields = GdToolsConfig.model_fields
    if section not in section_fields:
        return list(section_fields.keys())
    field_info = section_fields[section]
    nested_model = field_info.annotation
    if nested_model is not None and hasattr(nested_model, "model_fields"):
        return list(nested_model.model_fields.keys())  # type: ignore[arg-type]
    return None


@config.command()
def validate():
    """Validate the configuration file.

    Checks for schema errors (invalid keys, bad values) and path
    issues.  Schema errors cause a non-zero exit; path warnings are
    advisory only.
    """
    try:
        project_root = find_project_root()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        ctx = click.get_current_context()
        ctx.exit(2)

    config_file = project_root / "gd-tools.toml"

    schema_errors: list[str] = []
    path_warnings: list[str] = []

    # --- No config file: validate defaults ---
    if not config_file.is_file():
        config = GdToolsConfig()
        path_warnings = validate_paths(config, project_root)
        if path_warnings:
            click.echo("Path Warnings:")
            for w in path_warnings:
                click.echo(f"  ! {w}")
        click.echo("No gd-tools.toml found. Using default configuration.")
        click.echo("✓ Configuration is valid (using defaults).")
        ctx = click.get_current_context()
        ctx.exit(0)

    # --- Read raw TOML ---
    try:
        with open(config_file, "rb") as f:
            raw_toml = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        click.echo(f"Schema Error: Invalid TOML syntax: {exc}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

    # --- Removed GUT runtime (hard error, checked before Pydantic) ---
    test_section = raw_toml.get("test")
    if isinstance(test_section, dict) and test_section.get("runtime") == "gut":
        click.echo(
            'Schema Error: test.runtime = "gut": GUT runtime support was '
            "removed in v0.6.0. The native runtime is the default. Run "
            "`gd-tools migrate` or see docs/gut-migration.md.",
            err=True,
        )
        ctx = click.get_current_context()
        ctx.exit(2)

    clean_toml = raw_toml

    # --- Schema validation via Pydantic ---
    config: GdToolsConfig | None = None
    try:
        config = GdToolsConfig(**clean_toml)
    except ValidationError as exc:
        for error in exc.errors():
            loc = ".".join(str(p) for p in error["loc"])
            msg = error["msg"]
            if "Extra inputs are not permitted" in msg:
                parts = loc.split(".")
                section = parts[0] if parts else ""
                valid = _get_valid_keys_for_section(section)
                hint = f" — valid keys: {', '.join(valid)}" if valid else ""
                schema_errors.append(
                    f"Unknown key '{loc}': not a recognized "
                    f"configuration field{hint}"
                )
            else:
                schema_errors.append(f"{loc}: {msg}")

    # --- Path validation (only if schema is valid) ---
    if config is not None:
        path_warnings = validate_paths(config, project_root)

    # --- Print grouped findings ---
    if schema_errors:
        click.echo("Schema Errors:")
        for err in schema_errors:
            click.echo(f"  ✗ {err}")

    if path_warnings:
        click.echo("Path Warnings:")
        for w in path_warnings:
            click.echo(f"  ! {w}")

    # --- Summary ---
    click.echo(f"Configuration file: {config_file}")
    click.echo("Sections validated: 5 (godot, test, lint, format, coverage)")
    has_errors = bool(schema_errors)
    if has_errors or path_warnings:
        click.echo(
            f"Found: {len(schema_errors)} schema error(s), "
            f"{len(path_warnings)} path warning(s)"
        )
    if not has_errors:
        click.echo("✓ Configuration is valid.")
        if path_warnings:
            click.echo(f"  ({len(path_warnings)} path warning(s))")

    ctx = click.get_current_context()
    ctx.exit(1 if has_errors else 0)


@config.command(name="schema")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write the schema to this file (parent directories are "
    "created) instead of printing to stdout.",
)
def config_schema(output: Path | None) -> None:
    """Print the JSON Schema for gd-tools.toml.

    Generates the schema from the installed gd-tools version's
    configuration model (JSON Schema draft 2020-12). Point editors
    at the output (or the checked-in ``docs/gd-tools.schema.json``)
    via the ``$schema`` key in ``gd-tools.toml`` or editor-side
    TOML association to get autocomplete and inline validation.
    """
    ctx = click.get_current_context()
    if output is not None:
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(generate_schema_text(), encoding="utf-8")
        except OSError as e:
            click.echo(f"Error: cannot write schema file: {e}", err=True)
            ctx.exit(2)
        click.echo(f"Schema written to {output}")
    else:
        click.echo(generate_schema_text())
    ctx.exit(0)
