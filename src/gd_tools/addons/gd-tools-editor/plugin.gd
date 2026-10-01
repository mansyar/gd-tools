@tool
extends EditorPlugin

## Editor plugin entry point for the gd-tools dock.
##
## Instantiates the test/coverage dock panel when the plugin is
## enabled and removes it cleanly when disabled. Dock behavior
## (run buttons, async process runner, results parsing) lives in
## ``dock.gd``.

const DOCK_SCRIPT := "res://addons/gd-tools-editor/dock.gd"
const OVERLAY_SCRIPT := "res://addons/gd-tools-editor/coverage_overlay.gd"

var _dock: Panel = null
var _overlay: Node = null


func _enter_tree() -> void:
	_dock = Panel.new()
	_dock.name = "gd-tools"
	_dock.set_script(load(DOCK_SCRIPT))
	add_control_to_dock(DOCK_SLOT_RIGHT_UL, _dock)

	_overlay = Node.new()
	_overlay.name = "gd-tools-overlay"
	_overlay.set_script(load(OVERLAY_SCRIPT))
	add_child(_overlay)
	_dock.coverage_updated.connect(_overlay.refresh)


func _exit_tree() -> void:
	if _overlay:
		_overlay.clear()
		_overlay.queue_free()
		_overlay = null
	if _dock:
		remove_control_from_docks(_dock)
		_dock.queue_free()
		_dock = null
