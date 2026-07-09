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

## Record a hit at (file_id, line_id). No-op if tracker is inactive.
func hit(file_id: int, line_id: int) -> void:
	if not _active:
		return
	var key: String = "%d:%d" % [file_id, line_id]
	_hits[key] = _hits.get(key, 0) + 1

## Return a deep copy of the hit counts dictionary.
func get_hits() -> Dictionary:
	return _hits.duplicate(true)

## Clear all recorded hits.
func reset() -> void:
	_hits.clear()

## Return whether the tracker is active (env var was set at startup).
func is_active() -> bool:
	return _active
