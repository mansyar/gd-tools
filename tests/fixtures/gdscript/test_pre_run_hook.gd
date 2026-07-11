# gdlint:ignore=max-public-methods
extends GutTest

## GUT tests for pre_run_hook.gd.
## Phase 2: Tests for plan loading (env var, JSON parsing, validation).
## Phase 3: Tests for source instrumentation (_extract_indent,
## _inject_trackers, _instrument_file, tracker activation).

var _hook
var _calc_original_source: String = ""
var _calc_modified: bool = false


func before_each():
	_hook = load("res://addons/gd-tools-coverage/pre_run_hook.gd").new()
	_calc_original_source = ""
	_calc_modified = false


func after_each():
	if _calc_modified and not _calc_original_source.is_empty():
		var calc = load("res://scripts/calculator.gd") as GDScript
		calc.source_code = _calc_original_source
		calc.reload()
	_hook = null
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "")
	_clean_test_files()


# === _load_plan() tests ===


func test_load_plan_valid():
	var json = (
		'{"version": 1, "files": [{"file_id": 0, "path": "res://simple.gd", '
		+ '"lines": [{"line": 7, "id": 0}]}]}'
	)
	_write_file("user://test_plan_valid.json", json)
	var plan = _hook._load_plan("user://test_plan_valid.json")
	assert_eq(int(plan.get("version", -1)), 1, "version should be 1")
	assert_true(plan.has("files"), "plan should have files key")
	assert_eq(plan["files"].size(), 1, "should have 1 file")


func test_load_plan_nonexistent_file():
	var plan = _hook._load_plan("user://nonexistent_plan.json")
	assert_eq(plan.size(), 0, "should return empty dict for nonexistent file")
	assert_push_error("Failed to load coverage plan")


func test_load_plan_malformed_json():
	_write_file("user://test_plan_malformed.json", "not valid json{{{")
	var plan = _hook._load_plan("user://test_plan_malformed.json")
	assert_eq(plan.size(), 0, "should return empty dict for malformed JSON")
	assert_push_error("Failed to parse coverage plan JSON")
	assert_engine_error_count(1, "JSON.parse_string generates engine error")


# === _validate_plan() tests ===


func test_validate_plan_valid():
	var plan = {
		"version": 1,
		"files": [{"file_id": 0, "path": "res://simple.gd", "lines": [{"line": 7, "id": 0}]}]
	}
	assert_true(_hook._validate_plan(plan), "valid plan should return true")


func test_validate_plan_missing_version():
	var plan = {"files": []}
	assert_false(_hook._validate_plan(plan), "plan missing version should return false")
	assert_push_error("Missing 'version' key")


func test_validate_plan_missing_files():
	var plan = {"version": 1}
	assert_false(_hook._validate_plan(plan), "plan missing files should return false")
	assert_push_error("Missing or invalid 'files' key")


func test_validate_plan_empty_files():
	var plan = {"version": 1, "files": []}
	assert_true(_hook._validate_plan(plan), "plan with empty files should be valid")


func test_validate_plan_file_missing_file_id():
	var plan = {"version": 1, "files": [{"path": "res://test.gd", "lines": []}]}
	assert_false(_hook._validate_plan(plan), "file missing file_id should return false")
	assert_push_error("File entry missing 'file_id'")


func test_validate_plan_file_missing_path():
	var plan = {"version": 1, "files": [{"file_id": 0, "lines": []}]}
	assert_false(_hook._validate_plan(plan), "file missing path should return false")
	assert_push_error("File entry missing 'path'")


func test_validate_plan_file_missing_lines():
	var plan = {"version": 1, "files": [{"file_id": 0, "path": "res://test.gd"}]}
	assert_false(_hook._validate_plan(plan), "file missing lines should return false")
	assert_push_error("Missing or invalid 'lines' key")


# === run() tests ===


func test_run_no_env_var():
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "")
	_hook.run()
	assert_eq(_hook._plan.size(), 0, "plan should be empty when env var not set")


func test_run_valid_env_var():
	var json = (
		'{"version": 1, "files": [{"file_id": 0, "path": "res://scripts/calculator.gd", '
		+ '"lines": []}]}'
	)
	_write_file("user://test_plan_run.json", json)
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "user://test_plan_run.json")
	_hook.run()
	assert_eq(int(_hook._plan.get("version", -1)), 1, "plan should be loaded with version 1")


func test_run_empty_files_warning():
	var json = '{"version": 1, "files": []}'
	_write_file("user://test_plan_empty.json", json)
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "user://test_plan_empty.json")
	_hook.run()
	assert_eq(_hook._plan["files"].size(), 0, "plan should have empty files array")


# === _extract_indent() tests ===


func test_extract_indent_tab():
	var result = _hook._extract_indent("\t\thello")
	assert_eq(result, "\t\t", "should return tab characters")


func test_extract_indent_space():
	var result = _hook._extract_indent("    hello")
	assert_eq(result, "    ", "should return space characters")


func test_extract_indent_none():
	var result = _hook._extract_indent("hello")
	assert_eq(result, "", "should return empty string for no indent")


func test_extract_indent_mixed():
	var result = _hook._extract_indent("\t  hello")
	assert_eq(result, "\t  ", "should return mixed tabs and spaces")


# === _inject_trackers() tests ===


func test_inject_trackers_single_line():
	var source = "line1\nline2\nline3\n"
	var lines = [{"line": 2, "id": 0}]
	var result = _hook._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[1], "_GDTCoverage.hit(0, 0)", "tracker call should be before line 2")
	assert_eq(result_lines[2], "line2", "original line 2 should be preserved")


func test_inject_trackers_multiple_lines_bottom_to_top():
	var source = "line1\nline2\nline3\nline4\n"
	var lines = [{"line": 2, "id": 0}, {"line": 4, "id": 1}]
	var result = _hook._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	# Line 4 tracker should be inserted first (bottom-to-top), then line 2
	# After both insertions: line1, tracker0, line2, line3, tracker1, line4
	assert_eq(result_lines[1], "_GDTCoverage.hit(0, 0)", "tracker for line 2 at index 1")
	assert_eq(result_lines[2], "line2", "original line 2 preserved")
	assert_eq(result_lines[4], "_GDTCoverage.hit(0, 1)", "tracker for line 4 at index 4")
	assert_eq(result_lines[5], "line4", "original line 4 preserved")


func test_inject_trackers_indentation_matching():
	var source = "func foo():\n    var x = 5\n    return x\n"
	var lines = [{"line": 3, "id": 0}]
	var result = _hook._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "    _GDTCoverage.hit(0, 0)", "tracker should match indentation")
	assert_eq(result_lines[3], "    return x", "original line preserved with indent")


func test_inject_trackers_empty_lines():
	var source = "line1\nline2\n"
	var result = _hook._inject_trackers(source, 0, [])
	assert_eq(result, source, "source should be unchanged for empty lines")


func test_inject_trackers_duplicate_line_numbers():
	var source = "line1\nline2\nline3\n"
	var lines = [{"line": 2, "id": 0}, {"line": 2, "id": 1}]
	var result = _hook._inject_trackers(source, 0, lines)
	assert_true("_GDTCoverage.hit(0, 0)" in result, "should contain tracker for id 0")
	assert_true("_GDTCoverage.hit(0, 1)" in result, "should contain tracker for id 1")


func test_inject_trackers_very_long_file():
	# Create a 1000-line source string
	var lines_array = []
	for i in range(1000):
		lines_array.append("var v" + str(i) + " = " + str(i))
	var source = "\n".join(lines_array) + "\n"

	# Track lines at beginning (1), middle (500), and end (1000)
	var tracked_lines = [
		{"line": 1, "id": 0},
		{"line": 500, "id": 1},
		{"line": 1000, "id": 2},
	]
	var result = _hook._inject_trackers(source, 0, tracked_lines)
	var result_lines = result.split("\n")

	# 1000 original lines + trailing empty + 3 injected = 1004 elements
	assert_eq(result_lines.size(), 1004, "should have 1004 lines after 3 injections")

	# Tracker for line 1 at index 0
	assert_eq(result_lines[0], "_GDTCoverage.hit(0, 0)", "tracker before line 1")
	assert_eq(result_lines[1], "var v0 = 0", "original line 1 preserved")

	# Tracker for line 500 at index 500 (shifted by 1 from line 1 injection)
	assert_eq(result_lines[500], "_GDTCoverage.hit(0, 1)", "tracker before line 500")
	assert_eq(result_lines[501], "var v499 = 499", "original line 500 preserved")

	# Tracker for line 1000 at index 1001 (shifted by 2 from line 1 and 500 injections)
	assert_eq(result_lines[1001], "_GDTCoverage.hit(0, 2)", "tracker before line 1000")
	assert_eq(result_lines[1002], "var v999 = 999", "original line 1000 preserved")


# === _instrument_file() tests ===


func test_instrument_file_valid_path():
	# gdlint:ignore=duplicated-load
	var calc = load("res://scripts/calculator.gd") as GDScript
	_calc_original_source = calc.source_code
	_calc_modified = true
	var file_entry = {
		"file_id": 0, "path": "res://scripts/calculator.gd", "lines": [{"line": 7, "id": 0}]
	}
	var result = _hook._instrument_file(file_entry)
	assert_true(result, "should return true for valid script")
	assert_true("_GDTCoverage.hit(0, 0)" in calc.source_code, "source should contain tracker call")


func test_instrument_file_invalid_path():
	var file_entry = {
		"file_id": 0, "path": "res://nonexistent_script.gd", "lines": [{"line": 1, "id": 0}]
	}
	var result = _hook._instrument_file(file_entry)
	assert_false(result, "should return false for invalid path")
	assert_push_error("Failed to instrument script")
	assert_engine_error_count(2, "load() generates engine errors for invalid path")


func test_instrument_file_no_tracked_lines():
	var file_entry = {"file_id": 0, "path": "res://scripts/calculator.gd", "lines": []}
	var result = _hook._instrument_file(file_entry)
	assert_false(result, "should return false for no tracked lines")


# === Tracker activation tests ===


func test_activate_tracker():
	_GDTCoverage.set_active(false)
	_hook._activate_tracker()
	assert_true(_GDTCoverage.is_active(), "tracker should be active after activation")


func test_run_does_not_activate_tracker_with_empty_files():
	_GDTCoverage.set_active(false)
	var json = '{"version": 1, "files": []}'
	_write_file("user://test_plan_no_activate.json", json)
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "user://test_plan_no_activate.json")
	_hook.run()
	assert_false(_GDTCoverage.is_active(), "tracker should not be activated with empty files")


# === Helpers ===


func _write_file(path: String, content: String) -> void:
	var f = FileAccess.open(path, FileAccess.WRITE)
	if f:
		f.store_string(content)


func _clean_test_files() -> void:
	var dir = DirAccess.open("user://")
	if dir:
		var files = [
			"test_plan_valid.json",
			"test_plan_malformed.json",
			"test_plan_run.json",
			"test_plan_empty.json",
			"test_plan_no_activate.json",
		]
		for filename in files:
			dir.remove(filename)
