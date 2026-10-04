class_name GdToolsSnapshotSerializer
extends RefCounted

## Canonical, deterministic text rendering for snapshot values.
##
## The snapshot subsystem stores one rendered string per assertion, so the
## output must be byte-identical across repeated runs and platforms. Tier 1
## renders primitives, Arrays, and Dictionaries with sorted keys; Objects and
## node trees extend the same renderer in later phases.

const _INDENT := "  "


## Render a value into its canonical snapshot text.
static func render(value) -> String:
	return _render_value(value, 0)


static func _render_value(value, depth: int) -> String:
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
		TYPE_ARRAY:
			return _render_array(value, depth)
		TYPE_DICTIONARY:
			return _render_dictionary(value, depth)
		_:
			return "<unsupported %s>" % type_string(typeof(value))


static func _render_array(value: Array, depth: int) -> String:
	if value.is_empty():
		return "[]"
	var lines: Array[String] = []
	var inner := _INDENT.repeat(depth + 1)
	for item in value:
		lines.append(inner + _render_value(item, depth + 1))
	return "[\n" + ",\n".join(lines) + "\n" + _INDENT.repeat(depth) + "]"


static func _render_dictionary(value: Dictionary, depth: int) -> String:
	if value.is_empty():
		return "{}"
	var keys := value.keys()
	keys.sort_custom(_key_order)
	var lines: Array[String] = []
	var inner := _INDENT.repeat(depth + 1)
	for key in keys:
		lines.append(inner + _render_key(key) + ": " + _render_value(value[key], depth + 1))
	return "{\n" + ",\n".join(lines) + "\n" + _INDENT.repeat(depth) + "}"


static func _key_order(a, b) -> bool:
	return str(a) < str(b)


static func _render_key(key) -> String:
	if key is String:
		return _quote(key)
	return _render_value(key, 0)


static func _quote(text: String) -> String:
	var escaped := text
	escaped = escaped.replace("\\", "\\\\")
	escaped = escaped.replace("\"", "\\\"")
	escaped = escaped.replace("\n", "\\n")
	escaped = escaped.replace("\t", "\\t")
	return "\"%s\"" % escaped
