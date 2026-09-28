class_name GdToolsTest
extends Node

## Base class for gd-tools native GDScript tests.
##
## The runner owns lifecycle and process management. This class only provides
## the assertion surface and Godot-specific waits needed by a test suite.

signal _gd_tools_wait_resolved

var _gd_tools_failures: Array[Dictionary] = []
var _gd_tools_suite_state: Dictionary = {}
var _gd_tools_test_context: GdToolsTestContext = null
var _gd_tools_skipped := false
var _gd_tools_skip_reason := ""
var _gd_tools_wait_received := false
var _gd_tools_wait_signal = null
var _gd_tools_wait_timer: SceneTreeTimer = null
var _gd_tools_mock_methods: Dictionary = {}


func _gd_tools_record_failure(
		assertion: String,
		message: String = "",
		actual = null,
		expected = null
) -> void:
	## Record one structured assertion failure for the current test.
	##
	## Failures are discarded once the test has been skipped. The guard lives
	## here rather than in each assertion so that every assertion, present and
	## future, honours a skip without being modified.
	if _gd_tools_skipped:
		return
	var source := ""
	var line := 0
	var stack: Array[Dictionary] = get_stack()
	for frame in stack:
		var frame_source := str(frame.get("source", ""))
		if frame_source.ends_with("gd_tools_test.gd") or frame_source.ends_with(
				"gd_tools_gut_bridge.gd"
		) or frame_source.ends_with(
				"gd_tools_test_runner.gd"
		):
			continue
		source = frame_source
		line = int(frame.get("line", 0))
		break
	_gd_tools_failures.append({
		"assertion": assertion,
		"message": message,
		"actual": str(actual),
		"expected": str(expected),
		"source": source,
		"line": line,
	})


func get_failures() -> Array[Dictionary]:
	## Return a copy of failures recorded by the current test instance.
	return _gd_tools_failures.duplicate(true)


func clear_failures() -> void:
	## Clear per-test assertion state before reusing a test instance.
	_gd_tools_failures.clear()
	_gd_tools_skipped = false
	_gd_tools_skip_reason = ""


func _gd_tools_set_suite_state(state: Dictionary) -> void:
	## Share the suite-scoped state dictionary with a fresh test instance.
	_gd_tools_suite_state = state


func _gd_tools_get_suite_state() -> Dictionary:
	## Return the suite-scoped state dictionary.
	return _gd_tools_suite_state


func get_test_context() -> GdToolsTestContext:
	## Return the scene/resource context for the current test attempt.
	return _gd_tools_test_context


func _gd_tools_set_test_context(context: GdToolsTestContext) -> void:
	## Attach an integration context before lifecycle hooks execute.
	_gd_tools_test_context = context


func _gd_tools_clear_test_context() -> void:
	## Detach the completed attempt context before releasing its resources.
	if _gd_tools_test_context != null:
		_gd_tools_test_context.clear()
	_gd_tools_test_context = null


## Variant types whose instances answer a membership query. GDScript spells
## membership `has()` on these, except for String, which spells it
## `contains()`. Object values are handled separately by a `has_method` probe
## so a user's own container class is accepted without being listed here.
const _GD_TOOLS_MEMBERSHIP_TYPES := [
	TYPE_ARRAY,
	TYPE_DICTIONARY,
	TYPE_STRING,
	TYPE_PACKED_BYTE_ARRAY,
	TYPE_PACKED_INT32_ARRAY,
	TYPE_PACKED_INT64_ARRAY,
	TYPE_PACKED_FLOAT32_ARRAY,
	TYPE_PACKED_FLOAT64_ARRAY,
	TYPE_PACKED_STRING_ARRAY,
	TYPE_PACKED_VECTOR2_ARRAY,
	TYPE_PACKED_VECTOR3_ARRAY,
	TYPE_PACKED_COLOR_ARRAY,
]


func _gd_tools_is_numeric(value) -> bool:
	## Return whether a value can take part in a numeric comparison.
	return value is int or value is float


func _gd_tools_is_identity_bearing(value) -> bool:
	## Return whether this type can distinguish two separately created values
	## that compare equal, which is what makes reference identity meaningful.
	return value is Object or value is Array or value is Dictionary


func _gd_tools_can_check_membership(value) -> bool:
	## Return whether a value answers a membership query.
	if _GD_TOOLS_MEMBERSHIP_TYPES.has(typeof(value)):
		return true
	return value is Object and value.has_method("has")


func _gd_tools_element_fits(container, element) -> bool:
	## Return whether `element` is a type the container can be asked about.
	##
	## Every builtin answers membership with a TYPED parameter, so a mismatched
	## element raises inside `has()`/`contains()` rather than returning false.
	## That is a GDScript runtime error, which the runner captures and escalates
	## to exit 2 -- exactly the outcome spec R4 exists to prevent. Checking the
	## container alone was not enough: `assert_has("abc", 5)` passed the container
	## check and then raised `Invalid type in function 'contains' in base 'String'`.
	if container is String or container is PackedStringArray:
		return element is String or element is StringName
	if (
		container is PackedByteArray
		or container is PackedInt32Array
		or container is PackedInt64Array
	):
		return element is int
	if container is PackedFloat32Array or container is PackedFloat64Array:
		return element is int or element is float
	if container is PackedVector2Array:
		return element is Vector2
	if container is PackedVector3Array:
		return element is Vector3
	if container is PackedColorArray:
		return element is Color
	# Array and Dictionary accept any Variant, and a user container's own `has`
	# signature is the authority on what it will accept.
	return true


func _gd_tools_membership(container, element) -> bool:
	## Perform a membership query, bridging String's different spelling.
	if container is String:
		return container.contains(element)
	return container.has(element)


func _gd_tools_detail(message: String, detail: String) -> String:
	## Combine a caller-supplied message with assertion-specific detail.
	return detail if message.is_empty() else "%s: %s" % [message, detail]


func _gd_tools_record_type_failure(
		assertion: String,
		expectation: String,
		value,
		position: int,
		hint: String = ""
) -> void:
	## Record a failure for a wrongly typed argument instead of raising.
	##
	## Spec R4: a GDScript runtime error here would be captured by the runner
	## and escalate the entire run to exit 2, turning one bad call in one test
	## into a run-level environment failure. Naming the type is actionable.
	var message := "%s expects %s at argument %d, got %s" % [
		assertion, expectation, position, type_string(typeof(value))
	]
	if not hint.is_empty():
		message += ". " + hint
	_gd_tools_record_failure(assertion, message, value, expectation)


func assert_gt(actual, expected, message: String = "") -> void:
	## Assert that a value is strictly greater than another.
	if not _gd_tools_is_numeric(actual):
		_gd_tools_record_type_failure("assert_gt", "a number", actual, 1)
		return
	if not _gd_tools_is_numeric(expected):
		_gd_tools_record_type_failure("assert_gt", "a number", expected, 2)
		return
	if actual <= expected:
		_gd_tools_record_failure("assert_gt", message, actual, expected)


func assert_gte(actual, expected, message: String = "") -> void:
	## Assert that a value is greater than or equal to another.
	if not _gd_tools_is_numeric(actual):
		_gd_tools_record_type_failure("assert_gte", "a number", actual, 1)
		return
	if not _gd_tools_is_numeric(expected):
		_gd_tools_record_type_failure("assert_gte", "a number", expected, 2)
		return
	if actual < expected:
		_gd_tools_record_failure("assert_gte", message, actual, expected)


func assert_lt(actual, expected, message: String = "") -> void:
	## Assert that a value is strictly less than another.
	if not _gd_tools_is_numeric(actual):
		_gd_tools_record_type_failure("assert_lt", "a number", actual, 1)
		return
	if not _gd_tools_is_numeric(expected):
		_gd_tools_record_type_failure("assert_lt", "a number", expected, 2)
		return
	if actual >= expected:
		_gd_tools_record_failure("assert_lt", message, actual, expected)


func assert_lte(actual, expected, message: String = "") -> void:
	## Assert that a value is less than or equal to another.
	if not _gd_tools_is_numeric(actual):
		_gd_tools_record_type_failure("assert_lte", "a number", actual, 1)
		return
	if not _gd_tools_is_numeric(expected):
		_gd_tools_record_type_failure("assert_lte", "a number", expected, 2)
		return
	if actual > expected:
		_gd_tools_record_failure("assert_lte", message, actual, expected)


func assert_between(value, lower, upper, message: String = "") -> void:
	## Assert that a value falls within a range. BOTH bounds are INCLUSIVE.
	##
	## Inclusive is deliberate: a test ported from GUT must not change meaning
	## on the way across. Do not "fix" this to be exclusive.
	if not _gd_tools_is_numeric(value):
		_gd_tools_record_type_failure("assert_between", "a number", value, 1)
		return
	if not _gd_tools_is_numeric(lower):
		_gd_tools_record_type_failure("assert_between", "a number", lower, 2)
		return
	if not _gd_tools_is_numeric(upper):
		_gd_tools_record_type_failure("assert_between", "a number", upper, 3)
		return
	if value < lower:
		_gd_tools_record_failure(
			"assert_between",
			_gd_tools_detail(
				message, "value %s is below the lower bound %s" % [value, lower]
			),
			value,
			lower
		)
	elif value > upper:
		_gd_tools_record_failure(
			"assert_between",
			_gd_tools_detail(
				message, "value %s is above the upper bound %s" % [value, upper]
			),
			value,
			upper
		)


func assert_almost_eq(actual, expected, max_delta, message: String = "") -> void:
	## Assert that two numbers differ by no more than `max_delta`.
	if not _gd_tools_is_numeric(actual):
		_gd_tools_record_type_failure("assert_almost_eq", "a number", actual, 1)
		return
	if not _gd_tools_is_numeric(expected):
		_gd_tools_record_type_failure("assert_almost_eq", "a number", expected, 2)
		return
	if not _gd_tools_is_numeric(max_delta):
		_gd_tools_record_type_failure("assert_almost_eq", "a number", max_delta, 3)
		return
	var delta: float = absf(float(actual) - float(expected))
	if delta > max_delta:
		_gd_tools_record_failure(
			"assert_almost_eq",
			_gd_tools_detail(
				message, "difference %s exceeds the allowance %s" % [delta, max_delta]
			),
			actual,
			expected
		)


func assert_has(container, element, message: String = "") -> void:
	## Assert that a container holds an element.
	if not _gd_tools_can_check_membership(container):
		_gd_tools_record_type_failure("assert_has", "a container", container, 1)
		return
	if not _gd_tools_element_fits(container, element):
		_gd_tools_record_type_failure(
			"assert_has", "an element the container can hold", element, 2
		)
		return
	if not _gd_tools_membership(container, element):
		_gd_tools_record_failure(
			"assert_has",
			_gd_tools_detail(
				message,
				"%s does not contain %s" % [type_string(typeof(container)), element]
			),
			container,
			element
		)


func assert_in(element, container, message: String = "") -> void:
	## Assert that an element is present in a container.
	##
	## Note the INVERTED argument order relative to `assert_has`. GUT spells it
	## this way and a migrated test must not silently swap subject and object.
	if not _gd_tools_can_check_membership(container):
		_gd_tools_record_type_failure("assert_in", "a container", container, 2)
		return
	if not _gd_tools_element_fits(container, element):
		_gd_tools_record_type_failure(
			"assert_in", "an element the container can hold", element, 1
		)
		return
	if not _gd_tools_membership(container, element):
		_gd_tools_record_failure(
			"assert_in",
			_gd_tools_detail(
				message,
				"%s does not contain %s" % [type_string(typeof(container)), element]
			),
			container,
			element
		)


func assert_has_method(object, method, message: String = "") -> void:
	## Assert that an object exposes a named method.
	if not (object is Object):
		_gd_tools_record_type_failure("assert_has_method", "an Object", object, 1)
		return
	if not (method is String or method is StringName):
		_gd_tools_record_type_failure("assert_has_method", "a method name", method, 2)
		return
	if not object.has_method(method):
		_gd_tools_record_failure(
			"assert_has_method",
			_gd_tools_detail(
				message, "%s has no method %s" % [object.get_class(), method]
			),
			object,
			method
		)


func assert_is(actual, expected, message: String = "") -> void:
	## Assert that two values are the SAME instance, not merely equal.
	if not _gd_tools_is_identity_bearing(actual):
		_gd_tools_record_type_failure(
			"assert_is",
			"a value carrying reference identity",
			actual,
			1,
			"Use assert_eq to compare values."
		)
		return
	if not _gd_tools_is_identity_bearing(expected):
		_gd_tools_record_type_failure(
			"assert_is",
			"a value carrying reference identity",
			expected,
			2,
			"Use assert_eq to compare values."
		)
		return
	if not is_same(actual, expected):
		_gd_tools_record_failure(
			"assert_is",
			_gd_tools_detail(
				message, "distinct instances of %s" % type_string(typeof(actual))
			),
			actual,
			expected
		)


func assert_true(value: bool, message: String = "") -> void:
	## Assert that a boolean value is true.
	if not value:
		_gd_tools_record_failure("assert_true", message, value, true)


func assert_false(value: bool, message: String = "") -> void:
	## Assert that a boolean value is false.
	if value:
		_gd_tools_record_failure("assert_false", message, value, false)


func assert_eq(actual, expected, message: String = "") -> void:
	## Assert that two values are equal.
	if actual != expected:
		_gd_tools_record_failure("assert_eq", message, actual, expected)


func assert_ne(actual, expected, message: String = "") -> void:
	## Assert that two values are different.
	if actual == expected:
		_gd_tools_record_failure("assert_ne", message, actual, expected)


func assert_null(value, message: String = "") -> void:
	## Assert that a value is null.
	if value != null:
		_gd_tools_record_failure("assert_null", message, value, null)


func assert_not_null(value, message: String = "") -> void:
	## Assert that a value is not null.
	if value == null:
		_gd_tools_record_failure("assert_not_null", message, value, "not null")


## Return a full test double of a GDScript script.
##
## Every doublable script method is redeclared on the generated double as an
## untyped override. Unstubbed double methods return null and never run the
## real implementation (GUT semantics). Accepts a preloaded Script or a
## resource path string; an unusable target fails the test immediately.
func double(target: Variant) -> Object:
	return _gd_tools_make_double(target, false)


## Return a partial test double of a GDScript script.
##
## Identical to [method double] except that unstubbed methods forward to the
## real implementation via super(), preserving real behaviour except where a
## later stub overrides it.
func partial_double(target: Variant) -> Object:
	return _gd_tools_make_double(target, true)


func _gd_tools_make_double(target: Variant, is_partial: bool) -> Object:
	var target_script := _gd_tools_resolve_mock_script(target)
	if target_script == null:
		fail(
				"double() and partial_double() require a GDScript script"
				+ " or a script resource path"
		)
		return null
	var methods := _gd_tools_mock_methods_for(target_script)
	var source := GdToolsMock.Doubler.generate(
			target_script, get_instance_id(), is_partial, methods
	)
	var generated := GDScript.new()
	generated.source_code = source
	var reload_error := generated.reload()
	if reload_error != OK or not generated.can_instantiate():
		fail(
				"Unable to generate a double of '%s': the generated script"
				+ " did not load" % target_script.resource_path
		)
		return null
	return generated.new()


func _gd_tools_resolve_mock_script(target: Variant) -> Script:
	if target is Script:
		return target
	if target is String:
		return load(str(target)) as Script
	return null


func _gd_tools_mock_methods_for(target_script: Script) -> Array:
	var path := target_script.resource_path
	if not _gd_tools_mock_methods.has(path):
		_gd_tools_mock_methods[path] = (
			GdToolsMock.Doubler.collect_methods(target_script)
		)
	return _gd_tools_mock_methods[path]


func _gd_tools_mock_return_meta(script_path: String, method: String) -> Dictionary:
	var methods: Array = _gd_tools_mock_methods.get(script_path, [])
	for meta in methods:
		if str(meta.get("name", "")) == method:
			return meta.get("return", {})
	return {}


func _gd_tools_mock_default(
		script_path: String,
		method: String,
		index: int
) -> Variant:
	var methods: Array = _gd_tools_mock_methods.get(script_path, [])
	for meta in methods:
		if str(meta.get("name", "")) != method:
			continue
		var default_args: Array = meta.get("default_args", [])
		var argument_count: int = meta.get("args", []).size()
		var first_default := argument_count - default_args.size()
		if index >= first_default and index - first_default < default_args.size():
			return default_args[index - first_default]
		return null
	return null


func fail(message: String = "Test failed") -> void:
	## Record an unconditional test failure.
	_gd_tools_record_failure("fail", message)


func skip_test(reason: String = "") -> void:
	## Skip the current test.
	##
	## The runner reports the test as `skipped` rather than `passed`. Any
	## assertion recorded after this call is discarded, so an early guard is
	## safe mid-test:
	##
	##     if not client.is_connected():
	##         skip_test("no socket in headless")
	##
	## A failure recorded *before* the skip still fails the test: a skip never
	## masks a real failure.
	_gd_tools_skipped = true
	_gd_tools_skip_reason = "Test skipped." if reason.is_empty() else reason


func pending_test(reason: String = "") -> void:
	## Skip the current test. Alias for `skip_test`, matching the GUT spelling.
	skip_test(reason)


func is_skipped() -> bool:
	## Return whether this test called `skip_test` or `pending_test`.
	return _gd_tools_skipped


func get_skip_reason() -> String:
	## Return the reason given to `skip_test`. Never empty.
	return _gd_tools_skip_reason


func wait_process_frame() -> void:
	## Wait for one process frame.
	await get_tree().process_frame


func wait_physics_frames(frame_count: int = 1) -> void:
	## Wait for one or more physics frames.
	for _frame in range(max(frame_count, 0)):
		await get_tree().physics_frame


func wait_seconds(seconds: float) -> void:
	## Wait for a scene-tree timer.
	await get_tree().create_timer(seconds).timeout


func wait_for_signal(
		target_signal: Signal,
		timeout_seconds: float = 5.0
	) -> bool:
	## Wait for a signal with a bounded timeout; return whether it was emitted.
	##
	##     if not wait_for_signal(door.door_opened, 1.0):
	##         fail("door never opened")
	##
	## Returns the moment the signal fires rather than when the budget runs
	## out, so a generous budget does not become a mandatory wait. The default
	## budget matches the runner's per-test default, so an unbounded wait that
	## would hang now surfaces as a `false` instead of a test timeout.
	##
	## Records no failure of its own: whether a missed signal is a defect is the
	## test's call to make. That is what distinguishes it from
	## `GdToolsTestContext.wait_for_signal`, which is scoped to an integration
	## context and records the miss for you.
	_gd_tools_wait_received = false
	_gd_tools_wait_signal = target_signal
	_gd_tools_wait_signal.connect(_gd_tools_on_wait_signal, CONNECT_ONE_SHOT)
	_gd_tools_wait_timer = get_tree().create_timer(max(timeout_seconds, 0.001))
	_gd_tools_wait_timer.timeout.connect(
			_gd_tools_wait_resolved.emit,
			CONNECT_ONE_SHOT
	)
	await _gd_tools_wait_resolved
	var received := _gd_tools_wait_received
	_gd_tools_disconnect_wait()
	return received


func _gd_tools_on_wait_signal() -> void:
	_gd_tools_wait_received = true
	_gd_tools_wait_resolved.emit()


func _gd_tools_disconnect_wait() -> void:
	## Drop whichever side of the race did not win, so a later wait in the same
	## test is not resolved by this one's leftover timer.
	if _gd_tools_wait_signal != null and _gd_tools_wait_signal.is_connected(
			_gd_tools_on_wait_signal
	):
		_gd_tools_wait_signal.disconnect(_gd_tools_on_wait_signal)
	if _gd_tools_wait_timer != null and _gd_tools_wait_timer.timeout.is_connected(
			_gd_tools_wait_resolved.emit
	):
		_gd_tools_wait_timer.timeout.disconnect(_gd_tools_wait_resolved.emit)
	_gd_tools_wait_signal = null
	_gd_tools_wait_timer = null
