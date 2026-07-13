extends GutHookScript

## Post-run hook for GUT test runner.
## Collects coverage data from the _GDTCoverage tracker and
## writes it to a JSON file after tests have executed.

const TRACKER_NAME = "_GDTCoverage"


func run() -> void:
	var tracker = _get_tracker()
	if tracker == null:
		return

	if not tracker.is_active():
		return

	var hits: Dictionary = tracker.get_hits()
	var data: Dictionary = _build_coverage_json(hits)

	var output_path: String = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
	if output_path.is_empty():
		_log_error(
			"Cannot write coverage output.",
			"GD_TOOLS_COVERAGE_OUTPUT environment variable is not set.",
			"Set GD_TOOLS_COVERAGE_OUTPUT to a writable file path."
		)
		return

	if not _write_json(output_path, data):
		return

	_log_summary(hits, output_path)


func _get_tracker() -> Node:
	var tree = Engine.get_main_loop() as SceneTree
	if tree == null:
		_log_error(
			"Cannot access coverage tracker.",
			"SceneTree is not available.",
			"Ensure the hook runs in a Godot project context."
		)
		return null

	var tracker = tree.root.get_node_or_null(TRACKER_NAME)
	if tracker == null:
		_log_error(
			"Cannot access coverage tracker.",
			"Autoload '" + TRACKER_NAME + "' not found.",
			"Ensure the coverage addon is installed and registered as an autoload."
		)
		return null

	return tracker


func _build_coverage_json(hits: Dictionary) -> Dictionary:
	var files: Array = []
	for file_id in hits:
		var file_hits: Dictionary = hits[file_id]
		var hits_dict: Dictionary = {}
		for line_id in file_hits:
			hits_dict[str(line_id)] = file_hits[line_id]
		files.append({"file_id": int(file_id), "hits": hits_dict})
	return {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"files": files
	}


func _write_json(path: String, data: Dictionary) -> bool:
	var dir_path: String = path.get_base_dir()
	if not dir_path.is_empty() and not DirAccess.dir_exists_absolute(dir_path):
		var err: int = DirAccess.make_dir_recursive_absolute(dir_path)
		if err != OK:
			_log_error(
				"Cannot create output directory.",
				"Failed to create directory: " + dir_path,
				"Check permissions and path validity."
			)
			return false

	var file = FileAccess.open(path, FileAccess.WRITE)
	if file == null:
		_log_error(
			"Cannot write coverage output.",
			"Cannot open file for writing: " + path,
			"Check file permissions and path validity."
		)
		return false

	file.store_string(JSON.stringify(data, "  "))
	file = null
	return true


func _log_summary(hits: Dictionary, output_path: String) -> void:
	var total_files: int = hits.size()
	var total_lines: int = 0
	for file_id in hits:
		total_lines += hits[file_id].size()
	print(
		"[gd-tools] Coverage summary: %d files, %d lines tracked, output: %s"
		% [total_files, total_lines, output_path]
	)


func _log_error(what: String, cause: String, fix: String) -> void:
	push_error("[gd-tools] [Error] " + what + "\n\n" + "  Cause: " + cause + "\n" + "  Fix:   " + fix)
