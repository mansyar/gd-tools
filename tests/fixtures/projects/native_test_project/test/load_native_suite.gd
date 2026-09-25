extends SceneTree

func _init() -> void:
	var suite_script = load("res://test/native_suite.gd")
	if suite_script == null:
		quit(1)
		return
	var suite = suite_script.new()
	if suite == null:
		quit(1)
		return
	quit(0)
