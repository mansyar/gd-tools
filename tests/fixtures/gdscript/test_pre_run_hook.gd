extends GutTest

## GUT tests for pre_run_hook.gd.
## Phase 2: Tests for plan loading (env var, JSON parsing, validation).

var _hook


func before_each():
	_hook = load("res://addons/gd-tools-coverage/pre_run_hook.gd").new()


func after_each():
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
		'{"version": 1, "files": [{"file_id": 0, "path": "res://simple.gd", '
		+ '"lines": [{"line": 7, "id": 0}]}]}'
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
		]
		for filename in files:
			dir.remove(filename)
