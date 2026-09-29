extends RefCounted

## Static helpers for deterministic parameterized case names.
##
## Case names are pytest-style suffixes on the method name: each value is
## stringified (strings verbatim, primitives via ``str``), and unstable
## types such as Objects, Dictionaries and Arrays fall back to the case
## index so the same declaration always produces the same names. Multiple
## values are hyphen-joined.


static func case_suffix(values: Array, case_index: int) -> String:
	var parts: Array[String] = []
	for value in values:
		parts.append(_stringify(value, case_index))
	return "[%s]" % "-".join(parts)


static func normalize_value_set(value_set: Variant) -> Array:
	## Godot's JSON parser decodes every number as a float; restore whole
	## numbers to ints so declared values and case names keep the form the
	## author wrote after a manifest round trip.
	var normalized: Array = []
	if typeof(value_set) != TYPE_ARRAY:
		return normalized
	for value: Variant in value_set:
		if typeof(value) == TYPE_ARRAY:
			normalized.append(normalize_value_set(value))
		else:
			normalized.append(normalize_value(value))
	return normalized


static func normalize_value(value: Variant) -> Variant:
	if typeof(value) != TYPE_FLOAT:
		return value
	var number := float(value)
	if not is_nan(number) and absf(number) <= 9007199254740992.0 and number == floorf(number):
		return int(number)
	return value


static func _stringify(value: Variant, case_index: int) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_ARRAY, TYPE_DICTIONARY, TYPE_OBJECT:
			return str(case_index)
		_:
			return str(value)
