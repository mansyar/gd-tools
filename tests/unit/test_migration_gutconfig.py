"""Unit tests for the .gutconfig.json option mapping inventory."""

import pytest

from gd_tools.migration.gutconfig import (
    GUTCONFIG_OPTIONS,
    translate_gutconfig,
)

pytestmark = pytest.mark.unit

# Every key gd-tools init writes into .gutconfig.json (see
# gd_tools.init._GUTCONFIG_OVERWRITE_KEYS / _GUTCONFIG_PRESERVE_KEYS).
_TEMPLATE_KEYS = frozenset(
    {
        "dirs",
        "include_subdirs",
        "prefix",
        "suffix",
        "should_exit",
        "junit_xml_file",
        "pre_run_script",
        "post_run_script",
    }
)


class TestInventory:
    def test_inventory_covers_every_template_key(self):
        """No .gutconfig.json key gd-tools writes goes unmapped."""

        assert {option.key for option in GUTCONFIG_OPTIONS} >= _TEMPLATE_KEYS

    def test_inventory_entries_are_well_formed(self):
        """Entries have unique keys, a valid handling, and a note."""

        keys = [option.key for option in GUTCONFIG_OPTIONS]
        assert len(keys) == len(set(keys))

        for option in GUTCONFIG_OPTIONS:
            assert option.handling in {"translate", "no-op", "drop"}
            assert option.note
            if option.handling == "translate":
                assert option.target
            else:
                assert option.target is None


class TestTranslateGutconfig:
    def test_maps_discovery_options_to_test_config(self):
        """dirs/prefix/suffix translate into gd-tools test settings."""

        translation = translate_gutconfig(
            {"dirs": ["res://test/"], "prefix": "test_", "suffix": ".gd"}
        )

        assert translation.mapped == (
            ("dirs", "test.test_dirs"),
            ("prefix", "test.prefix"),
            ("suffix", "test.suffix"),
        )

    def test_maps_junit_xml_to_cli_flag(self):
        """junit_xml_file translates into the --junit-xml CLI flag."""

        translation = translate_gutconfig(
            {"junit_xml_file": ".gd-tools/results.xml"}
        )

        assert translation.mapped == (("junit_xml_file", "--junit-xml"),)

    def test_reports_noop_keys(self):
        """Options handled automatically require no user action."""

        translation = translate_gutconfig(
            {"should_exit": True, "include_subdirs": True}
        )

        assert translation.noop == ("should_exit", "include_subdirs")

    def test_reports_dropped_hook_keys(self):
        """Hook script keys have no native equivalent and are dropped."""

        translation = translate_gutconfig(
            {
                "pre_run_script": "res://addons/gd-tools-coverage/pre_run_hook.gd",
                "post_run_script": "res://addons/gd-tools-coverage/post_run_hook.gd",
            }
        )

        assert translation.dropped == ("pre_run_script", "post_run_script")

    def test_reports_unknown_keys_separately(self):
        """Keys outside the inventory are surfaced, never silently lost."""

        translation = translate_gutconfig({"log_level": 1})

        assert translation.unknown == ("log_level",)

    def test_empty_config_translates_to_nothing(self):
        """An empty .gutconfig.json yields empty buckets."""

        translation = translate_gutconfig({})

        assert translation.mapped == ()
        assert translation.noop == ()
        assert translation.dropped == ()
        assert translation.unknown == ()
