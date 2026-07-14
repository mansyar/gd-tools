extends RefCounted

## Data class instantiated by the GameState autoload.
## Instruments correctly because coverage.gd uses reload(true)
## (keep_state) which reloads source without discarding instances.

var _name: String = ""
var _health: int = 0


func set_name(value: String) -> void:
	_name = value


func get_name() -> String:
	return _name


func set_health(value: int) -> void:
	_health = value


func get_health() -> int:
	return _health


func is_alive() -> bool:
	return _health > 0
