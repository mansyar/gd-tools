extends RefCounted

## GUT pre-run hook for coverage instrumentation.
##
## Reads an instrumentation plan (JSON), injects _GDTCoverage.hit()
## calls into GDScript source code, and reloads the modified scripts.
## Activated via GD_TOOLS_COVERAGE_PLAN environment variable.

const TRACKER_NAME = "_GDTCoverage"

var _plan: Dictionary = {}
var _instrumented_scripts: Array = []

func _init() -> void:
	var plan_path: String = OS.get_environment("GD_TOOLS_COVERAGE_PLAN")
	if plan_path.is_empty():
		push_warning("[gd-tools] GD_TOOLS_COVERAGE_PLAN not set, skipping instrumentation")
		return
	var file: FileAccess = FileAccess.open(plan_path, FileAccess.READ)
	if file == null:
		push_error("[gd-tools] Cannot open plan file: " + plan_path)
		return
	var json_text: String = file.get_as_text()
	file.close()
	var json: JSON = JSON.new()
	var err: int = json.parse(json_text)
	if err != OK:
		push_error("[gd-tools] JSON parse error: " + json.get_error_message())
		return
	_plan = json.data
	_instrument_all()

## Instruments all scripts listed in the instrumentation plan.
func _instrument_all() -> void:
	for file_entry in _plan["files"]:
		var entry: Dictionary = file_entry
		_instrument_script(entry["path"], entry["file_id"], entry["lines"])

## Loads a GDScript, injects tracker calls, and reloads it.
## On reload failure, restores the original source and reloads.
func _instrument_script(script_path: String, file_id: int, lines: Array) -> void:
	var script: GDScript = load(script_path)
	if script == null:
		push_error("[gd-tools] Cannot load script: " + script_path)
		return
	var original_source: String = script.source_code
	var instrumented_source: String = _inject_trackers(original_source, file_id, lines)
	_instrumented_scripts.append({"script": script, "original": original_source})
	script.source_code = instrumented_source
	var err: int = script.reload()
	if err != OK:
		push_error("[gd-tools] reload() failed for " + script_path + ", restoring original")
		script.source_code = original_source
		script.reload()
		return
	print("[gd-tools] Instrumented: " + script_path + " (" + str(lines.size()) + " lines)")

## Injects _GDTCoverage.hit() calls before each tracked line.
## Processes bottom-to-top (descending) so earlier insertions don't shift
## the line numbers of subsequent entries.
static func _inject_trackers(source: String, file_id: int, lines: Array) -> String:
	var source_lines: PackedStringArray = source.split("\n")
	# Sort line entries descending by "line" (bottom-to-top to preserve line numbers)
	var sorted_lines: Array = lines.duplicate(true)
	sorted_lines.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))
	for entry in sorted_lines:
		var target_line_num: int = int(entry["line"])
		var line_id: int = int(entry["id"])
		var target_index: int = target_line_num - 1
		if target_index < 0 or target_index >= source_lines.size():
			continue
		var target_line: String = source_lines[target_index]
		var indent: String = _get_indentation(target_line)
		var tracker_call: String = "%s%s.hit(%d, %d)" % [indent, TRACKER_NAME, file_id, line_id]
		source_lines.insert(target_index, tracker_call)
	return "\n".join(source_lines)

## Extracts leading whitespace (tabs and spaces) from a line.
static func _get_indentation(line: String) -> String:
	var indent: String = ""
	for c in line:
		if c == " " or c == "\t":
			indent += c
		else:
			break
	return indent
