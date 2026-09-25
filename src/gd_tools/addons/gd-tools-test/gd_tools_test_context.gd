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
	## Recursively find nodes whose names match a glob pattern.
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

	var pending: Array[Node] = [_scene_root]
	while not pending.is_empty():
		var node := pending.pop_back()
		if str(node.name).match(pattern):
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
	var signal_callback := _on_wait_signal
	var timeout_callback := _on_wait_timeout
	target_signal.connect(signal_callback, CONNECT_ONE_SHOT)
	var timer := _test.get_tree().create_timer(max(timeout_seconds, 0.001))
	timer.timeout.connect(timeout_callback, CONNECT_ONE_SHOT)
	await wait_resolved
	if target_signal.is_connected(signal_callback):
		target_signal.disconnect(signal_callback)
	if _wait_timed_out:
		_record_failure(
			"integration_signal",
			"Signal wait timed out after %.3f seconds" % timeout_seconds,
			timeout_seconds,
			"a signal before timeout"
		)
	return _wait_signal_received


func clear() -> void:
	## Release references owned by the completed attempt.
	_test = null
	_scene_root = null
	_resources.clear()
	_integration.clear()


func _on_wait_signal() -> void:
	_wait_signal_received = true
	wait_resolved.emit()


func _on_wait_timeout() -> void:
	_wait_timed_out = true
	wait_resolved.emit()


func _record_failure(assertion: String, message: String, actual, expected) -> void:
	if _test != null:
		_test.call("_gd_tools_record_failure", assertion, message, actual, expected)
