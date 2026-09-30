@tool
extends EditorPlugin

## Editor plugin entry point for the gd-tools dock.
##
## Instantiates the test/coverage dock panel when the plugin is
## enabled and removes it cleanly when disabled. Full dock behavior
## (run buttons, async process runner, results parsing) is implemented
## in Phase 2 of the editor plugin track.

const DOCK_SCRIPT := "res://addons/gd-tools-editor/dock.gd"

var _dock: Panel = null


func _enter_tree() -> void:
	_dock = Panel.new()
	_dock.name = "gd-tools"
	_dock.set_script(load(DOCK_SCRIPT))
	add_control_to_dock(DOCK_SLOT_RIGHT_UL, _dock)


func _exit_tree() -> void:
	if _dock:
		remove_control_from_docks(_dock)
		_dock.queue_free()
		_dock = null
