extends RefCounted

## GUT post-run hook for coverage data serialization.
##
## Reads hit data from the _GDTCoverage tracker autoload and writes
## it to a JSON file. Activated when the tracker is active
## (GD_TOOLS_COVERAGE_ACTIVE environment variable is set).
## Output path configured via GD_TOOLS_COVERAGE_OUTPUT
## environment variable (default: user://coverage.json).

func _init() -> void:
	var tracker: Node = _get_tracker()
	if tracker == null:
		push_error("[gd-tools] Cannot find _GDTCoverage autoload node")
		return
	if not tracker.is_active():
		return
	var output_path: String = OS.get_environment("GD_TOOLS_COVERAGE_OUTPUT")
	if output_path.is_empty():
		output_path = "user://coverage.json"
	var hits: Dictionary = tracker.get_hits()
	var data: Dictionary = {
		"version": 1,
		"generated_at": Time.get_datetime_string_from_system(true, false) + "Z",
		"hits": hits
	}
	var file: FileAccess = FileAccess.open(output_path, FileAccess.WRITE)
	if file == null:
		push_error("[gd-tools] Cannot open output file: " + output_path)
		return
	file.store_string(JSON.stringify(data, "  "))
	file.close()
	print("[gd-tools] Coverage data written to: " + output_path + " (" + str(hits.size()) + " hit points)")

## Gets the _GDTCoverage tracker autoload node from the scene tree.
func _get_tracker() -> Node:
	var tree: SceneTree = Engine.get_main_loop() as SceneTree
	if tree == null:
		return null
	return tree.root.get_node_or_null("_GDTCoverage")
