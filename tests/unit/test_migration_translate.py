"""Unit tests for .gutconfig.json -> gd-tools config translation."""

import pytest

from gd_tools.migration.translate import build_config_update

pytestmark = pytest.mark.unit


class TestBuildConfigUpdate:
    def test_dirs_are_normalized_to_test_dirs(self):
        """GUT res:// paths lose their prefix and trailing slash."""

        update = build_config_update({"dirs": ["res://test/", "res://tests"]})

        assert update.test_values == {"test_dirs": ["test", "tests"]}

    def test_prefix_and_suffix_map_directly(self):
        """prefix/suffix copy into test settings unchanged."""

        update = build_config_update({"prefix": "test_", "suffix": ".gd"})

        assert update.test_values["prefix"] == "test_"
        assert update.test_values["suffix"] == ".gd"

    def test_junit_xml_becomes_cli_flag(self):
        """junit_xml_file suggests the --junit-xml CLI flag."""

        update = build_config_update(
            {"junit_xml_file": ".gd-tools/results.xml"}
        )

        assert update.cli_flags == (("--junit-xml", ".gd-tools/results.xml"),)
        assert "junit_xml_file" not in update.test_values

    def test_noop_dropped_and_unknown_keys_are_untouched(self):
        """Keys without gd-tools targets stay in the preserved file."""

        update = build_config_update(
            {
                "should_exit": True,
                "pre_run_script": "res://hooks/pre.gd",
                "log_level": 1,
            }
        )

        assert update.untouched_keys == (
            "should_exit",
            "pre_run_script",
            "log_level",
        )
        assert update.test_values == {}

    def test_existing_values_are_never_clobbered(self):
        """A key already set in gd-tools.toml is kept, not overwritten."""

        update = build_config_update(
            {"dirs": ["res://test/"]},
            existing={"test": {"test_dirs": ["suites"]}},
        )

        assert "test_dirs" not in update.test_values
        assert update.skipped == (("dirs", "test.test_dirs"),)

    def test_existing_other_keys_do_not_block_translation(self):
        """Unrelated existing settings do not affect the mapping."""

        update = build_config_update(
            {"dirs": ["res://test/"], "prefix": "check_"},
            existing={"test": {"timeout_seconds": 10}},
        )

        assert update.test_values == {
            "test_dirs": ["test"],
            "prefix": "check_",
        }
        assert update.skipped == ()

    def test_empty_gutconfig_produces_empty_update(self):
        """No keys means nothing to translate."""

        update = build_config_update({})

        assert update.test_values == {}
        assert update.cli_flags == ()
        assert update.skipped == ()
        assert update.untouched_keys == ()
