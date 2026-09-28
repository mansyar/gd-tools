class_name GdToolsMock
extends RefCounted

## Runtime link between a generated double and the gd-tools mock machinery.
##
## The doubler embeds an instance of this class into every generated double
## script as `__gd_tools`, passing the double itself plus a values dictionary
## captured at generation time. Generated overrides delegate every behavioural
## decision here: whether the call forwards to the real implementation, what a
## parameter default evaluates to, and what value a stub supplies. All mutable
## mock state lives on the test instance that created the double, so doubles
## never outlive the test that made them.

var _is_partial := false
var _suite: Variant = null
var _script_path := ""


func _init(target: Object, values: Dictionary) -> void:
	_is_partial = bool(values.get("is_partial", false))
	_script_path = str(values.get("path", ""))
	var suite_id := int(values.get("suite_id", 0))
	if suite_id != 0:
		_suite = instance_from_id(suite_id)


## Evaluate a doubled method's parameter default.
##
## Generated overrides declare every parameter with this call as its default
## expression, so calling a double without arguments never errors. The real
## default lives in the method metadata cached on the creating test instance;
## a parameter without one resolves to null, mirroring GUT semantics.
func default_val(method: String, index: int) -> Variant:
	if _suite == null:
		return null
	return _suite._gd_tools_mock_default(_script_path, method, index)


## Return true when the generated override must forward to super().
##
## A partial double forwards every call to the real implementation until a
## stub says otherwise; a full double never forwards. Stub registration in a
## later phase overrides this default per method and per argument match.
func calls_super(method: String, args: Array) -> bool:
	return _is_partial


## Return the value a stub supplies for a call, or null when unstubbed.
##
## Unstubbed doubles answer null (GUT semantics). Stub registration and
## argument matching arrive in a later phase; until then every call resolves
## to null.
func respond(method: String, args: Array) -> Variant:
	return null


## Adapt a call result to the doubled method's declared return type.
##
## Null is not a legal value for typed primitive returns (`-> int`, `-> String`,
## ...), so an unstubbed double of such a method answers with the return
## type's zero value instead of null (GUT semantics hold wherever null is
## legal: Variant, object, and untyped returns pass through untouched). A
## stub's non-null value always passes through unchanged.
func coerce(method: String, value: Variant) -> Variant:
	if value != null:
		return value
	if _suite == null:
		return null
	var return_meta: Dictionary = _suite._gd_tools_mock_return_meta(
			_script_path, method
	)
	if return_meta.is_empty():
		return null
	return _default_for_return(return_meta)


static func _default_for_return(return_meta: Dictionary) -> Variant:
	var type_id := int(return_meta.get("type", TYPE_NIL))
	match type_id:
		TYPE_OBJECT, TYPE_NIL:
			return null
		TYPE_BOOL:
			return false
		TYPE_INT:
			return 0
		TYPE_FLOAT:
			return 0.0
		TYPE_STRING:
			return ""
		TYPE_STRING_NAME:
			return &""
		TYPE_NODE_PATH:
			return ^""
		TYPE_ARRAY:
			return []
		TYPE_DICTIONARY:
			return {}
		TYPE_VECTOR2:
			return Vector2()
		TYPE_VECTOR2I:
			return Vector2i()
		TYPE_RECT2:
			return Rect2()
		TYPE_RECT2I:
			return Rect2i()
		TYPE_VECTOR3:
			return Vector3()
		TYPE_VECTOR3I:
			return Vector3i()
		TYPE_VECTOR4:
			return Vector4()
		TYPE_VECTOR4I:
			return Vector4i()
		TYPE_TRANSFORM2D:
			return Transform2D()
		TYPE_TRANSFORM3D:
			return Transform3D()
		TYPE_PROJECTION:
			return Projection()
		TYPE_QUATERNION:
			return Quaternion()
		TYPE_PLANE:
			return Plane()
		TYPE_AABB:
			return AABB()
		TYPE_BASIS:
			return Basis()
		TYPE_COLOR:
			return Color()
		TYPE_RID:
			return RID()
		TYPE_CALLABLE:
			return Callable()
		TYPE_PACKED_VECTOR2_ARRAY:
			return PackedVector2Array()
		TYPE_PACKED_VECTOR3_ARRAY:
			return PackedVector3Array()
		TYPE_PACKED_VECTOR4_ARRAY:
			return PackedVector4Array()
		TYPE_PACKED_COLOR_ARRAY:
			return PackedColorArray()
		TYPE_PACKED_INT32_ARRAY:
			return PackedInt32Array()
		TYPE_PACKED_INT64_ARRAY:
			return PackedInt64Array()
		TYPE_PACKED_FLOAT32_ARRAY:
			return PackedFloat32Array()
		TYPE_PACKED_FLOAT64_ARRAY:
			return PackedFloat64Array()
		TYPE_PACKED_STRING_ARRAY:
			return PackedStringArray()
		TYPE_PACKED_BYTE_ARRAY:
			return PackedByteArray()
		_:
			return null


## Build the GDScript source text for a test double of a target script.
class Doubler:
	const MOCK_SCRIPT_PATH := "res://addons/gd-tools-test/gd_tools_mock.gd"
	const PARAM_PREFIX := "p_"

	## Collect the doublable methods of a target script.
	##
	## Static methods cannot be reached through an instance and variadic
	## methods cannot be redeclared with a fixed signature, so both are
	## excluded from doubling.
	static func collect_methods(target_script: Script) -> Array:
		var methods: Array = []
		for meta in target_script.get_script_method_list():
			var flags := int(meta.get("flags", 0))
			if flags & METHOD_FLAG_VARARG or flags & METHOD_FLAG_STATIC:
				continue
			methods.append(meta)
		return methods

	## Generate the full source text of a double script.
	##
	## The generated script extends the target by resource path, embeds the
	## creating test instance's id (so runtime decisions can consult the
	## per-test mock state), and redeclares every doublable method as an
	## untyped override whose body delegates to `__gd_tools`. Overriding
	## without return type annotations is what lets a full double return null
	## from methods with typed returns.
	static func generate(
			target_script: Script,
			suite_id: int,
			is_partial: bool,
			methods: Array
	) -> String:
		var lines: Array[String] = []
		lines.append('extends "%s"' % target_script.resource_path)
		lines.append("")
		lines.append("var __gd_tools_values = {")
		lines.append('\t"suite_id": %d,' % suite_id)
		lines.append(
				'\t"is_partial": %s,' % ("true" if is_partial else "false")
		)
		lines.append('\t"path": "%s",' % target_script.resource_path)
		lines.append("}")
		lines.append(
				'var __gd_tools = load("%s").new(self, __gd_tools_values)'
						% MOCK_SCRIPT_PATH
		)
		for meta in methods:
			lines.append("")
			lines.append(_method_text(meta))
		return "\n".join(lines)

	static func _method_text(meta: Dictionary) -> String:
		var method_name := str(meta["name"])
		if method_name == "_init":
			return _init_text(meta)
		var params := _params_text(meta)
		var args := _args_text(meta)
		if _is_void_return(meta):
			# An override of a void method is itself void: it may not return
			# a value at all, so both branches run as plain statements.
			return "\n".join([
					"func %s(%s):" % [method_name, params],
					'\tif __gd_tools.calls_super("%s", [%s]):'
							% [method_name, args],
					"\t\tsuper(%s)" % args,
					"\telse:",
					'\t\t__gd_tools.respond("%s", [%s])' % [method_name, args],
			])
		if _is_nullable_return(meta):
			return "\n".join([
					"func %s(%s):" % [method_name, params],
					'\tif __gd_tools.calls_super("%s", [%s]):'
							% [method_name, args],
					"\t\treturn await super(%s)" % args,
					'\treturn __gd_tools.respond("%s", [%s])'
							% [method_name, args],
			])
		# Typed primitive returns cannot legally answer null, so the stub
		# result goes through coerce() to become the type's zero value.
		return "\n".join([
				"func %s(%s):" % [method_name, params],
				'\tif __gd_tools.calls_super("%s", [%s]):' % [method_name, args],
				"\t\treturn await super(%s)" % args,
				'\treturn __gd_tools.coerce("%s", __gd_tools.respond("%s", [%s]))'
						% [method_name, method_name, args],
		])

	static func _is_void_return(meta: Dictionary) -> bool:
		var return_meta: Dictionary = meta.get("return", {})
		return (
				int(return_meta.get("type", TYPE_NIL)) == TYPE_NIL
				and (
						int(return_meta.get("usage", 0))
						& PROPERTY_USAGE_NIL_IS_VARIANT
				) == 0
		)

	static func _is_nullable_return(meta: Dictionary) -> bool:
		var return_meta: Dictionary = meta.get("return", {})
		var type_id := int(return_meta.get("type", TYPE_NIL))
		if type_id == TYPE_NIL:
			return (
					(
							int(return_meta.get("usage", 0))
							& PROPERTY_USAGE_NIL_IS_VARIANT
					) != 0
			)
		return type_id == TYPE_OBJECT

	static func _init_text(meta: Dictionary) -> String:
		return "\n".join([
				"func _init(%s):" % _params_text(meta),
				"\tsuper(%s)" % _args_text(meta),
		])

	static func _params_text(meta: Dictionary) -> String:
		var method_name := str(meta["name"])
		var params: Array[String] = []
		var args: Array = meta.get("args", [])
		for index in range(args.size()):
			params.append(
					'%s = __gd_tools.default_val("%s", %d)'
							% [PARAM_PREFIX + str(args[index]["name"]), method_name, index]
			)
		return ", ".join(params)

	static func _args_text(meta: Dictionary) -> String:
		var names: Array[String] = []
		for arg in meta.get("args", []):
			names.append(PARAM_PREFIX + str(arg["name"]))
		return ", ".join(names)
