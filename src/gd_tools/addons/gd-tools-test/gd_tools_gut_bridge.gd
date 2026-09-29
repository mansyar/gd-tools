## GUT compatibility bridge base class (Migration Phase 3).
##
## Provides the documented core GUT subset on top of the native runtime so
## legacy GUT-style suites run through `gd-tools test` without the GUT addon
## installed. Suites keep their `extends GutTest` line and resolve to this
## class, which forwards every supported construct onto the native
## `GdToolsTest` machinery: the same result contract, statuses, coverage and
## artifacts as native suites.
##
## Supported subset (see `docs/gut-migration.md`):
## - Lifecycle hooks: `before_all`, `after_all`, `before_each`, `after_each`,
##   `prerun_setup`, `postrun_teardown` (inherited by user suites; the runner
##   invokes them duck-typed).
## - Core value/comparison, string and file assertions.
## - The signal family (`watch_signals` plus the `assert_signal_*` set).
## - Async helpers (`wait_*` and legacy `yield_*` aliases).
## - Skipping (`skip_test`, `skip_if_godot_version_lt/ne`).
## - Mocking (`double`, `partial_double`, `stub`, `assert_called*`), inherited
##   from the native `GdToolsTest` runtime with identical semantics.
##
## Parameterization (`parameterize`/`use_parameters`) is native now: bridge
## suites use the same declaration validation, case expansion, and naming as
## native suites. Remaining unsupported GUT constructs (property/orphan
## checks, engine-error asserts) are rejected by the preflight static scan
## before any test runs, with migration guidance.
class_name GutTest
extends GdToolsTest

const _GUT_MAX_SIGNAL_ARGS := 10

## Per-object emission records: object -> signal name -> {count, params}.
var _gut_signal_watchers: Dictionary = {}


## # GUT signal family -------------------------------------------------------------

## Watch every declared signal on [param object], recording emissions and
## their parameters for the `assert_signal_*` family.
func watch_signals(object: Object) -> void:
	if object == null:
		_gut_fail("watch_signals", "watch_signals() called with a null object")
		return
	if _gut_signal_watchers.has(object):
		return
	_gut_signal_watchers[object] = {}
	for signal_info in object.get_signal_list():
		_gut_watch_signal(object, str(signal_info["name"]))


func _gut_watch_signal(object: Object, signal_name: String) -> void:
	if _gut_signal_watchers.has(object) and _gut_signal_watchers[object].has(signal_name):
		return
	var arity := 0
	for signal_info in object.get_signal_list():
		if str(signal_info["name"]) == signal_name:
			arity = (signal_info["args"] as Array).size()
			break
	if arity > _GUT_MAX_SIGNAL_ARGS:
		_gut_fail(
				"watch_signals",
				"Signal '%s' has %d arguments; the bridge watches at most %d"
						% [signal_name, arity, _GUT_MAX_SIGNAL_ARGS]
		)
		return
	_gut_signal_watchers[object][signal_name] = {"count": 0, "params": []}
	object.connect(
			signal_name,
			Callable(self, "_gut_on_signal_%d" % arity).bind(object, signal_name)
	)


## The bound arguments land positionally after the emitted ones, so every
## handler below declares exactly `arity + 2` parameters: the emitted
## arguments, then the watched object and the signal name appended by
## `Callable.bind()`.
func _gut_on_signal_0(watched: Object, signal_name: String) -> void:
	_gut_record_emission(watched, signal_name, [])


func _gut_on_signal_1(arg0, watched: Object, signal_name: String) -> void:
	_gut_record_emission(watched, signal_name, [arg0])


func _gut_on_signal_2(arg0, arg1, watched: Object, signal_name: String) -> void:
	_gut_record_emission(watched, signal_name, [arg0, arg1])


func _gut_on_signal_3(arg0, arg1, arg2, watched: Object, signal_name: String) -> void:
	_gut_record_emission(watched, signal_name, [arg0, arg1, arg2])


func _gut_on_signal_4(
		arg0, arg1, arg2, arg3, watched: Object, signal_name: String
) -> void:
	_gut_record_emission(watched, signal_name, [arg0, arg1, arg2, arg3])


func _gut_on_signal_5(
		arg0, arg1, arg2, arg3, arg4, watched: Object, signal_name: String
) -> void:
	_gut_record_emission(watched, signal_name, [arg0, arg1, arg2, arg3, arg4])


func _gut_on_signal_6(
		arg0, arg1, arg2, arg3, arg4, arg5, watched: Object, signal_name: String
) -> void:
	_gut_record_emission(
			watched, signal_name, [arg0, arg1, arg2, arg3, arg4, arg5]
	)


func _gut_on_signal_7(
		arg0, arg1, arg2, arg3, arg4, arg5, arg6, watched: Object, signal_name: String
) -> void:
	_gut_record_emission(
			watched, signal_name, [arg0, arg1, arg2, arg3, arg4, arg5, arg6]
	)


func _gut_on_signal_8(
		arg0,
		arg1,
		arg2,
		arg3,
		arg4,
		arg5,
		arg6,
		arg7,
		watched: Object,
		signal_name: String
) -> void:
	_gut_record_emission(
			watched, signal_name, [arg0, arg1, arg2, arg3, arg4, arg5, arg6, arg7]
	)


func _gut_on_signal_9(
		arg0,
		arg1,
		arg2,
		arg3,
		arg4,
		arg5,
		arg6,
		arg7,
		arg8,
		watched: Object,
		signal_name: String
) -> void:
	_gut_record_emission(
			watched,
			signal_name,
			[arg0, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8]
	)


func _gut_on_signal_10(
		arg0,
		arg1,
		arg2,
		arg3,
		arg4,
		arg5,
		arg6,
		arg7,
		arg8,
		arg9,
		watched: Object,
		signal_name: String
) -> void:
	_gut_record_emission(
			watched,
			signal_name,
			[arg0, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9]
	)


func _gut_record_emission(watched: Object, signal_name: String, params: Array) -> void:
	var watched_map: Dictionary = _gut_signal_watchers.get(watched, {})
	if not watched_map.has(signal_name):
		return
	var record: Dictionary = watched_map[signal_name]
	record["count"] = int(record["count"]) + 1
	(record["params"] as Array).append(params)


func _gut_watched_record(object: Object, signal_name: String) -> Dictionary:
	if not _gut_signal_watchers.has(object):
		return {}
	var watched: Dictionary = _gut_signal_watchers[object]
	if not watched.has(signal_name):
		return {}
	return watched[signal_name]


func assert_signal_emitted(object: Object, signal_name: String, text: String = "") -> void:
	var record := _gut_watched_record(object, signal_name)
	if record.is_empty():
		_gut_fail(
				"assert_signal_emitted",
				_object_not_watched_message(object, signal_name)
		)
		return
	if int(record["count"]) <= 0:
		_gut_fail(
				"assert_signal_emitted",
				_gut_detail(
						text,
						"Expected signal '%s' to be emitted, but it was not" % signal_name
				)
		)


func assert_signal_not_emitted(object: Object, signal_name: String, text: String = "") -> void:
	var record := _gut_watched_record(object, signal_name)
	if record.is_empty():
		_gut_fail(
				"assert_signal_not_emitted",
				_object_not_watched_message(object, signal_name)
		)
		return
	if int(record["count"]) > 0:
		_gut_fail(
				"assert_signal_not_emitted",
				_gut_detail(
						text,
						"Expected signal '%s' NOT to be emitted, but it was emitted %d time(s)"
								% [signal_name, int(record["count"])]
				)
		)


func assert_signal_emit_count(
		object: Object,
		signal_name: String,
		expected: int,
		text: String = ""
) -> void:
	var record := _gut_watched_record(object, signal_name)
	if record.is_empty():
		_gut_fail(
				"assert_signal_emit_count",
				_object_not_watched_message(object, signal_name)
		)
		return
	var actual := int(record["count"])
	if actual != expected:
		_gut_fail(
				"assert_signal_emit_count",
				_gut_detail(
						text,
						"Expected signal '%s' to be emitted %d time(s), but it was emitted %d time(s)"
								% [signal_name, expected, actual]
				),
				actual,
				expected
		)


func assert_signal_emitted_with_parameters(
		object: Object,
		signal_name: String,
		parameters: Array,
		index: int = -1,
		text: String = ""
) -> void:
	var record := _gut_watched_record(object, signal_name)
	if record.is_empty():
		_gut_fail(
				"assert_signal_emitted_with_parameters",
				_object_not_watched_message(object, signal_name)
		)
		return
	var emissions: Array = record["params"]
	if emissions.is_empty():
		_gut_fail(
				"assert_signal_emitted_with_parameters",
				_gut_detail(
						text,
						"Signal '%s' was never emitted, so no parameters were recorded"
								% signal_name
				)
		)
		return
	var emission_index := index
	if emission_index < 0:
		emission_index = emissions.size() + emission_index
	if emission_index < 0 or emission_index >= emissions.size():
		_gut_fail(
				"assert_signal_emitted_with_parameters",
				_gut_detail(
						text,
						"Emission index %d is out of range for signal '%s' (%d emission(s))"
								% [index, signal_name, emissions.size()]
				)
		)
		return
	var actual: Array = emissions[emission_index]
	if not _gut_params_match(actual, parameters):
		_gut_fail(
				"assert_signal_emitted_with_parameters",
				_gut_detail(
						text,
						"Expected signal '%s' to be emitted with parameters %s, but got %s"
								% [signal_name, parameters, actual]
				),
				actual,
				parameters
		)


func assert_has_signal(object: Object, signal_name: String, text: String = "") -> void:
	if object == null or not object.has_signal(signal_name):
		_gut_fail(
				"assert_has_signal",
				_gut_detail(
						text,
						"Expected object %s to have signal '%s', but it does not"
								% [object, signal_name]
				)
		)


func assert_connected(p1, p2, p3 = null, p4 = null) -> void:
	var connected := _gut_is_connected(p1, p2, p3, p4)
	if not connected.ok:
		_gut_fail("assert_connected", connected.message)
	elif not connected.value:
		_gut_fail("assert_connected", connected.message)


func assert_not_connected(p1, p2, p3 = null, p4 = null) -> void:
	var connected := _gut_is_connected(p1, p2, p3, p4)
	if not connected.ok:
		_gut_fail("assert_not_connected", connected.message)
	elif connected.value:
		_gut_fail("assert_not_connected", connected.message)


## Resolve the two GUT call forms for the connected-assertions:
## `(signal_name, source, method)` or `(source, signal_name, target, method)`.
func _gut_is_connected(p1, p2, p3, p4) -> Dictionary:
	var signal_name := ""
	var source: Object = null
	var target: Object = null
	var method_name := ""
	if p1 is String:
		signal_name = str(p1)
		source = p2 as Object
		method_name = str(p3)
	else:
		source = p1 as Object
		signal_name = str(p2)
		target = p3 as Object
		method_name = str(p4)
	if source == null or method_name.is_empty():
		return {
			"ok": false,
			"value": false,
			"message": "assert_connected requires a source object, a signal name and a method name",
		}
	var connected := false
	for connection in source.get_signal_connection_list(signal_name):
		var callable: Callable = connection["callable"]
		if callable.get_method() == method_name and (target == null or callable.get_object() == target):
			connected = true
			break
	var description := "Expected signal '%s' on %s to be %sconnected to method '%s'" % [
		signal_name,
		source,
		"" if connected == false else "NOT ",
		method_name,
	]
	return {"ok": true, "value": connected, "message": description}


func _object_not_watched_message(object: Object, signal_name: String) -> String:
	return (
		"Object %s is not being watched for signal '%s'. "
		+ "Call watch_signals(object) before the signal asserts."
	) % [object, signal_name]


func _gut_params_match(actual: Array, expected: Array) -> bool:
	if actual.size() != expected.size():
		return false
	for i in actual.size():
		if not _gut_param_equal(actual[i], expected[i]):
			return false
	return true


func _gut_param_equal(actual, expected) -> bool:
	if typeof(actual) in [TYPE_OBJECT, TYPE_ARRAY, TYPE_DICTIONARY] or typeof(expected) in [
				TYPE_OBJECT,
				TYPE_ARRAY,
				TYPE_DICTIONARY
	]:
		return actual == expected
	return str(actual) == str(expected) if typeof(actual) != typeof(expected) else actual == expected


## # Core assertions (GUT spellings) -----------------------------------------------

func assert_almost_ne(got, not_expected, error_interval, text: String = "") -> void:
	if is_nan(got) or is_nan(not_expected) or absf(got - not_expected) <= absf(error_interval):
		_gut_fail(
				"assert_almost_ne",
				_gut_detail(
						text,
						"Expected %s to NOT be within %s of %s" % [got, error_interval, not_expected]
				),
				got,
				not_expected
		)


func assert_not_between(got, expect_low, expect_high, text: String = "") -> void:
	if got >= expect_low and got <= expect_high:
		_gut_fail(
				"assert_not_between",
				_gut_detail(
						text,
						"Expected %s to NOT be between %s and %s (inclusive)"
								% [got, expect_low, expect_high]
				),
				got,
				"[%s, %s]" % [expect_low, expect_high]
		)


func assert_does_not_have(obj, element, text: String = "") -> void:
	if _gd_tools_membership(obj, element):
		_gut_fail(
				"assert_does_not_have",
				_gut_detail(text, "Expected %s to NOT contain %s" % [obj, element]),
				obj,
				element
		)


## GUT's `assert_is` checks the value against a class or built-in type. This
## intentionally shadows the native identity assertion: GUT's identity check is
## spelled `assert_same` here.
func assert_is(object, a_class, text: String = "") -> void:
	var matches := false
	if typeof(a_class) == TYPE_INT:
		matches = typeof(object) == int(a_class)
	elif typeof(a_class) == TYPE_OBJECT:
		matches = is_instance_of(object, a_class)
	if not matches:
		_gut_fail(
				"assert_is",
				_gut_detail(
						text,
						"Expected %s to be of type %s" % [object, a_class]
				),
				object,
				a_class
		)


func assert_same(v1, v2, text: String = "") -> void:
	if v1 != v2 or typeof(v1) != typeof(v2):
		_gut_fail(
				"assert_same",
				_gut_detail(text, "Expected %s to be the same instance as %s" % [v1, v2]),
				v1,
				v2
		)


func assert_not_same(v1, v2, text: String = "") -> void:
	if v1 == v2 and typeof(v1) == typeof(v2):
		_gut_fail(
				"assert_not_same",
				_gut_detail(text, "Expected %s to NOT be the same instance as %s" % [v1, v2]),
				v1,
				v2
		)


func assert_typeof(object, type: int, text: String = "") -> void:
	if typeof(object) != type:
		_gut_fail(
				"assert_typeof",
				_gut_detail(
						text,
						"Expected typeof %s to be %d, but got %d" % [object, type, typeof(object)]
				),
				typeof(object),
				type
		)


func assert_not_typeof(object, type: int, text: String = "") -> void:
	if typeof(object) == type:
		_gut_fail(
				"assert_not_typeof",
				_gut_detail(
						text,
						"Expected typeof %s to NOT be %d" % [object, type]
				),
				typeof(object),
				type
		)


func assert_eq_deep(v1, v2, text: String = "") -> void:
	if not _gut_deep_equal(v1, v2):
		_gut_fail(
				"assert_eq_deep",
				_gut_detail(text, "Expected %s to deeply equal %s" % [v1, v2]),
				v1,
				v2
		)


func assert_ne_deep(v1, v2, text: String = "") -> void:
	if _gut_deep_equal(v1, v2):
		_gut_fail(
				"assert_ne_deep",
				_gut_detail(text, "Expected %s to NOT deeply equal %s" % [v1, v2]),
				v1,
				v2
		)


func _gut_deep_equal(v1, v2) -> bool:
	if typeof(v1) == TYPE_ARRAY and typeof(v2) == TYPE_ARRAY:
		var left: Array = v1
		var right: Array = v2
		if left.size() != right.size():
			return false
		for i in left.size():
			if not _gut_deep_equal(left[i], right[i]):
				return false
		return true
	if typeof(v1) == TYPE_DICTIONARY and typeof(v2) == TYPE_DICTIONARY:
		var left: Dictionary = v1
		var right: Dictionary = v2
		if left.size() != right.size():
			return false
		for key in left:
			if not right.has(key) or not _gut_deep_equal(left[key], right[key]):
				return false
		return true
	return typeof(v1) == typeof(v2) and v1 == v2


func assert_string_contains(text: String, search: String, match_case: bool = true) -> void:
	var haystack := text
	var needle := search
	if not match_case:
		haystack = haystack.to_lower()
		needle = needle.to_lower()
	if not haystack.contains(needle):
		_gut_fail(
				"assert_string_contains",
				_gut_detail("", "Expected '%s' to contain '%s'" % [text, search]),
				text,
				search
		)


func assert_string_starts_with(text: String, search: String, match_case: bool = true) -> void:
	var haystack := text
	var needle := search
	if not match_case:
		haystack = haystack.to_lower()
		needle = needle.to_lower()
	if not haystack.begins_with(needle):
		_gut_fail(
				"assert_string_starts_with",
				_gut_detail("", "Expected '%s' to start with '%s'" % [text, search]),
				text,
				search
		)


func assert_string_ends_with(text: String, search: String, match_case: bool = true) -> void:
	var haystack := text
	var needle := search
	if not match_case:
		haystack = haystack.to_lower()
		needle = needle.to_lower()
	if not haystack.ends_with(needle):
		_gut_fail(
				"assert_string_ends_with",
				_gut_detail("", "Expected '%s' to end with '%s'" % [text, search]),
				text,
				search
		)


func assert_file_exists(file_path: String, text: String = "") -> void:
	if not FileAccess.file_exists(file_path):
		_gut_fail(
				"assert_file_exists",
				_gut_detail(text, "Expected file to exist: %s" % file_path)
		)


func assert_file_does_not_exist(file_path: String, text: String = "") -> void:
	if FileAccess.file_exists(file_path):
		_gut_fail(
				"assert_file_does_not_exist",
				_gut_detail(text, "Expected file to NOT exist: %s" % file_path)
		)


func assert_file_empty(file_path: String, text: String = "") -> void:
	if not FileAccess.file_exists(file_path):
		_gut_fail("assert_file_empty", _gut_detail(text, "File does not exist: %s" % file_path))
		return
	var file := FileAccess.open(file_path, FileAccess.READ)
	if file != null and file.get_length() > 0:
		_gut_fail(
				"assert_file_empty",
				_gut_detail(text, "Expected file to be empty: %s" % file_path)
		)


func assert_file_not_empty(file_path: String, text: String = "") -> void:
	if FileAccess.file_exists(file_path):
		var file := FileAccess.open(file_path, FileAccess.READ)
		if file != null and file.get_length() > 0:
			return
	_gut_fail(
			"assert_file_not_empty",
			_gut_detail(
					text,
					"Expected file to exist and not be empty: %s" % file_path
			)
	)


## # Async helpers -----------------------------------------------------------------

func wait_frames(frames: int, _msg: String = "") -> void:
	for i in frames:
		await get_tree().process_frame


func wait_idle_frames(frames: int, _msg: String = "") -> void:
	await wait_frames(frames)


func wait_process_frames(frames: int, _msg: String = "") -> void:
	await wait_frames(frames)


## Poll [param callable] every frame until it returns `true` or the time budget
## expires. Returns `true` when the callable became truthy in time.
func wait_until(callable: Callable, max_time: float, _p3 = "", _p4 = "") -> bool:
	var deadline := Time.get_ticks_msec() + int(max_time * 1000.0)
	while Time.get_ticks_msec() < deadline:
		if callable.call():
			return true
		await get_tree().process_frame
	return callable.call()


## Poll [param callable] every frame until it returns falsy or the budget
## expires. Returns `true` when the condition cleared in time.
func wait_while(callable: Callable, max_time: float, _p3 = "", _p4 = "") -> bool:
	var deadline := Time.get_ticks_msec() + int(max_time * 1000.0)
	while Time.get_ticks_msec() < deadline:
		if not callable.call():
			return true
		await get_tree().process_frame
	return not callable.call()


func yield_for(time: float, _msg: String = "") -> void:
	await wait_seconds(time)


func yield_to(obj: Object, signal_name, max_wait: float, _msg: String = "") -> bool:
	var target: Variant = signal_name
	if typeof(target) == TYPE_STRING:
		target = obj.get(str(signal_name))
		if typeof(target) != TYPE_SIGNAL:
			_gut_fail(
					"yield_to",
					"Object %s has no signal '%s'" % [obj, signal_name]
			)
			return false
	return await wait_for_signal(target, max_wait)


func yield_frames(frames: int, _msg: String = "") -> void:
	await wait_frames(frames)


## # Skipping ----------------------------------------------------------------------

func skip_if_godot_version_lt(expected: String, message: String = "") -> void:
	var expected_version := _gut_parse_version(expected)
	var engine_version := _gut_engine_version()
	if _gut_version_lt(engine_version, expected_version):
		skip_test(
				_gut_detail(
						message,
						"Skipped: requires Godot %s or newer (running %s)"
								% [expected, _gut_format_version(engine_version)]
				)
		)


func skip_if_godot_version_ne(expected: String, message: String = "") -> void:
	var expected_version := _gut_parse_version(expected)
	var engine_version := _gut_engine_version()
	if engine_version != expected_version:
		skip_test(
				_gut_detail(
						message,
						"Skipped: requires Godot %s (running %s)"
								% [expected, _gut_format_version(engine_version)]
				)
		)


func _gut_engine_version() -> Array:
	var info := Engine.get_version_info()
	return [int(info["major"]), int(info["minor"]), int(info["patch"])]


func _gut_parse_version(text: String) -> Array:
	var parts: Array = [0, 0, 0]
	var index := 0
	for component in text.split("."):
		if index >= parts.size():
			break
		var digits := ""
		for character in str(component):
			if character >= "0" and character <= "9":
				digits += character
			else:
				break
		if not digits.is_empty():
			parts[index] = int(digits)
		index += 1
	return parts


func _gut_version_lt(a: Array, b: Array) -> bool:
	for i in 3:
		if int(a[i]) != int(b[i]):
			return int(a[i]) < int(b[i])
	return false


func _gut_format_version(version: Array) -> String:
	return "%d.%d.%d" % [version[0], version[1], version[2]]


## # Failure plumbing ---------------------------------------------------------------

func _gut_detail(text: String, message: String) -> String:
	return message if text.is_empty() else "%s: %s" % [text, message]


func _gut_fail(
		assertion: String,
		message: String,
		actual = null,
		expected = null
) -> void:
	_gd_tools_record_failure(assertion, message, actual, expected)
