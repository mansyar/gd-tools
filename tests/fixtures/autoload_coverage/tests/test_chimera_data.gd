extends GutTest

## GUT tests that exercise ChimeraData methods.
## These calls happen after tracker activation (via pre_run_hook),
## so coverage hits are recorded.

var _chimera: Object


func before_each() -> void:
	_chimera = load("res://scripts/chimera_data.gd").new()


func after_each() -> void:
	_chimera = null


func test_set_and_get_name() -> void:
	_chimera.set_name("Spike")
	assert_eq(_chimera.get_name(), "Spike")


func test_set_and_get_health() -> void:
	_chimera.set_health(50)
	assert_eq(_chimera.get_health(), 50)


func test_is_alive_when_health_positive() -> void:
	_chimera.set_health(10)
	assert_true(_chimera.is_alive())


func test_is_dead_when_health_zero() -> void:
	_chimera.set_health(0)
	assert_false(_chimera.is_alive())
