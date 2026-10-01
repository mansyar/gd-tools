@tool
extends Node

## In-editor coverage heatmap overlay.
##
## Loads ``plan.json`` + ``coverage.json`` from ``.gd-tools/coverage/``
## and paints per-line background colors on the active script editor's
## ``CodeEdit``: green = covered, red = uncovered, yellow = partial
## branch (the same semantics as the HTML reporter). When a script
## file's modification time is newer than the coverage data, colors are
## rendered muted — stale results are never shown as fresh, and stale
## markings are never silently cleared.

signal coverage_data_changed

const COVERAGE_DIR := "res://.gd-tools/coverage"
const COLOR_COVERED := Color(0.2, 0.85, 0.3, 0.18)
const COLOR_UNCOVERED := Color(0.95, 0.2, 0.2, 0.16)
const COLOR_PARTIAL := Color(1.0, 0.8, 0.0, 0.2)
const STALE_ALPHA_FACTOR := 0.4
const TRANSPARENT := Color(0.0, 0.0, 0.0, 0.0)

## Responsiveness guard: files with more planned lines than this are
## skipped (with a notice) so opening them never lags the editor.
const MAX_OVERLAY_LINES := 5000

## res:// path -> {line number (1-based) -> "covered"|"uncovered"|"partial"}
var _line_statuses: Dictionary = {}
var _data_modified_time: int = 0
var _painted_lines: Array[int] = []
var _painted_code_edit: CodeEdit = null
var _painted_signature := ""


func _ready() -> void:
	if not Engine.is_editor_hint():
		return
	load_coverage()
	var script_editor := EditorInterface.get_script_editor()
	script_editor.editor_script_changed.connect(_on_script_changed)
	apply_to_current_script()


## Reloads the coverage artifacts and repaints the active script.
func refresh() -> void:
	load_coverage()
	coverage_data_changed.emit()
	apply_to_current_script()


## Removes all painted colors (used when the plugin is disabled).
func clear() -> void:
	if _painted_code_edit != null:
		for line: int in _painted_lines:
			_painted_code_edit.set_line_background_color(
				line, TRANSPARENT
			)
	_painted_code_edit = null
	_painted_lines = []
	_painted_signature = ""


## Loads plan.json + coverage.json into the per-file status map.
func load_coverage() -> Dictionary:
	_line_statuses = {}
	_data_modified_time = 0
	var plan := _load_json(COVERAGE_DIR + "/plan.json")
	var data := _load_json(COVERAGE_DIR + "/coverage.json")
	if plan.is_empty() or data.is_empty():
		return _line_statuses
	_data_modified_time = FileAccess.get_modified_time(
		COVERAGE_DIR + "/coverage.json"
	)
	var hits_by_id := {}
	for entry: Dictionary in data.get("files", []):
		hits_by_id[_json_id_key(entry.get("file_id"))] = entry.get(
			"hits", {}
		)
	for file_plan: Dictionary in plan.get("files", []):
		var res_path := str(file_plan.get("path", ""))
		if res_path.is_empty():
			continue
		var hits: Dictionary = hits_by_id.get(
			_json_id_key(file_plan.get("file_id")), {}
		)
		var statuses := _statuses_for_file(file_plan, hits)
		if statuses.is_empty():
			continue
		_line_statuses[res_path] = statuses
	return _line_statuses


## True when the given res:// source file was modified after the
## coverage data was written (its colors would be stale).
func is_stale(res_path: String) -> bool:
	if _data_modified_time <= 0:
		return false
	if not FileAccess.file_exists(res_path):
		return false
	var source_time := FileAccess.get_modified_time(res_path)
	return source_time > _data_modified_time


## Paints the heatmap for the currently edited script, if any.
func apply_to_current_script() -> void:
	if not Engine.is_editor_hint():
		return
	var script_editor := EditorInterface.get_script_editor()
	var current_script := script_editor.get_current_script()
	clear()
	if current_script == null:
		return
	var res_path := current_script.resource_path
	_apply_to_script(script_editor, res_path)


func _on_script_changed(_script: Script) -> void:
	apply_to_current_script()


func _apply_to_script(script_editor: Variant, res_path: String) -> void:
	var statuses: Dictionary = _line_statuses.get(res_path, {})
	var editor_base: Variant = script_editor.get_current_editor()
	if editor_base == null:
		return
	var code_edit := _find_code_edit(editor_base)
	if code_edit == null:
		return
	var stale := is_stale(res_path)
	var signature := "%s|%d|%s" % [res_path, _data_modified_time, stale]
	if signature == _painted_signature:
		return
	if statuses.is_empty():
		return
	if statuses.size() > MAX_OVERLAY_LINES:
		print(
			"gd-tools: skipping coverage overlay for %s "
			+ "(%d planned lines exceeds the %d-line guard)"
			% [res_path, statuses.size(), MAX_OVERLAY_LINES]
		)
		return
	_painted_signature = signature
	_painted_code_edit = code_edit
	for line_no: int in statuses:
		var color := _color_for(str(statuses[line_no]), stale)
		var index := line_no - 1
		if index < 0 or index >= code_edit.get_line_count():
			continue
		code_edit.set_line_background_color(index, color)
		_painted_lines.append(index)


func _statuses_for_file(
	file_plan: Dictionary,
	hits: Dictionary,
) -> Dictionary:
	var statuses := {}
	for line_plan: Dictionary in file_plan.get("lines", []):
		var line_no := int(line_plan.get("line", 0))
		var hit := int(hits.get(_json_id_key(line_plan.get("id", "")), 0))
		var status := "uncovered"
		if hit > 0:
			if str(line_plan.get("type", "")) == "branch":
				status = "partial"
			else:
				status = "covered"
		statuses[line_no] = status
	return statuses


func _color_for(status: String, stale: bool) -> Color:
	var color := COLOR_UNCOVERED
	match status:
		"covered":
			color = COLOR_COVERED
		"partial":
			color = COLOR_PARTIAL
	if stale:
		color.a *= STALE_ALPHA_FACTOR
	return color


func _find_code_edit(editor_base: Variant) -> CodeEdit:
	var found: Array = editor_base.find_children(
		"", "CodeEdit", true, false
	)
	for child: Variant in found:
		if child is CodeEdit:
			return child
	return null


## Normalizes a numeric JSON value to its string key form.
##
## Godot parses JSON integers as floats, and ``str(0.0)`` yields
## ``"0.0"`` — which would never match the ``"0"`` object keys in
## coverage.json. Normalizing through ``int()`` first guarantees a
## stable key on both sides of the lookup.
func _json_id_key(value: Variant) -> String:
	return str(int(value))


func _load_json(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	return parsed
