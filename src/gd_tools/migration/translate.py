"""Translation of ``.gutconfig.json`` into gd-tools settings.

Translation is pure: it classifies and converts keys but never writes
files. The source ``.gutconfig.json`` is always preserved on disk
(merge-never-clobber): keys already set in the user's gd-tools.toml are
kept as-is and reported as skipped instead of being overwritten.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from gd_tools.migration.gutconfig import _OPTIONS_BY_KEY


@dataclass(frozen=True)
class ConfigUpdate:
    """The gd-tools changes a ``.gutconfig.json`` translates into."""

    #: Values for the ``[test]`` section of gd-tools.toml.
    test_values: dict[str, object] = field(default_factory=dict)
    #: ``(flag, value)`` pairs to pass on the ``gd-tools test`` command line.
    cli_flags: tuple[tuple[str, str], ...] = ()
    #: ``(gut_key, gd_tools_target)`` pairs already set in gd-tools.toml and
    #: therefore deliberately not overwritten.
    skipped: tuple[tuple[str, str], ...] = ()
    #: Keys with no gd-tools target; they stay in the preserved
    #: ``.gutconfig.json`` on disk.
    untouched_keys: tuple[str, ...] = ()


def _normalize_dir(directory: str) -> str:
    """Convert a GUT directory value to a gd-tools test directory."""
    return directory.removeprefix("res://").rstrip("/")


def build_config_update(
    options: Mapping[str, object],
    existing: Mapping[str, Mapping[str, object]] | None = None,
) -> ConfigUpdate:
    """Translate parsed ``.gutconfig.json`` keys into a ConfigUpdate.

    Args:
        options: Parsed ``.gutconfig.json`` content.
        existing: Optional current gd-tools.toml content as a
            section-to-keys mapping; values already present are never
            clobbered.

    Returns:
        The translation result. Keys without a gd-tools target are listed
        under ``untouched_keys``; the source file itself is always
        preserved on disk.
    """
    existing_test = dict((existing or {}).get("test") or {})
    test_values: dict[str, object] = {}
    cli_flags: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    untouched: list[str] = []

    for key, value in options.items():
        option = _OPTIONS_BY_KEY.get(key)
        if option is None or option.handling != "translate":
            untouched.append(key)
            continue

        if option.target == "test.test_dirs":
            if "test_dirs" in existing_test:
                skipped.append((key, option.target))
            else:
                test_values["test_dirs"] = [
                    _normalize_dir(directory)
                    for directory in value  # type: ignore[union-attr]
                ]
        elif option.target == "test.prefix":
            if "prefix" in existing_test:
                skipped.append((key, option.target))
            else:
                test_values["prefix"] = value
        elif option.target == "test.suffix":
            if "suffix" in existing_test:
                skipped.append((key, option.target))
            else:
                test_values["suffix"] = value
        elif option.target == "--junit-xml":
            cli_flags.append(("--junit-xml", str(value)))

    return ConfigUpdate(
        test_values=test_values,
        cli_flags=tuple(cli_flags),
        skipped=tuple(skipped),
        untouched_keys=tuple(untouched),
    )
