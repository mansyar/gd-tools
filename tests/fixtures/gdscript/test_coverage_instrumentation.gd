# gdlint:ignore=max-public-methods
extends GutTest

## GUT tests for coverage.gd instrumentation methods.
## Moved from test_pre_run_hook.gd when instrumentation logic was
## moved from pre_run_hook.gd to _GDTCoverage._ready().
## Tests: _load_plan, _validate_plan, _extract_indent,
## _inject_trackers, _instrument_file.

var _calc_original_source: String = ""
var _calc_modified: bool = false


func before_each():
	_GDTCoverage._plan = {}
	_GDTCoverage.set_active(false)
	_calc_original_source = ""
	_calc_modified = false


func after_each():
	if _calc_modified and not _calc_original_source.is_empty():
		var calc = load("res://scripts/calculator.gd") as GDScript
		calc.source_code = _calc_original_source
		calc.reload()
	_GDTCoverage._plan = {}
	_GDTCoverage.set_active(false)
	OS.set_environment("GD_TOOLS_COVERAGE_PLAN", "")
	_clean_test_files()


# === _load_plan() tests ===


func test_load_plan_valid():
	var json = (
		'{"version": 1, "files": [{"file_id": 0, "path": "res://simple.gd", '
		+ '"lines": [{"line": 7, "id": 0}]}]}'
	)
	_write_file("user://test_plan_valid.json", json)
	var plan = _GDTCoverage._load_plan("user://test_plan_valid.json")
	assert_eq(int(plan.get("version", -1)), 1, "version should be 1")
	assert_true(plan.has("files"), "plan should have files key")
	assert_eq(plan["files"].size(), 1, "should have 1 file")


func test_load_plan_nonexistent_file():
	var plan = _GDTCoverage._load_plan("user://nonexistent_plan.json")
	assert_eq(plan.size(), 0, "should return empty dict for nonexistent file")
	assert_push_error("Failed to load coverage plan")


func test_load_plan_malformed_json():
	_write_file("user://test_plan_malformed.json", "not valid json{{{")
	var plan = _GDTCoverage._load_plan("user://test_plan_malformed.json")
	assert_eq(plan.size(), 0, "should return empty dict for malformed JSON")
	assert_push_error("Failed to parse coverage plan JSON")
	assert_engine_error_count(1, "JSON.parse_string generates engine error")


# === _validate_plan() tests ===


func test_validate_plan_valid():
	var plan = {
		"version": 1,
		"files": [{"file_id": 0, "path": "res://simple.gd", "lines": [{"line": 7, "id": 0}]}]
	}
	assert_true(_GDTCoverage._validate_plan(plan), "valid plan should return true")


func test_validate_plan_missing_version():
	var plan = {"files": []}
	assert_false(_GDTCoverage._validate_plan(plan), "plan missing version should return false")
	assert_push_error("Missing 'version' key")


func test_validate_plan_missing_files():
	var plan = {"version": 1}
	assert_false(_GDTCoverage._validate_plan(plan), "plan missing files should return false")
	assert_push_error("Missing or invalid 'files' key")


func test_validate_plan_empty_files():
	var plan = {"version": 1, "files": []}
	assert_true(_GDTCoverage._validate_plan(plan), "plan with empty files should be valid")


func test_validate_plan_file_missing_file_id():
	var plan = {"version": 1, "files": [{"path": "res://test.gd", "lines": []}]}
	assert_false(_GDTCoverage._validate_plan(plan), "file missing file_id should return false")
	assert_push_error("File entry missing 'file_id'")


func test_validate_plan_file_missing_path():
	var plan = {"version": 1, "files": [{"file_id": 0, "lines": []}]}
	assert_false(_GDTCoverage._validate_plan(plan), "file missing path should return false")
	assert_push_error("File entry missing 'path'")


func test_validate_plan_file_missing_lines():
	var plan = {"version": 1, "files": [{"file_id": 0, "path": "res://test.gd"}]}
	assert_false(_GDTCoverage._validate_plan(plan), "file missing lines should return false")
	assert_push_error("Missing or invalid 'lines' key")


# === _extract_indent() tests ===


func test_extract_indent_tab():
	var result = _GDTCoverage._extract_indent("\t\thello")
	assert_eq(result, "\t\t", "should return tab characters")


func test_extract_indent_space():
	var result = _GDTCoverage._extract_indent("    hello")
	assert_eq(result, "    ", "should return space characters")


func test_extract_indent_none():
	var result = _GDTCoverage._extract_indent("hello")
	assert_eq(result, "", "should return empty string for no indent")


func test_extract_indent_mixed():
	var result = _GDTCoverage._extract_indent("\t  hello")
	assert_eq(result, "\t  ", "should return mixed tabs and spaces")


# === _inject_trackers() tests ===


func test_inject_trackers_single_line():
	var source = "line1\nline2\nline3\n"
	var lines = [{"line": 2, "id": 0}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[1], "_GDTCoverage.hit(0, 0)", "tracker call should be before line 2")
	assert_eq(result_lines[2], "line2", "original line 2 should be preserved")


func test_inject_trackers_multiple_lines_bottom_to_top():
	var source = "line1\nline2\nline3\nline4\n"
	var lines = [{"line": 2, "id": 0}, {"line": 4, "id": 1}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
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
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "    _GDTCoverage.hit(0, 0)", "tracker should match indentation")
	assert_eq(result_lines[3], "    return x", "original line preserved with indent")


func test_inject_trackers_empty_lines():
	var source = "line1\nline2\n"
	var result = _GDTCoverage._inject_trackers(source, 0, [])
	assert_eq(result, source, "source should be unchanged for empty lines")


func test_inject_trackers_duplicate_line_numbers():
	var source = "line1\nline2\nline3\n"
	var lines = [{"line": 2, "id": 0}, {"line": 2, "id": 1}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
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
	var result = _GDTCoverage._inject_trackers(source, 0, tracked_lines)
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


# === _inject_trackers() match_case tests ===


func test_inject_trackers_match_case_literal_pattern():
	# Match case with literal pattern: tracker goes AFTER pattern line
	var source = 'func foo(state):\n\tmatch state:\n\t\t0:\n\t\t\tprint("zero")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[1], "\tmatch state:", "match line directly before pattern")
	assert_eq(result_lines[2], "\t\t0:", "pattern line should be unchanged")
	assert_eq(
		result_lines[3], "\t\t\t_GDTCoverage.hit(0, 0)", "tracker after pattern with body indent"
	)
	assert_eq(result_lines[4], '\t\t\tprint("zero")', "body line should be preserved")


func test_inject_trackers_match_case_wildcard_pattern():
	var source = 'func foo(state):\n\tmatch state:\n\t\t_:\n\t\t\tprint("default")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t\t_:", "wildcard pattern unchanged")
	assert_eq(
		result_lines[3], "\t\t\t_GDTCoverage.hit(0, 0)", "tracker after wildcard with body indent"
	)


func test_inject_trackers_match_case_var_binding():
	var source = "func foo(arr):\n\tmatch arr:\n\t\tvar x:\n\t\t\tprint(x)\n"
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t\tvar x:", "var binding pattern unchanged")
	assert_eq(
		result_lines[3],
		"\t\t\t_GDTCoverage.hit(0, 0)",
		"tracker after var binding with body indent"
	)


func test_inject_trackers_match_case_array_pattern():
	var source = 'func foo(arr):\n\tmatch arr:\n\t\t[0, 1]:\n\t\t\tprint("match")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t\t[0, 1]:", "array pattern unchanged")
	assert_eq(
		result_lines[3],
		"\t\t\t_GDTCoverage.hit(0, 0)",
		"tracker after array pattern with body indent"
	)


func test_inject_trackers_match_case_dict_pattern():
	var source = 'func foo(d):\n\tmatch d:\n\t\t{"key": 1}:\n\t\t\tprint("match")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], '\t\t{"key": 1}:', "dict pattern unchanged")
	assert_eq(
		result_lines[3],
		"\t\t\t_GDTCoverage.hit(0, 0)",
		"tracker after dict pattern with body indent"
	)


func test_inject_trackers_match_case_multiple_patterns():
	var source = 'func foo(state):\n\tmatch state:\n\t\t0, 1, 2:\n\t\t\tprint("low")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t\t0, 1, 2:", "multiple pattern unchanged")
	assert_eq(
		result_lines[3],
		"\t\t\t_GDTCoverage.hit(0, 0)",
		"tracker after multiple pattern with body indent"
	)


func test_inject_trackers_match_case_guarded_pattern():
	var source = 'func foo(state):\n\tmatch state:\n\t\t0 when state > 5:\n\t\t\tprint("guarded")\n'
	var lines = [{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t\t0 when state > 5:", "guarded pattern unchanged")
	assert_eq(
		result_lines[3],
		"\t\t\t_GDTCoverage.hit(0, 0)",
		"tracker after guarded pattern with body indent"
	)


func test_inject_trackers_match_case_full_statement():
	# Full match with multiple cases — no tracker between match expr and first pattern
	var source = (
		"func handle(state):\n"
		+ "\tmatch state:\n"
		+ "\t\t0:\n"
		+ '\t\t\tprint("zero")\n'
		+ "\t\t1:\n"
		+ '\t\t\tprint("one")\n'
		+ "\t\t_:\n"
		+ '\t\t\tprint("default")\n'
	)
	var lines = [
		{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"},
		{"line": 5, "id": 1, "type": "branch", "branch_type": "match_case"},
		{"line": 7, "id": 2, "type": "branch", "branch_type": "match_case"},
	]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	# No tracker between match and first pattern
	assert_eq(result_lines[1], "\tmatch state:", "match line unchanged")
	assert_eq(result_lines[2], "\t\t0:", "first pattern directly after match (no tracker between)")
	# Tracker for case 0 after first pattern
	assert_eq(
		result_lines[3], "\t\t\t_GDTCoverage.hit(0, 0)", "tracker for case 0 after first pattern"
	)
	assert_eq(result_lines[4], '\t\t\tprint("zero")', "body of case 0 preserved")
	# Second case
	assert_eq(result_lines[5], "\t\t1:", "second pattern preserved")
	assert_eq(
		result_lines[6], "\t\t\t_GDTCoverage.hit(0, 1)", "tracker for case 1 after second pattern"
	)
	assert_eq(result_lines[7], '\t\t\tprint("one")', "body of case 1 preserved")
	# Wildcard case
	assert_eq(result_lines[8], "\t\t_:", "wildcard pattern preserved")
	assert_eq(
		result_lines[9], "\t\t\t_GDTCoverage.hit(0, 2)", "tracker for wildcard case after pattern"
	)


func test_inject_trackers_non_match_case_still_injects_before():
	# Regression: non-match_case entries should still inject BEFORE the tracked line
	var source = "func foo():\n\tvar x = 5\n\treturn x\n"
	var lines = [{"line": 3, "id": 0, "type": "statement"}]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	assert_eq(result_lines[2], "\t_GDTCoverage.hit(0, 0)", "tracker should be before line 3")
	assert_eq(result_lines[3], "\treturn x", "original line 3 preserved")


func test_inject_trackers_mixed_match_and_non_match():
	# Mixed: one match_case entry and one regular entry
	var source = (
		"func handle(state):\n"
		+ "\tmatch state:\n"
		+ "\t\t0:\n"
		+ '\t\t\tprint("zero")\n'
		+ "\treturn\n"
	)
	var lines = [
		{"line": 3, "id": 0, "type": "branch", "branch_type": "match_case"},
		{"line": 5, "id": 1, "type": "statement"},
	]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	# match_case tracker AFTER pattern, regular tracker BEFORE return
	assert_eq(result_lines[2], "\t\t0:", "pattern preserved")
	assert_eq(result_lines[3], "\t\t\t_GDTCoverage.hit(0, 0)", "match_case tracker after pattern")
	assert_eq(result_lines[4], '\t\t\tprint("zero")', "body preserved")
	assert_eq(result_lines[5], "\t_GDTCoverage.hit(0, 1)", "regular tracker before return")
	assert_eq(result_lines[6], "\treturn", "return line preserved")


func test_inject_trackers_if_false_injects_after_else():
	# if_false (else:) tracker must be injected AFTER the else: line,
	# inside the else body — injecting before would break the if-else structure.
	var source = (
		"func foo(x):\n" + "\tif x > 0:\n" + "\t\treturn 1\n" + "\telse:\n" + "\t\treturn 0\n"
	)
	var lines = [
		{"line": 2, "id": 0, "type": "branch", "branch_type": "if_true"},
		{"line": 4, "id": 1, "type": "branch", "branch_type": "if_false"},
	]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	# if_true tracker BEFORE the if line
	assert_eq(result_lines[1], "\t_GDTCoverage.hit(0, 0)", "if_true tracker before if")
	assert_eq(result_lines[2], "\tif x > 0:", "if line preserved")
	assert_eq(result_lines[3], "\t\treturn 1", "if body preserved")
	# if_false tracker AFTER the else: line (inside else body)
	assert_eq(result_lines[4], "\telse:", "else line preserved")
	assert_eq(result_lines[5], "\t\t_GDTCoverage.hit(0, 1)", "if_false tracker after else")
	assert_eq(result_lines[6], "\t\treturn 0", "else body preserved")


func test_inject_trackers_elif_true_injects_after_elif():
	# elif_true tracker must be injected AFTER the elif: line,
	# inside the elif body — injecting before would break the if-elif structure.
	var source = (
		"func foo(x):\n"
		+ "\tif x > 10:\n"
		+ "\t\treturn 1\n"
		+ "\telif x > 5:\n"
		+ "\t\treturn 2\n"
		+ "\telse:\n"
		+ "\t\treturn 0\n"
	)
	var lines = [
		{"line": 2, "id": 0, "type": "branch", "branch_type": "if_true"},
		{"line": 4, "id": 1, "type": "branch", "branch_type": "elif_true"},
		{"line": 6, "id": 2, "type": "branch", "branch_type": "if_false"},
	]
	var result = _GDTCoverage._inject_trackers(source, 0, lines)
	var result_lines = result.split("\n")
	# if_true tracker BEFORE the if line
	assert_eq(result_lines[1], "\t_GDTCoverage.hit(0, 0)", "if_true tracker before if")
	assert_eq(result_lines[2], "\tif x > 10:", "if line preserved")
	assert_eq(result_lines[3], "\t\treturn 1", "if body preserved")
	# elif_true tracker AFTER the elif: line (inside elif body)
	assert_eq(result_lines[4], "\telif x > 5:", "elif line preserved")
	assert_eq(result_lines[5], "\t\t_GDTCoverage.hit(0, 1)", "elif_true tracker after elif")
	assert_eq(result_lines[6], "\t\treturn 2", "elif body preserved")
	# if_false tracker AFTER the else: line (inside else body)
	assert_eq(result_lines[7], "\telse:", "else line preserved")
	assert_eq(result_lines[8], "\t\t_GDTCoverage.hit(0, 2)", "if_false tracker after else")
	assert_eq(result_lines[9], "\t\treturn 0", "else body preserved")


# === _instrument_file() tests ===


func test_instrument_file_valid_path():
	# gdlint:ignore=duplicated-load
	var calc = load("res://scripts/calculator.gd") as GDScript
	_calc_original_source = calc.source_code
	_calc_modified = true
	var file_entry = {
		"file_id": 0, "path": "res://scripts/calculator.gd", "lines": [{"line": 7, "id": 0}]
	}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_true(result, "should return true for valid script")
	assert_true("_GDTCoverage.hit(0, 0)" in calc.source_code, "source should contain tracker call")


func test_instrument_file_invalid_path():
	var file_entry = {
		"file_id": 0, "path": "res://nonexistent_script.gd", "lines": [{"line": 1, "id": 0}]
	}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_false(result, "should return false for invalid path")
	assert_push_error("Failed to instrument script")
	assert_engine_error_count(2, "load() generates engine errors for invalid path")


func test_instrument_file_no_tracked_lines():
	var file_entry = {"file_id": 0, "path": "res://scripts/calculator.gd", "lines": []}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_false(result, "should return false for no tracked lines")


func test_instrument_file_succeeds_with_active_instances():
	# gdlint:ignore=duplicated-load
	var calc = load("res://scripts/calculator.gd") as GDScript
	_calc_original_source = calc.source_code
	_calc_modified = true
	# Create an instance — reload(true) keeps it while recompiling
	var instance = calc.new()
	var file_entry = {
		"file_id": 0, "path": "res://scripts/calculator.gd", "lines": [{"line": 7, "id": 0}]
	}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_true(result, "should return true even when script has active instances")
	assert_true(
		"_GDTCoverage.hit" in calc.source_code,
		"source should contain tracker calls after instrumentation"
	)


func test_instrument_file_source_instrumented_with_instances():
	# gdlint:ignore=duplicated-load
	var calc = load("res://scripts/calculator.gd") as GDScript
	_calc_original_source = calc.source_code
	_calc_modified = true
	var instance = calc.new()
	var file_entry = {
		"file_id": 0, "path": "res://scripts/calculator.gd", "lines": [{"line": 7, "id": 0}]
	}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_true(result, "should succeed with active instances")
	assert_ne(
		calc.source_code, _calc_original_source,
		"source should be instrumented, not original"
	)
	assert_true(
		"_GDTCoverage.hit" in calc.source_code,
		"instrumented source should contain tracker calls"
	)


func test_instrument_file_restores_source_on_reload_failure():
	# gdlint:ignore=duplicated-load
	var calc = load("res://scripts/calculator.gd") as GDScript
	_calc_original_source = calc.source_code
	_calc_modified = true
	# Set invalid source so reload(true) fails with a parse error
	var broken_source = "func broken(:\n"
	calc.source_code = broken_source
	var file_entry = {
		"file_id": 0, "path": "res://scripts/calculator.gd", "lines": [{"line": 1, "id": 0}]
	}
	var result = _GDTCoverage._instrument_file(file_entry)
	assert_false(result, "should return false when reload fails")
	assert_eq(
		calc.source_code,
		broken_source,
		"source_code should be restored to original on reload failure"
	)
	assert_push_error("Failed to reload instrumented script")
	assert_engine_error_count(
		2, "instrumented source and restored broken source both fail to parse"
	)


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
		]
		for filename in files:
			dir.remove(filename)
