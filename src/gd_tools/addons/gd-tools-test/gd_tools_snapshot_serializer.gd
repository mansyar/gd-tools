class_name GdToolsSnapshotSerializer
extends RefCounted

## Canonical, deterministic text rendering for snapshot values.
##
## The snapshot subsystem stores one rendered string per assertion, so the
## output must be byte-identical across repeated runs and platforms. Tier 1
## renders primitives, Arrays, and Dictionaries with sorted keys; Objects and
## node trees extend the same renderer.

const _INDENT := "  "


## Render a value into its canonical snapshot text.
static func render(value) -> String:
	return _render_value(value, 0, [])


static func _render_value(value, depth: int, path: Array) -> String:
	if value == null:
		return "null"
	match typeof(value):
		TYPE_BOOL:
			return "true" if value else "false"
		TYPE_INT:
			return str(value)
		TYPE_FLOAT:
			return str(value)
		TYPE_STRING:
			return _quote(str(value))
		TYPE_ARRAY, TYPE_DICTIONARY, TYPE_OBJECT:
			if _is_on_path(value, path):
				return "<ref>"
			var next_path := path + [value]
			match typeof(value):
				TYPE_ARRAY:
					return _render_array(value, depth, next_path)
				TYPE_DICTIONARY:
					return _render_dictionary(value, depth, next_path)
				_:
					if value is Node:
						return _render_node_tree(value, depth, "", next_path)
					return _render_object(value, depth, next_path)
		_:
			return "<unsupported %s>" % type_string(typeof(value))


## Report whether a reference-type value is already on the active render path.
##
## Containers and Objects are reference types, so a value that appears on the
## active path would recurse forever without this guard. The check uses
## identity comparison, never content equality, so cyclic structures are safe
## to probe. Non-cyclic shared references are rendered in full each time so
## no information is lost.
static func _is_on_path(value, path: Array) -> bool:
	for ancestor in path:
		if is_same(ancestor, value):
			return true
	return false


static func _render_array(value: Array, depth: int, path: Array) -> String:
	if value.is_empty():
		return "[]"
	var lines: Array[String] = []
	var inner := _INDENT.repeat(depth + 1)
	for item in value:
		lines.append(inner + _render_value(item, depth + 1, path))
	return "[\n" + ",\n".join(lines) + "\n" + _INDENT.repeat(depth) + "]"


static func _render_dictionary(value: Dictionary, depth: int, path: Array) -> String:
	if value.is_empty():
		return "{}"
	var keys := value.keys()
	keys.sort_custom(_key_order)
	var lines: Array[String] = []
	var inner := _INDENT.repeat(depth + 1)
	for key in keys:
		lines.append(inner + _render_key(key) + ": " + _render_value(value[key], depth + 1, path))
	return "{\n" + ",\n".join(lines) + "\n" + _INDENT.repeat(depth) + "}"


static func _key_order(a, b) -> bool:
	return str(a) < str(b)


## Render one object as a header line plus its stored script properties.
static func _render_object(value: Object, depth: int, path: Array) -> String:
	var script: Script = value.get_script()
	var lines := _render_stored_properties(value, script, depth, path)
	var header := "Object:%s" % _object_type_name(value, script)
	if lines.is_empty():
		return header
	return header + "\n" + "\n".join(lines)


static func _render_node_tree(
	node: Node, depth: int, path: String, seen: Array
) -> String:
	var node_path := path if path != "" else "/"
	var header := "Node:%s (%s)" % [node_path, node.get_class()]
	var lines := _render_stored_properties(node, node.get_script(), depth, seen)
	var inner := _INDENT.repeat(depth + 1)
	for child in node.get_children():
		var child_path := path + "/" + str(child.name)
		lines.append(inner + _render_node_tree(child, depth + 1, child_path, seen))
	if lines.is_empty():
		return header
	return header + "\n" + "\n".join(lines)


static func _render_stored_properties(
	value: Object, script: Script, depth: int, path: Array
) -> Array[String]:
	var lines: Array[String] = []
	if script == null:
		return lines
	var names: Array[String] = []
	for prop in script.get_script_property_list():
		if int(prop.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			names.append(str(prop.name))
	names.sort()
	var inner := _INDENT.repeat(depth + 1)
	for prop_name in names:
		lines.append(
			inner
			+ prop_name
			+ ": "
			+ _render_value(value.get(prop_name), depth + 1, path)
		)
	return lines


static func _object_type_name(value: Object, script: Script) -> String:
	if script != null and str(script.resource_path) != "":
		return str(script.resource_path)
	return value.get_class()


static func _render_key(key) -> String:
	if key is String:
		return _quote(key)
	return _render_value(key, 0, [])


static func _quote(text: String) -> String:
	var escaped := text
	escaped = escaped.replace("\\", "\\\\")
	escaped = escaped.replace("\"", "\\\"")
	escaped = escaped.replace("\n", "\\n")
	escaped = escaped.replace("\t", "\\t")
	return "\"%s\"" % escaped
