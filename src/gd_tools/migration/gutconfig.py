"""Inventory of ``.gutconfig.json`` options and their migration mapping.

Every option GUT configuration files use in this ecosystem is classified as
either translatable to a gd-tools setting, handled automatically by the
native runtime (no-op), or dropped because no equivalent exists. Unknown
keys are surfaced to the user instead of being silently lost; the file
itself is always preserved on disk (merge-never-clobber).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

GutconfigHandling = str  # one of "translate", "no-op", "drop"


@dataclass(frozen=True)
class GutconfigOption:
    """One ``.gutconfig.json`` key and how migration treats it."""

    key: str
    handling: GutconfigHandling
    target: str | None
    note: str


#: Curated mapping covering every key gd-tools' own ``init`` writes into
#: ``.gutconfig.json`` plus how each is handled during migration.
GUTCONFIG_OPTIONS: tuple[GutconfigOption, ...] = (
    GutconfigOption(
        key="dirs",
        handling="translate",
        target="test.test_dirs",
        note="Test directories become test.test_dirs in gd-tools.toml.",
    ),
    GutconfigOption(
        key="prefix",
        handling="translate",
        target="test.prefix",
        note="Test file prefix becomes test.prefix in gd-tools.toml.",
    ),
    GutconfigOption(
        key="suffix",
        handling="translate",
        target="test.suffix",
        note="Test file suffix becomes test.suffix in gd-tools.toml.",
    ),
    GutconfigOption(
        key="junit_xml_file",
        handling="translate",
        target="--junit-xml",
        note=(
            "Pass the path to 'gd-tools test --junit-xml'; there is no "
            "gd-tools.toml key for it."
        ),
    ),
    GutconfigOption(
        key="include_subdirs",
        handling="no-op",
        target=None,
        note=(
            "gd-tools test discovery always scans test directories "
            "recursively."
        ),
    ),
    GutconfigOption(
        key="should_exit",
        handling="no-op",
        target=None,
        note="gd-tools always exits when the run finishes.",
    ),
    GutconfigOption(
        key="pre_run_script",
        handling="drop",
        target=None,
        note=(
            "Coverage hook scripts are replaced by the native coverage "
            "autoload installed by 'gd-tools init --coverage'."
        ),
    ),
    GutconfigOption(
        key="post_run_script",
        handling="drop",
        target=None,
        note=(
            "Coverage hook scripts are replaced by the native coverage "
            "autoload installed by 'gd-tools init --coverage'."
        ),
    ),
)


@dataclass(frozen=True)
class ConfigTranslation:
    """Classification of one ``.gutconfig.json``'s keys."""

    mapped: tuple[tuple[str, str], ...] = ()
    noop: tuple[str, ...] = ()
    dropped: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()


_OPTIONS_BY_KEY = {option.key: option for option in GUTCONFIG_OPTIONS}


def translate_gutconfig(options: Mapping[str, object]) -> ConfigTranslation:
    """Classify ``.gutconfig.json`` keys against the migration inventory.

    Args:
        options: Parsed ``.gutconfig.json`` content.

    Returns:
        The classification in inventory order, with keys that are not in
        the inventory reported under ``unknown``.
    """
    mapped: list[tuple[str, str]] = []
    noop: list[str] = []
    dropped: list[str] = []
    unknown: list[str] = []

    for key in options:
        option = _OPTIONS_BY_KEY.get(key)
        if option is None:
            unknown.append(key)
        elif option.handling == "translate":
            mapped.append((key, option.target))
        elif option.handling == "no-op":
            noop.append(key)
        else:
            dropped.append(key)

    return ConfigTranslation(
        mapped=tuple(mapped),
        noop=tuple(noop),
        dropped=tuple(dropped),
        unknown=tuple(unknown),
    )
