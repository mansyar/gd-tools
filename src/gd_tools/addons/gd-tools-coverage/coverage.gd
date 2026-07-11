extends Node

# Coverage tracker autoload for gd-tools.
# Records line hit counts during GUT test execution.
# Activated via the GD_TOOLS_COVERAGE_ACTIVE environment variable.

var _hits: Dictionary = {}

var _active: bool = false


func _ready() -> void:
	# Active only when GD_TOOLS_COVERAGE_ACTIVE is "1" or "true".
	var env_val: String = OS.get_environment("GD_TOOLS_COVERAGE_ACTIVE")
	env_val = env_val.to_lower()
	_active = env_val == "1" or env_val == "true"


func hit(file_id: int, line_id: int) -> void:
	# Single bool check for minimal overhead when inactive.
	if not _active:
		return
	if not _hits.has(file_id):
		_hits[file_id] = {}
	if not _hits[file_id].has(line_id):
		_hits[file_id][line_id] = 0
	_hits[file_id][line_id] += 1


func get_hits() -> Dictionary:
	return _hits


func reset() -> void:
	_hits.clear()


func set_active(active: bool) -> void:
	_active = active


func is_active() -> bool:
	return _active
