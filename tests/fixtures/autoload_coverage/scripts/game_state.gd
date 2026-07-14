extends Node

## Autoload that creates ChimeraData instances during _ready().
## This simulates the pattern where autoloads instantiate other scripts,
## which previously caused ERR_ALREADY_IN_USE during coverage instrumentation
## because the pre-run hook ran after instances already existed.

var _chimera: Object


func _ready() -> void:
	_chimera = load("res://scripts/chimera_data.gd").new()
	_chimera.set_name("Fluffy")
	_chimera.set_health(100)


func get_chimera() -> Object:
	return _chimera
