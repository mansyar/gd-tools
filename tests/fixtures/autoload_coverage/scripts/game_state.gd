extends Node

## Autoload that creates ChimeraData instances during _ready().
## Godot creates all autoload instances before calling any _ready(),
## so reload(true) (keep_state) is used to instrument scripts that
## already have active instances.

var _chimera: Object


func _ready() -> void:
	_chimera = load("res://scripts/chimera_data.gd").new()
	_chimera.set_name("Fluffy")
	_chimera.set_health(100)


func get_chimera() -> Object:
	return _chimera
