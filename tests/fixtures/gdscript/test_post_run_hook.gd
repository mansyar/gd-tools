# gdlint:ignore=max-public-methods
extends GutTest

## GUT tests for post_run_hook.gd.
## Phase 4: Tests for data collection and output
## (_get_tracker, _build_coverage_json, _write_json, summary logging, run).

var _hook


func before_each():
	_hook = load("res://addons/gd-tools-coverage/post_run_hook.gd").new()
	_GDTCoverage.reset()
	OS.set_environment("GD_TOOLS_COVERAGE_OUTPUT", "")


func after_each():
	_hook = null
	_GDTCoverage.reset()
	OS.set_environment("GD_TOOLS_COVERAGE_OUTPUT", "")
	_clean_test_files()


# === _get_tracker() tests ===


func test_get_tracker_present():
	var tracker = _hook._get_tracker()
	assert_not_null(tracker, "should return tracker when autoload is present")


func test_get_tracker_returns_correct_node():
	var tracker = _hook._get_tracker()
	assert_eq(tracker, _GDTCoverage, "should return the _GDTCoverage autoload")


# === _build_coverage_json() tests ===


func test_build_coverage_json_empty_hits():
	var data = _hook._build_coverage_json({})
	assert_eq(int(data.get("version", -1)), 1, "version should be 1")
	assert_true(data.has("generated_at"), "should have generated_at")
	assert_eq(data["files"].size(), 0, "files should be empty for no hits")


func test_build_coverage_json_with_data():
	var hits = {0: {1: 3, 2: 1}}
	var data = _hook._build_coverage_json(hits)
	assert_eq(data["files"].size(), 1, "should have 1 file")
	var file_entry = data["files"][0]
	assert_eq(int(file_entry["file_id"]), 0, "file_id should be 0")
	assert_eq(file_entry["hits"].size(), 2, "should have 2 hit entries")
	assert_eq(int(file_entry["hits"]["1"]), 3, "line 1 should have 3 hits")
	assert_eq(int(file_entry["hits"]["2"]), 1, "line 2 should have 1 hit")


func test_build_coverage_json_multiple_files():
	var hits = {0: {1: 1}, 1: {2: 2, 3: 3}}
	var data = _hook._build_coverage_json(hits)
	assert_eq(data["files"].size(), 2, "should have 2 files")
	var file_ids = []
	for file_entry in data["files"]:
		file_ids.append(int(file_entry["file_id"]))
	assert_true(0 in file_ids, "should contain file_id 0")
	assert_true(1 in file_ids, "should contain file_id 1")


# === _write_json() tests ===


func test_write_json_valid_path():
	var data = {"version": 1, "files": []}
	var result = _hook._write_json("user://test_coverage_output.json", data)
	assert_true(result, "should return true for successful write")
	assert_true(
		FileAccess.file_exists("user://test_coverage_output.json"), "file should be created"
	)
	var content = FileAccess.get_file_as_string("user://test_coverage_output.json")
	var parsed = JSON.parse_string(content)
	assert_eq(int(parsed.get("version", -1)), 1, "file should contain version 1")


func test_write_json_creates_parent_dirs():
	var data = {"version": 1, "files": []}
	var result = _hook._write_json("user://test_subdir/coverage.json", data)
	assert_true(result, "should return true for successful write")
	assert_true(
		FileAccess.file_exists("user://test_subdir/coverage.json"),
		"file should be created in subdir"
	)


# === Summary logging tests ===


func test_summary_contains_file_count():
	var hits = {0: {1: 1}, 1: {2: 1}}
	var summary = _hook._log_summary(hits, "user://test_output.json")
	assert_true("2 files" in summary, "summary should contain file count")


func test_summary_contains_line_count():
	var hits = {0: {1: 1, 2: 1, 3: 1}}
	var summary = _hook._log_summary(hits, "user://test_output.json")
	assert_true("3 lines" in summary, "summary should contain line count")


func test_summary_contains_output_path():
	var hits = {}
	var summary = _hook._log_summary(hits, "user://my_output.json")
	assert_true("user://my_output.json" in summary, "summary should contain output path")


# === run() tests ===


func test_run_no_output_env_var():
	_GDTCoverage.set_active(true)
	_GDTCoverage.hit(0, 1)
	OS.set_environment("GD_TOOLS_COVERAGE_OUTPUT", "")
	_hook.run()
	assert_push_error("Cannot write coverage output")


func test_run_writes_output():
	_GDTCoverage.set_active(true)
	_GDTCoverage.hit(0, 1)
	OS.set_environment("GD_TOOLS_COVERAGE_OUTPUT", "user://test_run_output.json")
	_hook.run()
	assert_true(
		FileAccess.file_exists("user://test_run_output.json"), "output file should be created"
	)
	var content = FileAccess.get_file_as_string("user://test_run_output.json")
	var parsed = JSON.parse_string(content)
	assert_eq(int(parsed.get("version", -1)), 1, "output should have version 1")
	assert_eq(parsed["files"].size(), 1, "output should have 1 file")


func test_run_inactive_tracker_no_output():
	_GDTCoverage.set_active(false)
	OS.set_environment("GD_TOOLS_COVERAGE_OUTPUT", "user://test_inactive_output.json")
	_hook.run()
	assert_false(
		FileAccess.file_exists("user://test_inactive_output.json"),
		"should not write output when tracker inactive"
	)


# === Helpers ===


func _clean_test_files() -> void:
	var dir = DirAccess.open("user://")
	if dir:
		var files = [
			"test_coverage_output.json",
			"test_run_output.json",
			"test_inactive_output.json",
		]
		for filename in files:
			dir.remove(filename)
		if dir.dir_exists("test_subdir"):
			dir.remove("test_subdir/coverage.json")
			dir.remove("test_subdir")
