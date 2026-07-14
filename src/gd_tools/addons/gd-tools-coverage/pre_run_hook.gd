extends GutHookScript

## Pre-run hook for GUT test runner.
## Instruments GDScript source files with coverage tracking calls
## before tests are executed.

const TRACKER_NAME = "_GDTCoverage"

var _plan: Dictionary = {}


func run() -> void:
	var plan_path: String = OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
	if plan_path.is_empty():
		print("[gd-tools] [Warning] GD_TOOLS_COVERAGE_PLAN not set. Skipping instrumentation.")
		return

	_plan = _load_plan(plan_path)
	if _plan.is_empty():
		return

	if not _validate_plan(_plan):
		_plan = {}
		return

	var files: Array = _plan.get("files", [])
	if files.is_empty():
		print("[gd-tools] [Warning] Coverage plan has no files to instrument.")
		return

	var instrumented_count: int = _instrument_files()
	if instrumented_count > 0:
		_activate_tracker()


func _instrument_files() -> int:
	var files: Array = _plan.get("files", [])
	var count: int = 0
	for file_entry in files:
		if _instrument_file(file_entry):
			count += 1
	return count


func _instrument_file(file_entry: Dictionary) -> bool:
	var path: String = file_entry.get("path", "")
	var file_id: int = int(file_entry.get("file_id", -1))
	var lines: Array = file_entry.get("lines", [])

	if lines.is_empty():
		return false

	var script = load(path) as GDScript
	if script == null:
		_log_error(
			"Failed to instrument script.",
			"Cannot load script: " + path,
			"Verify the path in the plan exists and compiles."
		)
		return false

	var original_source: String = script.source_code
	var instrumented: String = _inject_trackers(original_source, file_id, lines)
	script.source_code = instrumented
	var err: int = script.reload()
	if err == ERR_ALREADY_IN_USE:
		print("[gd-tools] [Warning] Skipping instrumented script with active instances: " + path)
		script.source_code = original_source
		return false
	if err != OK:
		_log_error(
			"Failed to reload instrumented script.",
			"reload() failed for: " + path,
			"Check tracker injection logic for syntax errors."
		)
		script.source_code = original_source
		script.reload()
		return false

	return true


func _activate_tracker() -> void:
	var tree = Engine.get_main_loop() as SceneTree
	if tree == null:
		_log_error(
			"Failed to activate coverage tracker.",
			"Cannot access SceneTree.",
			"Ensure the hook runs in a Godot project context."
		)
		return

	var tracker = tree.root.get_node_or_null(TRACKER_NAME)
	if tracker == null:
		_log_error(
			"Failed to activate coverage tracker.",
			"Autoload '" + TRACKER_NAME + "' not found.",
			"Ensure the coverage addon is installed and registered as an autoload."
		)
		return

	tracker.set_active(true)


static func _extract_indent(line: String) -> String:
	var indent: String = ""
	for c in line:
		if c == " " or c == "\t":
			indent += c
		else:
			break
	return indent


static func _detect_body_indent(source_lines: PackedStringArray, pattern_index: int) -> String:
	# Scan lines after the pattern line to find the next non-empty line
	# and use its indentation as the body indent.
	var i: int = pattern_index + 1
	while i < source_lines.size():
		var line: String = source_lines[i]
		if not line.strip_edges().is_empty():
			return _extract_indent(line)
		i += 1
	# Fallback: if no non-empty line found, use the pattern indent plus one tab.
	return _extract_indent(source_lines[pattern_index]) + "\t"


static func _inject_trackers(source: String, file_id: int, lines: Array) -> String:
	var source_lines: PackedStringArray = source.split("\n")
	var sorted_lines: Array = lines.duplicate(true)
	sorted_lines.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))
	for entry in sorted_lines:
		var target_line_num: int = int(entry["line"])
		var line_id: int = int(entry["id"])
		var target_index: int = target_line_num - 1
		if target_index < 0 or target_index >= source_lines.size():
			continue
		var target_line: String = source_lines[target_index]
		var branch_type = entry.get("branch_type", "")
		if branch_type == null:
			branch_type = ""
		var insert_index: int
		var indent: String
		if branch_type in ["match_case", "if_false", "elif_true"]:
			# Inject AFTER the branch line (inside the body).
			# match_case patterns, else: and elif: lines must have trackers
			# placed inside their body — injecting before these lines would
			# insert a statement between the if/elif/else keywords, breaking
			# the GDScript block structure (orphaned else/elif = syntax error).
			insert_index = target_index + 1
			indent = _detect_body_indent(source_lines, target_index)
		else:
			# Inject BEFORE the tracked line (existing behavior)
			insert_index = target_index
			indent = _extract_indent(target_line)
		var tracker_call: String = "%s%s.hit(%d, %d)" % [indent, TRACKER_NAME, file_id, line_id]
		source_lines.insert(insert_index, tracker_call)
	return "\n".join(source_lines)


func _load_plan(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		_log_error(
			"Failed to load coverage plan.",
			"File not found: " + path,
			"Ensure GD_TOOLS_COVERAGE_PLAN points to a valid plan JSON file."
		)
		return {}

	var f = FileAccess.open(path, FileAccess.READ)
	if f == null:
		_log_error(
			"Failed to load coverage plan.",
			"Cannot open file: " + path,
			"Check file permissions and try again."
		)
		return {}

	var content: String = f.get_as_text()
	f = null

	var parsed = JSON.parse_string(content)
	if not (parsed is Dictionary):
		_log_error(
			"Failed to parse coverage plan JSON.",
			"Invalid JSON in file: " + path,
			"Validate the JSON syntax and try again."
		)
		return {}

	return parsed


func _validate_plan(plan: Dictionary) -> bool:
	if not plan.has("version"):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing 'version' key.",
			"Ensure the plan JSON has a 'version' field."
		)
		return false

	if not plan.has("files") or not (plan["files"] is Array):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing or invalid 'files' key.",
			"Ensure the plan JSON has a 'files' array."
		)
		return false

	for file_entry in plan["files"]:
		if not _validate_file_entry(file_entry):
			return false

	return true


func _validate_file_entry(file_entry: Variant) -> bool:
	if not (file_entry is Dictionary):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry is not an object.",
			"Ensure each file in 'files' is a JSON object."
		)
		return false

	if not file_entry.has("file_id"):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry missing 'file_id'.",
			"Ensure each file has a 'file_id' field."
		)
		return false

	if not file_entry.has("path"):
		_log_error(
			"Invalid coverage plan structure.",
			"File entry missing 'path'.",
			"Ensure each file has a 'path' field."
		)
		return false

	if not file_entry.has("lines") or not (file_entry["lines"] is Array):
		_log_error(
			"Invalid coverage plan structure.",
			"Missing or invalid 'lines' key.",
			"Ensure each file has a 'lines' array."
		)
		return false

	for line_entry in file_entry["lines"]:
		if not (line_entry is Dictionary) or not line_entry.has("line") or not line_entry.has("id"):
			_log_error(
				"Invalid coverage plan structure.",
				"Line entry missing 'line' or 'id' key.",
				"Ensure each line entry has 'line' and 'id' fields."
			)
			return false

	return true


func _log_error(what: String, cause: String, fix: String) -> void:
	push_error(
		"[gd-tools] [Error] " + what + "\n\n" + "  Cause: " + cause + "\n" + "  Fix:   " + fix
	)
