extends GutHookScript

## Pre-run hook for GUT test runner.
## Instruments GDScript source files with coverage tracking calls
## before tests are executed.

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

	# Phase 3: Instrument source files and activate tracker.


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

	return true


func _log_error(what: String, cause: String, fix: String) -> void:
	push_error("[gd-tools] [Error] " + what + "\n" + "  Cause: " + cause + "\n" + "  Fix:   " + fix)
