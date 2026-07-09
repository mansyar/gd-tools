extends Node

## Coverage tracker singleton (autoload).
##
## No-op when GD_TOOLS_COVERAGE_ACTIVE env var is not set.
## Records hit counts per (file_id, line_id) pair.

var _active: bool = false
var _hits: Dictionary = {}

func _ready() -> void:
	_active = OS.has_environment("GD_TOOLS_COVERAGE_ACTIVE")
	if _active:
		print("[gd-tools] Coverage tracking active")

func hit(file_id: int, line_id: int) -> void:
	if not _active:
		return
	var key: String = "%d:%d" % [file_id, line_id]
	_hits[key] = _hits.get(key, 0) + 1

func get_hits() -> Dictionary:
	return _hits.duplicate(true)

func reset() -> void:
	_hits.clear()

func is_active() -> bool:
	return _active
