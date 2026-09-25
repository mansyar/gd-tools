class_name GdToolsTestContext
extends RefCounted

## Explicit access to the scene tree and named resources for one test attempt.

signal wait_resolved

var _test: Node
var _scene_root: Node
var _resources: Dictionary = {}
var _integration: Dictionary = {}
var _wait_signal_received := false
var _wait_timed_out := false
var _wait_signal = null
var _wait_timer = null
var _wait_signal_callback = null
var _wait_timer_callback = null
var _wait_signal_connected := false
var _wait_timer_connected := false


func initialize(
	test: Node, integration: Dictionary, scene_root: Node, resources: Dictionary
) -> void:
	## Initialize the context before lifecycle hooks run for one attempt.
	_test = test
	_integration = integration.duplicate(true)
	_scene_root = scene_root
	_resources = resources.duplicate(true)


func get_scene_root() -> Node:
	## Return the primary scene root, or null for a resource-only attempt.
	return _scene_root


func get_integration() -> Dictionary:
	## Return the effective scene/resource metadata for this attempt.
	return _integration.duplicate(true)


func find_node(relative_path: String) -> Node:
	## Find a node by a path relative to the primary scene root.
	if _scene_root == null:
		_record_failure(
			"integration_scene",
			"Cannot find node '%s' without a primary scene" % relative_path,
			relative_path,
			"a primary scene"
		)
		return null
	if relative_path.is_empty() or relative_path.begins_with("/"):
		_record_failure(
			"integration_node",
			"Scene node path must be relative and non-empty: %s" % relative_path,
			relative_path,
			"a relative node path"
		)
		return null
	var node := _scene_root.get_node_or_null(relative_path) as Node
	if node == null:
		_record_failure(
			"integration_node",
			"Scene node not found: %s" % relative_path,
			relative_path,
			"an existing node"
		)
	return node


func find_nodes(pattern: String) -> Array[Node]:
	## Recursively find nodes whose names contain the given text.
	## A trailing "*" is accepted and ignored, so "Target*" reads as a prefix.
	var matches: Array[Node] = []
	if _scene_root == null:
		_record_failure(
			"integration_scene",
			"Cannot search for '%s' without a primary scene" % pattern,
			pattern,
			"a primary scene"
		)
		return matches
	if pattern.is_empty():
		_record_failure(
			"integration_node_pattern",
			"Scene node pattern must be non-empty",
			pattern,
			"a node name pattern"
		)
		return matches

	# String.match applies the pattern as a regular expression, not a glob, so
	# a leading "Target*" searches for a literal "Target" rather than a prefix.
	# Matching on the name substring keeps both spellings behaving the way the
	# documented prefix example reads.
	var matcher := RegEx.new()
	var literal := pattern.trim_suffix("*")
	if literal.is_empty():
		_record_failure(
			"integration_node_pattern",
			"Scene node pattern must name at least one character: %s" % pattern,
			pattern,
			"a node name pattern"
		)
		return matches
	if matcher.compile(literal) != OK:
		_record_failure(
			"integration_node_pattern",
			"Scene node pattern is not a valid search pattern: %s" % pattern,
			pattern,
			"a plain node name or prefix"
		)
		return matches

	var pending: Array[Node] = [_scene_root]
	while not pending.is_empty():
		var node := pending.pop_back()
		if matcher.search(str(node.name)) != null:
			matches.append(node)
		pending.append_array(node.get_children())

	if matches.is_empty():
		_record_failure(
			"integration_node_pattern",
			"No scene nodes matched pattern: %s" % pattern,
			pattern,
			"at least one matching node"
		)
	return matches


func get_resource(logical_name: String) -> Resource:
	## Return a named resource loaded for this attempt.
	if not _resources.has(logical_name):
		_record_failure(
			"integration_resource",
			"Integration resource not found: %s" % logical_name,
			logical_name,
			"a declared resource"
		)
		return null
	var resource := _resources.get(logical_name) as Resource
	if resource == null:
		_record_failure(
			"integration_resource",
			"Integration resource is not a Resource: %s" % logical_name,
			logical_name,
			"a Resource instance"
		)
	return resource


func wait_for_signal(target_signal: Signal, timeout_seconds: float) -> bool:
	## Wait for a signal with a bounded timeout owned by this context.
	if _test == null:
		_record_failure(
			"integration_context",
			"Cannot wait for a signal without an active test context",
			"missing test",
			"an active test"
		)
		return false

	_wait_signal_received = false
	_wait_timed_out = false
	_wait_signal = target_signal
	_wait_signal_callback = _on_wait_signal
	_wait_timer_callback = _on_wait_timeout
	target_signal.connect(_wait_signal_callback, CONNECT_ONE_SHOT)
	_wait_signal_connected = true
	_wait_timer = _test.get_tree().create_timer(max(timeout_seconds, 0.001))
	_wait_timer.timeout.connect(_wait_timer_callback, CONNECT_ONE_SHOT)
	_wait_timer_connected = true
	await wait_resolved
	_disconnect_wait()
	if _wait_timed_out:
		_record_failure(
			"integration_signal",
			(
				"Signal %s timed out after %.3f seconds"
				% [
					_wait_signal.get_name(),
					timeout_seconds,
				]
			),
			timeout_seconds,
			"a signal before timeout"
		)
	return _wait_signal_received


func capture_screenshot(path: String) -> Dictionary:
	## Capture the active viewport and publish the PNG atomically.
	var message := ""
	var temporary_path := ""
	if _test == null:
		message = "Cannot capture a screenshot without an active test context"
	elif path.is_empty():
		message = "Screenshot path must not be empty"
	else:
		var viewport := _test.get_tree().root
		var texture := viewport.get_texture()
		if texture == null:
			message = "Viewport texture is unavailable"
		else:
			var image := texture.get_image()
			if image == null or image.is_empty():
				message = "Viewport image is empty"
			elif path.is_relative_path():
				message = "Screenshot path must be absolute: %s" % path
			else:
				var directory := path.get_base_dir()
				if not DirAccess.dir_exists_absolute(directory):
					var directory_error := DirAccess.make_dir_recursive_absolute(directory)
					if directory_error != OK:
						message = (
							"Unable to create screenshot directory %s (error %s)"
							% [
								directory,
								directory_error,
							]
						)
				if message.is_empty():
					temporary_path = path + ".tmp"
					var save_error := image.save_png(temporary_path)
					if save_error != OK:
						DirAccess.remove_absolute(temporary_path)
						message = (
							"Unable to write screenshot %s (error %s)"
							% [
								path,
								save_error,
							]
						)
				if message.is_empty() and FileAccess.file_exists(path):
					var remove_error := DirAccess.remove_absolute(path)
					if remove_error != OK:
						message = (
							"Unable to replace screenshot %s (error %s)"
							% [
								path,
								remove_error,
							]
						)
				if message.is_empty():
					var rename_error := DirAccess.rename_absolute(temporary_path, path)
					if rename_error != OK:
						DirAccess.remove_absolute(temporary_path)
						message = (
							"Unable to publish screenshot %s (error %s)"
							% [
								path,
								rename_error,
							]
						)
	return {"ok": message.is_empty(), "path": path, "message": message}


func clear() -> void:
	## Release references owned by the completed attempt.
	if _wait_signal_connected or _wait_timer_connected:
		_wait_timed_out = true
		wait_resolved.emit()
	_disconnect_wait()
	_test = null
	_scene_root = null
	_resources.clear()
	_integration.clear()


func _disconnect_wait() -> void:
	if _wait_signal_connected:
		if _wait_signal.is_connected(_wait_signal_callback):
			_wait_signal.disconnect(_wait_signal_callback)
		_wait_signal_connected = false
	if _wait_timer_connected:
		if _wait_timer.timeout.is_connected(_wait_timer_callback):
			_wait_timer.timeout.disconnect(_wait_timer_callback)
		_wait_timer_connected = false
	_wait_signal = null
	_wait_timer = null
	_wait_signal_callback = null
	_wait_timer_callback = null


func _on_wait_signal() -> void:
	_wait_signal_received = true
	wait_resolved.emit()


func _on_wait_timeout() -> void:
	_wait_timed_out = true
	wait_resolved.emit()


func _record_failure(assertion: String, message: String, actual, expected) -> void:
	if _test != null:
		_test.call("_gd_tools_record_failure", assertion, message, actual, expected)
