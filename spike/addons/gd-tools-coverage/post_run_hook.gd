extends GutHookScript

## GUT post-run hook for coverage data serialization.
##
## Reads hit data from the _GDTCoverage tracker autoload and writes
## it to a JSON file. Activated when the tracker is active
## (GD_TOOLS_COVERAGE_ACTIVE environment variable is set).
## Output path configured via GD_TOOLS_COVERAGE_OUTPUT
## environment variable (default: user://coverage.json).

func run() -> void:
	var tracker: Node = _get_tracker()
	if tracker == null:
		push_error("[gd-tools] Cannot find _GDTCoverage autoload node\n  Cause: Tracker autoload is not registered in project.godot.\n  Fix: Verify _GDTCoverage is listed under [autoload] in project.godot.")
		return
	if not tracker.is_active():
		return
	var output_path: String = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
	if output_path.is_empty():
		output_path = "user://coverage.json"
	var hits: Dictionary = tracker.get_hits()
	var files: Array = _hits_to_files(hits)
	var data: Dictionary = {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"files": files
	}
	var file: FileAccess = FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_error("[gd-tools] Cannot open output file: " + output_path + "\n  Cause: Directory does not exist or is not writable.\n  Fix: Verify GD_TOOLS_COVERAGE_OUTPUT points to a writable path.")
		return
	file.store_string(JSON.stringify(data, "  "))
	file.close()
	print("[gd-tools] Coverage data written to: " + output_path + " (" + str(hits.size()) + " hit points)")

## Convert flat "file_id:line_id" hits to per-file format.
##
## The tracker stores hits with composite keys like "0:3" (file_id 0,
## line_id 3). The reporter expects a "files" array where each entry
## has "file_id" (int) and "hits" (dict with string line_id keys).
func _hits_to_files(hits: Dictionary) -> Array:
	var file_map: Dictionary = {}
	for key in hits:
		var parts: PackedStringArray = key.split(":")
		if parts.size() != 2:
			continue
		var file_id: int = parts[0].to_int()
		var line_id: String = parts[1]
		if not file_map.has(file_id):
			file_map[file_id] = {}
		file_map[file_id][line_id] = hits[key]
	var files: Array = []
	for file_id in file_map:
		files.append({"file_id": file_id, "hits": file_map[file_id]})
	return files

## Gets the _GDTCoverage tracker autoload node from the scene tree.
func _get_tracker() -> Node:
	var tree: SceneTree = Engine.get_main_loop() as SceneTree
	if tree == null:
		return null
	return tree.root.get_node_or_null("_GDTCoverage")
