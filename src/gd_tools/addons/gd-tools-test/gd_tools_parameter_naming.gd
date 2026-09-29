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


static func _stringify(value: Variant, case_index: int) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_ARRAY, TYPE_DICTIONARY, TYPE_OBJECT:
			return str(case_index)
		_:
			return str(value)
