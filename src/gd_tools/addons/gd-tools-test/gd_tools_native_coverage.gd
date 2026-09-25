class_name GdToolsNativeCoverage
extends RefCounted

## Transient native coverage collector for the gd-tools test runner.
##
## The Python side supplies the existing version-1 instrumentation plan. This
## class instruments scripts in memory, tracks hits through a static class
## callable, and writes the same JSON shape consumed by the Python reporter.

static var _hits: Dictionary = {}
static var _active := false
static var _output_path := ""


static func activate(plan_path: String, output_path: String) -> bool:
	## Instrument all files in a plan and enable hit collection.
	_hits.clear()
	_active = false
	_output_path = output_path

	if plan_path.is_empty() or not FileAccess.file_exists(plan_path):
		push_error("[gd-tools] Native coverage plan not found: %s" % plan_path)
		return false

	var plan_file := FileAccess.open(plan_path, FileAccess.READ)
	if plan_file == null:
		push_error("[gd-tools] Unable to read native coverage plan: %s" % plan_path)
		return false
	var parsed: Variant = JSON.parse_string(plan_file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY or int(parsed.get("version", -1)) != 1:
		push_error("[gd-tools] Unsupported native coverage plan format")
		return false

	for file_data in parsed.get("files", []):
		if not _instrument_file(file_data):
			_active = false
			return false

	_active = true
	return true


static func hit(file_id: int, line_id: int) -> void:
	## Record one instrumented hit when coverage is active.
	if not _active:
		return
	if not _hits.has(file_id):
		_hits[file_id] = {}
	if not _hits[file_id].has(line_id):
		_hits[file_id][line_id] = 0
	_hits[file_id][line_id] += 1


static func write() -> bool:
	## Write collected hits using the existing coverage JSON schema.
	if not _active or _output_path.is_empty():
		return false

	var files: Array = []
	for file_id in _hits:
		var file_hits: Dictionary = {}
		for line_id in _hits[file_id]:
			file_hits[str(line_id)] = _hits[file_id][line_id]
		files.append({"file_id": int(file_id), "hits": file_hits})

	var data := {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"files": files,
	}
	var directory := _output_path.get_base_dir()
	if not directory.is_empty() and not DirAccess.dir_exists_absolute(directory):
		if DirAccess.make_dir_recursive_absolute(directory) != OK:
			return false

	var temporary_path := _output_path + ".tmp"
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(data, "  ") + "\n")
	file.close()
	return DirAccess.rename_absolute(temporary_path, _output_path) == OK


static func _instrument_file(file_data: Dictionary) -> bool:
	var path := str(file_data.get("path", ""))
	var file_id := int(file_data.get("file_id", -1))
	var lines: Array = file_data.get("lines", [])
	if path.is_empty() or file_id < 0 or lines.is_empty():
		return false

	var script := load(path) as GDScript
	if script == null:
		push_error("[gd-tools] Unable to load coverage target: %s" % path)
		return false

	var original_source := script.source_code
	script.source_code = _inject_trackers(
			original_source,
			file_id,
			lines
	)
	var reload_error: int = script.reload(true)
	if reload_error != OK:
		script.source_code = original_source
		script.reload(true)
		push_error("[gd-tools] Unable to instrument coverage target: %s" % path)
		return false
	return true


static func _inject_trackers(
		source: String,
		file_id: int,
		lines: Array
) -> String:
	var source_lines: PackedStringArray = source.split("\n")
	var entries: Array = lines.duplicate(true)
	entries.sort_custom(func(a, b): return int(a["line"]) > int(b["line"]))
	for entry in entries:
		var target_index := int(entry["line"]) - 1
		if target_index < 0 or target_index >= source_lines.size():
			continue
		var branch_type = str(entry.get("branch_type", ""))
		var insert_index := target_index
		if branch_type in ["match_case", "if_false", "elif_true"]:
			insert_index = target_index + 1
		var indent := _extract_indent(source_lines[insert_index])
		if indent.is_empty():
			indent = _extract_indent(source_lines[target_index])
		var tracker := "%sGdToolsNativeCoverage.hit(%d, %d)" % [
			indent,
			file_id,
			int(entry["id"]),
		]
		source_lines.insert(insert_index, tracker)
	return "\n".join(source_lines)


static func _extract_indent(line: String) -> String:
	var indent := ""
	for character in line:
		if character == " " or character == "\t":
			indent += character
		else:
			break
	return indent
