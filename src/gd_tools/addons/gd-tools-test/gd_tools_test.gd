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
var _gd_tools_stub_registry: Dictionary = {}
var _gd_tools_signal_watchers: Dictionary = {}
var _gd_tools_case_index := 0
var _gd_tools_parameter_names: Array = []
var _gd_tools_parameter_values: Array = []
var _gd_tools_snapshot_suite_name := ""
var _gd_tools_snapshot_test_name := ""
var _gd_tools_snapshot_call_count := 0
var _gd_tools_snapshots_written: Array[String] = []

const _GD_TOOLS_SNAPSHOT_SERIALIZER := preload(
	"res://addons/gd-tools-test/gd_tools_snapshot_serializer.gd"
)
const _GD_TOOLS_SNAPSHOT_STORE := preload(
	"res://addons/gd-tools-test/gd_tools_snapshot_store.gd"
)
const _GD_TOOLS_SNAPSHOT_DEFAULT_BASE := "res://.gd-tools/snapshots"


func _gd_tools_record_failure(
	assertion: String, message: String = "", actual = null, expected = null
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
		if (
			frame_source.ends_with("gd_tools_test.gd")
			or frame_source.ends_with("gd_tools_test_runner.gd")
		):
			continue
		source = frame_source
		line = int(frame.get("line", 0))
		break
	(
		_gd_tools_failures
		. append(
			{
				"assertion": assertion,
				"message": message,
				"actual": str(actual),
				"expected": str(expected),
				"source": source,
				"line": line,
			}
		)
	)


func get_failures() -> Array[Dictionary]:
	## Return a copy of failures recorded by the current test instance.
	return _gd_tools_failures.duplicate(true)


func clear_failures() -> void:
	## Clear per-test assertion state before reusing a test instance.
	_gd_tools_failures.clear()
	_gd_tools_skipped = false
	_gd_tools_skip_reason = ""
	_gd_tools_reset_signal_watch()


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
	assertion: String, expectation: String, value, position: int, hint: String = ""
) -> void:
	## Record a failure for a wrongly typed argument instead of raising.
	##
	## Spec R4: a GDScript runtime error here would be captured by the runner
	## and escalate the entire run to exit 2, turning one bad call in one test
	## into a run-level environment failure. Naming the type is actionable.
	var message := (
		"%s expects %s at argument %d, got %s"
		% [assertion, expectation, position, type_string(typeof(value))]
	)
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
			_gd_tools_detail(message, "value %s is below the lower bound %s" % [value, lower]),
			value,
			lower
		)
	elif value > upper:
		_gd_tools_record_failure(
			"assert_between",
			_gd_tools_detail(message, "value %s is above the upper bound %s" % [value, upper]),
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
		_gd_tools_record_type_failure("assert_has", "an element the container can hold", element, 2)
		return
	if not _gd_tools_membership(container, element):
		_gd_tools_record_failure(
			"assert_has",
			_gd_tools_detail(
				message, "%s does not contain %s" % [type_string(typeof(container)), element]
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
		_gd_tools_record_type_failure("assert_in", "an element the container can hold", element, 1)
		return
	if not _gd_tools_membership(container, element):
		_gd_tools_record_failure(
			"assert_in",
			_gd_tools_detail(
				message, "%s does not contain %s" % [type_string(typeof(container)), element]
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
			_gd_tools_detail(message, "%s has no method %s" % [object.get_class(), method]),
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
			_gd_tools_detail(message, "distinct instances of %s" % type_string(typeof(actual))),
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
			(
				"double() and partial_double() require a GDScript script"
				+ " or a script resource path; got: %s" % [target]
			)
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
			(
				"Unable to generate a double of '%s': the generated script"
				+ " did not load" % target_script.resource_path
			)
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
		_gd_tools_mock_methods[path] = (GdToolsMock.Doubler.collect_methods(target_script))
	return _gd_tools_mock_methods[path]


func _gd_tools_mock_return_meta(script_path: String, method: String) -> Dictionary:
	var methods: Array = _gd_tools_mock_methods.get(script_path, [])
	for meta in methods:
		if str(meta.get("name", "")) == method:
			return meta.get("return", {})
	return {}


## Start a stub registration on a double.
##
## [param target] must be a double created by [method double] or
## [method partial_double]. The returned builder must be completed with
## [method GdToolsMock.StubBuilder.to_return] or
## [method GdToolsMock.StubBuilder.to_call_super]. When [param args] is
## given, only calls whose arguments match it element-wise are affected,
## with the string `"any"` acting as a wildcard per element; a stub
## registered without arguments is the default fallback for every other
## call. Exact-argument stubs take precedence over wildcard stubs, which
## take precedence over the default fallback; within one tier the most
## recently registered stub wins. Stubs are stored per double instance on
## the test instance, so they never leak into other tests or doubles.
func stub(target: Object, method: String, args: Array = []) -> GdToolsMock.StubBuilder:
	## Create a stub builder for one method of a double.
	##
	## Fails the test immediately when the target is not a double or has no
	## such method, so a typo surfaces at setup time instead of silently
	## registering a stub that can never match.
	var mock: Object = target.get("__gd_tools")
	if mock == null:
		fail(
			(
				"stub() requires a double created by double()"
				+ " or partial_double(); got: %s" % [target]
			)
		)
		return _gd_tools_disabled_stub_builder()
	var script_path := str(mock.get("_script_path"))
	var method_names := []
	var target_script := load(script_path) as Script
	if target_script != null:
		for meta in _gd_tools_mock_methods_for(target_script):
			method_names.append(str(meta.get("name", "")))
	if not method in method_names:
		fail('stub() cannot stub "%s": %s has no such method' % [method, script_path])
		return _gd_tools_disabled_stub_builder()
	return GdToolsMock.StubBuilder.new(self, target.get_instance_id(), method, args)


func _gd_tools_disabled_stub_builder() -> GdToolsMock.StubBuilder:
	## A no-op builder handed out after a fail-fast stub() error.
	return GdToolsMock.StubBuilder.new(self, 0, "", [], true)


func _gd_tools_stub_register(
	double_id: int, method: String, args: Array, action: String, value: Variant
) -> void:
	var per_double: Dictionary = _gd_tools_stub_registry.get(double_id, {})
	var entries: Array = per_double.get(method, [])
	(
		entries
		. append(
			{
				"args": args.duplicate(),
				"action": action,
				"value": value,
				# Sequence position for `return_seq` stubs; unused otherwise.
				"position": 0,
			}
		)
	)
	per_double[method] = entries
	_gd_tools_stub_registry[double_id] = per_double


static func _gd_tools_stub_specificity(pattern: Array, call_args: Array) -> int:
	## Rank how specifically a stub pattern matches a call.
	##
	## Returns 2 for an exact match, 1 for a match involving "any"
	## wildcards, 0 for the default (empty) pattern, and -1 for no match.
	if pattern.is_empty():
		return 0
	if pattern.size() != call_args.size():
		return -1
	var wildcard := false
	for index in range(pattern.size()):
		var element = pattern[index]
		if element is String and str(element) == "any":
			wildcard = true
			continue
		if element != call_args[index]:
			return -1
	return 1 if wildcard else 2


static func _gd_tools_args_match(pattern: Array, call_args: Array) -> bool:
	## Return whether an argument pattern matches a recorded call.
	##
	## Elements equal to the string "any" act as per-element wildcards,
	## matching any value; every other element must compare equal. The
	## pattern must have the same size as the recorded call. This helper
	## is the single source of truth for argument matching, shared by
	## stub dispatch and spy assertions.
	return _gd_tools_stub_specificity(pattern, call_args) >= 0


## Maximum number of recorded calls listed in spy assertion failure
## diagnostics. Beyond this, a summary line reports the omitted calls so
## failure output stays readable.
const _GD_TOOLS_CALL_LISTING_LIMIT := 8


func _gd_tools_calls_listing(method: String, calls: Array) -> String:
	## Render a bounded, indexed listing of recorded calls for diagnostics.
	var lines: Array[String] = ['Recorded calls for "%s":' % method]
	var shown := mini(calls.size(), _GD_TOOLS_CALL_LISTING_LIMIT)
	for index in range(shown):
		lines.append("  call %d: %s" % [index, calls[index]])
	if calls.size() > shown:
		lines.append("  ... and %d more call(s)" % (calls.size() - shown))
	return "\n".join(lines)


func _gd_tools_args_diff(expected_args: Array, actual_args: Array) -> String:
	## Render a per-argument expected-vs-actual diff for a failed match.
	##
	## Only concrete mismatched positions are listed; "any" wildcard
	## positions never mismatch and are skipped.
	var lines: Array[String] = []
	var shared := mini(expected_args.size(), actual_args.size())
	for index in range(shared):
		var expected = expected_args[index]
		if expected is String and str(expected) == "any":
			continue
		var actual = actual_args[index]
		if expected != actual:
			lines.append(
				"  argument %d: expected %s, but was %s" % [index, expected, actual]
			)
	return "\n".join(lines)


func _gd_tools_stub_find(double_id: int, method: String, call_args: Array) -> Dictionary:
	var per_double: Dictionary = _gd_tools_stub_registry.get(double_id, {})
	var entries: Array = per_double.get(method, [])
	var best: Dictionary = {}
	var best_tier := -1
	for entry in entries:
		var tier := _gd_tools_stub_specificity(entry["args"], call_args)
		if tier > best_tier:
			best_tier = tier
			best = entry
		elif tier == best_tier and tier >= 0:
			best = entry
	return best


func _gd_tools_mock_default(script_path: String, method: String, index: int) -> Variant:
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


func assert_called(target: Object, method: String, message: String = "") -> void:
	## Assert that a double recorded at least one call to `method`.
	if _gd_tools_assert_target_is_double(target, "assert_called"):
		return
	var calls: Array = _gd_tools_double_calls(target, method)
	if calls.is_empty():
		_gd_tools_record_failure(
			"assert_called",
			_gd_tools_detail(
				message,
				'Expected "%s" to have been called at least once, but it was never called.' % method
			),
			0,
			"at least 1"
		)


func assert_not_called(target: Object, method: String, message: String = "") -> void:
	## Assert that a double recorded no calls to `method`.
	if _gd_tools_assert_target_is_double(target, "assert_not_called"):
		return
	var calls: Array = _gd_tools_double_calls(target, method)
	if not calls.is_empty():
		_gd_tools_record_failure(
			"assert_not_called",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have never been called, but it was called %d time(s).'
					% [method, calls.size()]
				)
				+ "\n" + _gd_tools_calls_listing(method, calls)
			),
			calls.size(),
			0
		)


func assert_call_count(target: Object, method: String, count: int, message: String = "") -> void:
	## Assert that a double recorded exactly `count` calls to `method`.
	if _gd_tools_assert_target_is_double(target, "assert_call_count"):
		return
	var calls: Array = _gd_tools_double_calls(target, method)
	var actual := calls.size()
	if actual != count:
		_gd_tools_record_failure(
			"assert_call_count",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have been called %d time(s), but it was called %d time(s).'
					% [method, count, actual]
				)
				+ "\n" + _gd_tools_calls_listing(method, calls)
			),
			actual,
			count
		)


func assert_call_arguments(
	target: Object, method: String, expected_args: Array, call_index: int = -1, message: String = ""
) -> void:
	## Assert the arguments of one recorded call on a double.
	##
	## `call_index` selects the recorded call (0 is the first); -1, the
	## default, selects the most recent call. Elements of `expected_args`
	## equal to the string "any" act as per-element wildcards, matching
	## any recorded value, mirroring `stub()` argument patterns.
	if _gd_tools_assert_target_is_double(target, "assert_call_arguments"):
		return
	var calls: Array = _gd_tools_double_calls(target, method)
	if call_index < 0:
		call_index = calls.size() + call_index
	if call_index < 0 or call_index >= calls.size():
		_gd_tools_record_failure(
			"assert_call_arguments",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" call %d to exist, but only %d call(s) were recorded.'
					% [method, call_index, calls.size()]
				)
			),
			calls.size(),
			call_index + 1
		)
		return
	var actual_args: Array = calls[call_index]
	if not _gd_tools_args_match(expected_args, actual_args):
		_gd_tools_record_failure(
			"assert_call_arguments",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" call %d arguments %s, but was %s.'
					% [method, call_index, expected_args, actual_args]
				)
				+ "\n" + _gd_tools_args_diff(expected_args, actual_args)
			),
			actual_args,
			expected_args
		)


func assert_property_is(
	target: Object, property: String, expected: Variant, message: String = ""
) -> void:
	## Assert that `target` currently holds `expected` in `property`.
	##
	## Works on any Object, including doubles and real instances: the value
	## is read via `get()` after the code under test ran. There is no
	## property-access interception in GDScript (declared members bypass
	## `_get`/`_set`), so this asserts values rather than access events.
	if not property in target:
		_gd_tools_record_failure(
			"assert_property_is",
			_gd_tools_detail(
				message,
				'Expected property "%s" to exist, but the object has no such property.'
				% property
			),
			null,
			expected
		)
		return
	var actual: Variant = target.get(property)
	if actual != expected:
		_gd_tools_record_failure(
			"assert_property_is",
			_gd_tools_detail(
				message,
				'Expected property "%s" to be %s, but was %s.'
				% [property, str(expected), str(actual)]
			),
			actual,
			expected
		)


func assert_call_order(target: Object, methods: Array, message: String = "") -> void:
	## Assert that a double's calls happened in the expected relative order.
	##
	## The check is subsequence-based: every listed method must appear in the
	## recorder in the given order, while calls to methods that are not
	## listed are ignored. Repeated methods are consumed first-match. On
	## failure the message shows the actual recorded order (bounded).
	if _gd_tools_assert_target_is_double(target, "assert_call_order"):
		return
	var mock: Object = target.get("__gd_tools")
	var recorded: Array = []
	for call in mock.get("calls"):
		recorded.append(str(call.get("method", "")))
	var expected: Array = []
	for method in methods:
		expected.append(str(method))
	var cursor := 0
	for check in expected:
		var found := false
		while cursor < recorded.size():
			if recorded[cursor] == check:
				found = true
				cursor += 1
				break
			cursor += 1
		if not found:
			var detail: String
			if not recorded.has(check):
				detail = (
					'Expected calls in order %s, but "%s" was never called; the actual order was %s.'
					% [expected, check, _gd_tools_order_listing(recorded)]
				)
			else:
				detail = (
					"Expected calls in order %s, but the actual order was %s."
					% [expected, _gd_tools_order_listing(recorded)]
				)
			_gd_tools_record_failure(
				"assert_call_order", _gd_tools_detail(message, detail), expected, recorded
			)
			return


func _gd_tools_order_listing(recorded: Array) -> String:
	## Render the recorded method order for failure diagnostics, capped so
	## long streams stay readable.
	if recorded.size() <= _GD_TOOLS_CALL_LISTING_LIMIT:
		return str(recorded)
	var shown: Array = recorded.slice(0, _GD_TOOLS_CALL_LISTING_LIMIT)
	return "%s ... and %d more call(s)" % [
		str(shown), recorded.size() - _GD_TOOLS_CALL_LISTING_LIMIT
	]


func _gd_tools_assert_target_is_double(target: Object, assertion: String) -> bool:
	## Record a failure and return true when `target` is not a double.
	if target != null and target.get("__gd_tools") != null:
		return false
	_gd_tools_record_failure(
		assertion,
		(
			"%s() requires a double created by double() or partial_double(); got: %s"
			% [assertion, target]
		)
	)
	return true


## Maximum number of signal arguments a watched emission can capture per
## signal. Signals declaring more arguments than this are not captured;
## assertions against them will report no emissions.
const _GD_TOOLS_SIGNAL_ARG_SLOTS := 10


func watch_signals(target: Object) -> void:
	## Start recording every signal emission of `target` for this test.
	##
	## Recordings are scoped to the current test: watchers disconnect
	## automatically at test end and never leak into other tests. Any Object
	## can be watched, including doubles. Assertions on an unwatched object
	## fail with guidance instead of silently passing. Note that watching
	## keeps a reference to `target` until test end, extending the lifetime
	## of RefCounted objects.
	if target == null or not is_instance_valid(target):
		_gd_tools_record_failure(
			"watch_signals",
			"watch_signals() requires an Object to watch; got: %s" % [target]
		)
		return
	var target_id := target.get_instance_id()
	if _gd_tools_signal_watchers.has(target_id):
		return
	var connections: Dictionary = {}
	for signal_info in target.get_signal_list():
		var signal_name := str(signal_info.get("name", ""))
		var arg_count: int = signal_info.get("args").size()
		if arg_count > _GD_TOOLS_SIGNAL_ARG_SLOTS:
			continue
		var callable := (
			Callable(self, "_gd_tools_on_watched_emission_%d" % arg_count)
			. bind(target_id, signal_name)
		)
		if target.connect(signal_name, callable) != OK:
			continue
		connections[signal_name] = callable
	_gd_tools_signal_watchers[target_id] = {
		"object": target,
		"connections": connections,
		"emissions": [],
	}


func assert_signal_emitted(target: Object, signal_name: String, message: String = "") -> void:
	## Assert that a watched object emitted `signal_name` at least once.
	if _gd_tools_assert_target_is_watched(target, "assert_signal_emitted"):
		return
	if _gd_tools_signal_emissions(target, signal_name).is_empty():
		_gd_tools_record_failure(
			"assert_signal_emitted",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have been emitted at least once, but no emission was captured.'
					% signal_name
				)
			),
			0,
			"at least 1"
		)


func assert_signal_not_emitted(target: Object, signal_name: String, message: String = "") -> void:
	## Assert that a watched object emitted `signal_name` never.
	if _gd_tools_assert_target_is_watched(target, "assert_signal_not_emitted"):
		return
	var count := _gd_tools_signal_emissions(target, signal_name).size()
	if count > 0:
		_gd_tools_record_failure(
			"assert_signal_not_emitted",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have never been emitted, but it was emitted %d time(s).'
					% [signal_name, count]
				)
			),
			count,
			0
		)


func assert_signal_emit_count(
	target: Object, signal_name: String, count: int, message: String = ""
) -> void:
	## Assert that a watched object emitted `signal_name` exactly `count` times.
	if _gd_tools_assert_target_is_watched(target, "assert_signal_emit_count"):
		return
	var actual := _gd_tools_signal_emissions(target, signal_name).size()
	if actual != count:
		_gd_tools_record_failure(
			"assert_signal_emit_count",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have been emitted %d time(s), but it was emitted %d time(s).'
					% [signal_name, count, actual]
				)
			),
			actual,
			count
		)


func assert_signal_emitted_with_args(
	target: Object, signal_name: String, expected_args: Array, message: String = ""
) -> void:
	## Assert that a watched object emitted `signal_name` with matching args.
	##
	## Any-match semantics: passes when at least ONE captured emission
	## matches element-wise. The string `"any"` acts as a per-element
	## wildcard, mirroring the stub system's argument convention.
	if _gd_tools_assert_target_is_watched(
		target, "assert_signal_emitted_with_args"
	):
		return
	var emissions := _gd_tools_signal_emissions(target, signal_name)
	for emission in emissions:
		if _gd_tools_stub_specificity(expected_args, emission["args"]) >= 0:
			return
	if emissions.is_empty():
		_gd_tools_record_failure(
			"assert_signal_emitted_with_args",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have been emitted with arguments %s, but no emission was captured.'
					% [signal_name, expected_args]
				)
			),
			_gd_tools_format_emissions(emissions),
			expected_args
		)
	else:
		_gd_tools_record_failure(
			"assert_signal_emitted_with_args",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to have been emitted with arguments %s, but none of the %d captured emission(s) matched: %s'
					% [
						signal_name,
						expected_args,
						emissions.size(),
						_gd_tools_format_emissions(emissions),
					]
				)
			),
			_gd_tools_format_emissions(emissions),
			expected_args
		)


func assert_signal_emitted_after(
	target_signal: Signal, timeout_seconds: float = 5.0, message: String = ""
) -> void:
	## Await one emission of `target_signal`, asserting it arrives in time.
	##
	## Unlike the watched-object assertions this takes the signal itself,
	## so no watch_signals() setup is required. `wait_for_signal`'s
	## `-> bool` contract is untouched.
	var fired: bool = await wait_for_signal(target_signal, timeout_seconds)
	if not fired:
		_gd_tools_record_failure(
			"assert_signal_emitted_after",
			_gd_tools_detail(
				message,
				(
					'Expected "%s" to be emitted within %s seconds, but the wait timed out.'
					% [target_signal.get_name(), timeout_seconds]
				)
			),
			"timed out",
			"emitted within %s seconds" % timeout_seconds
		)


func _gd_tools_assert_target_is_watched(target: Object, assertion: String) -> bool:
	## Record a guidance failure and return true when `target` is unwatched.
	if (
		target != null
		and is_instance_valid(target)
		and _gd_tools_signal_watchers.has(target.get_instance_id())
	):
		return false
	_gd_tools_record_failure(
		assertion,
		(
			"%s() requires an object registered with watch_signals();"
			+ " object not watched - call watch_signals(%s) first"
			% [assertion, target]
		)
	)
	return true


func _gd_tools_signal_emissions(target: Object, signal_name: String) -> Array:
	## Return the emissions recorded for one signal on a watched object.
	var entry: Dictionary = _gd_tools_signal_watchers.get(
		target.get_instance_id(), {}
	)
	var matching: Array = []
	if entry.is_empty():
		return matching
	for emission in entry["emissions"]:
		if str(emission.get("signal", "")) == signal_name:
			matching.append(emission)
	return matching


func _gd_tools_format_emissions(emissions: Array) -> String:
	## Render captured emissions compactly for failure diagnostics.
	if emissions.is_empty():
		return "none"
	var parts: Array = []
	for emission in emissions:
		parts.append("%s(%s)" % [emission["signal"], str(emission["args"])])
	return ", ".join(parts)


func _gd_tools_reset_signal_watch() -> void:
	## Disconnect every watcher and drop recordings for a fresh test state.
	for watcher_id in _gd_tools_signal_watchers:
		var entry: Dictionary = _gd_tools_signal_watchers[watcher_id]
		var watched = entry.get("object")
		if not is_instance_valid(watched):
			continue
		var connections: Dictionary = entry.get("connections", {})
		for signal_name in connections:
			watched.disconnect(signal_name, connections[signal_name])
	_gd_tools_signal_watchers.clear()


func _gd_tools_on_watched_emission_0(instance_id, signal_name) -> void:
	_gd_tools_record_watched_emission(instance_id, signal_name, [])


func _gd_tools_on_watched_emission_1(p1, instance_id, signal_name) -> void:
	_gd_tools_record_watched_emission(instance_id, signal_name, [p1])


func _gd_tools_on_watched_emission_2(p1, p2, instance_id, signal_name) -> void:
	_gd_tools_record_watched_emission(instance_id, signal_name, [p1, p2])


func _gd_tools_on_watched_emission_3(
	p1, p2, p3, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(instance_id, signal_name, [p1, p2, p3])


func _gd_tools_on_watched_emission_4(
	p1, p2, p3, p4, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4]
	)


func _gd_tools_on_watched_emission_5(
	p1, p2, p3, p4, p5, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5]
	)


func _gd_tools_on_watched_emission_6(
	p1, p2, p3, p4, p5, p6, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5, p6]
	)


func _gd_tools_on_watched_emission_7(
	p1, p2, p3, p4, p5, p6, p7, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5, p6, p7]
	)


func _gd_tools_on_watched_emission_8(
	p1, p2, p3, p4, p5, p6, p7, p8, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5, p6, p7, p8]
	)


func _gd_tools_on_watched_emission_9(
	p1, p2, p3, p4, p5, p6, p7, p8, p9, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5, p6, p7, p8, p9]
	)


func _gd_tools_on_watched_emission_10(
	p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, instance_id, signal_name
) -> void:
	_gd_tools_record_watched_emission(
		instance_id, signal_name, [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10]
	)


func _gd_tools_record_watched_emission(
	instance_id: int, signal_name: String, args: Array
) -> void:
	## Store one captured emission on the watcher entry for `instance_id`.
	var entry: Dictionary = _gd_tools_signal_watchers.get(instance_id, {})
	if entry.is_empty():
		return
	entry["emissions"].append({"signal": signal_name, "args": args})


func _gd_tools_double_calls(target: Object, method: String) -> Array:
	## Return the arguments of every recorded call to `method` on a double.
	var mock: Object = target.get("__gd_tools")
	var recorded: Array = []
	for call in mock.get("calls"):
		if str(call.get("method", "")) == method:
			recorded.append(call.get("args", []))
	return recorded


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


func parameterize(param_names, values) -> void:
	## Declare the parameter sets for the suite's parameterized tests.
	##
	## Called once from `before_all`. The preflight validates the declaration
	## statically and the runner expands each matching `test_*` method into
	## one case per value set. Runtime expansion is provided by the runner;
	## this method only records the declaration. The arguments stay untyped
	## so that malformed declarations are reported by the preflight instead
	## of refusing to compile the suite.
	_gd_tools_parameter_names = param_names.duplicate(true)
	_gd_tools_parameter_values = values.duplicate(true)


func use_parameters(params: Variant) -> Variant:
	## Return the current case's value from a ``use_parameters`` declaration.
	##
	## The preflight statically resolves the literal argument into per-case
	## metadata and the runner advances the case index before each case body
	## runs, so repeated calls observe one value per case (the GUT legacy
	## convention). Declare at most one ``use_parameters`` call per test
	## method; the preflight rejects additional calls. An index past the end
	## of ``params`` yields ``null`` instead of failing the run.
	if typeof(params) == TYPE_DICTIONARY:
		var values: Array = (params as Dictionary).values()
		if _gd_tools_case_index < values.size():
			return values[_gd_tools_case_index]
		return null
	if typeof(params) == TYPE_ARRAY:
		if _gd_tools_case_index < (params as Array).size():
			return (params as Array)[_gd_tools_case_index]
		return null
	return null


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


func wait_for_signal(target_signal: Signal, timeout_seconds: float = 5.0) -> bool:
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
	_gd_tools_wait_timer.timeout.connect(_gd_tools_wait_resolved.emit, CONNECT_ONE_SHOT)
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
	if (
		_gd_tools_wait_signal != null
		and _gd_tools_wait_signal.is_connected(_gd_tools_on_wait_signal)
	):
		_gd_tools_wait_signal.disconnect(_gd_tools_on_wait_signal)
	if (
		_gd_tools_wait_timer != null
		and _gd_tools_wait_timer.timeout.is_connected(_gd_tools_wait_resolved.emit)
	):
		_gd_tools_wait_timer.timeout.disconnect(_gd_tools_wait_resolved.emit)
	_gd_tools_wait_signal = null
	_gd_tools_wait_timer = null


## Assert that a value matches its stored snapshot, writing it on first run.
##
## The first run for a given snapshot name stores the canonical rendering of
## [param value] and passes; later runs compare against the stored file and
## fail with a line diff when the rendering drifts. I/O problems and
## malformed snapshot files fail closed: they record a failure instead of
## silently passing. Automatic names follow the ``<test>_<call_index>``
## convention; pass [param name] to override it.
func assert_snapshot(value, name: String = "") -> void:
	var suite_name := _gd_tools_snapshot_suite_name
	var test_name := _gd_tools_snapshot_test_name
	if suite_name.is_empty() or test_name.is_empty():
		_gd_tools_record_failure(
			"assert_snapshot",
			"Snapshot context is unavailable; assert_snapshot requires the native runner.",
			str(value),
			""
		)
		return
	var snapshot_name := name
	if snapshot_name.is_empty():
		_gd_tools_snapshot_call_count += 1
		snapshot_name = "%s_%d" % [test_name, _gd_tools_snapshot_call_count]
	var rendered := _GD_TOOLS_SNAPSHOT_SERIALIZER.render(value)
	var existing := _GD_TOOLS_SNAPSHOT_STORE.read(
		_gd_tools_snapshot_base_dir(), suite_name, test_name, snapshot_name
	)
	if bool(existing.get("ok", false)):
		var stored := str(existing.get("value", ""))
		if stored == rendered:
			return
		_gd_tools_record_failure(
			"assert_snapshot",
			"Snapshot mismatch for %s:\n%s\nRun gd-tools test --snapshot-update to accept the new output."
				% [snapshot_name, _gd_tools_snapshot_diff(stored, rendered)],
			rendered,
			stored,
		)
		return
	if str(existing.get("error", "io")) != "not_found":
		_gd_tools_record_failure(
			"assert_snapshot",
			str(existing.get("message", "Snapshot read failed.")),
			rendered,
			""
		)
		return
	var write_result := _GD_TOOLS_SNAPSHOT_STORE.write(
		_gd_tools_snapshot_base_dir(), suite_name, test_name, snapshot_name, rendered
	)
	if not bool(write_result.get("ok", false)):
		_gd_tools_record_failure(
			"assert_snapshot",
			str(write_result.get("message", "Snapshot write failed.")),
			rendered,
			""
		)
		return
	_gd_tools_snapshots_written.append("%s/%s/%s" % [suite_name, test_name, snapshot_name])


## Snapshots written by this test attempt, as ``suite/test/name`` paths.
func get_snapshots_written() -> Array[String]:
	return _gd_tools_snapshots_written.duplicate()


func _gd_tools_snapshot_base_dir() -> String:
	var base_dir := OS.get_environment("GD_TOOLS_SNAPSHOT_BASE")
	if base_dir.is_empty():
		return _GD_TOOLS_SNAPSHOT_DEFAULT_BASE
	return base_dir


## Render a unified-style line diff between stored and rendered snapshots.
func _gd_tools_snapshot_diff(stored: String, rendered: String) -> String:
	var old_lines := stored.split("\n")
	var new_lines := rendered.split("\n")
	var rows := old_lines.size()
	var cols := new_lines.size()
	var table: Array = []
	for _row in range(rows + 1):
		var line := []
		line.resize(cols + 1)
		line.fill(0)
		table.append(line)
	for i in range(rows - 1, -1, -1):
		for j in range(cols - 1, -1, -1):
			if old_lines[i] == new_lines[j]:
				table[i][j] = int(table[i + 1][j + 1]) + 1
			else:
				table[i][j] = max(int(table[i + 1][j]), int(table[i][j + 1]))
	var out: Array[String] = []
	var i := 0
	var j := 0
	while i < rows and j < cols:
		if old_lines[i] == new_lines[j]:
			out.append("  " + str(old_lines[i]))
			i += 1
			j += 1
		elif int(table[i + 1][j]) >= int(table[i][j + 1]):
			out.append("+ " + str(new_lines[j]))
			j += 1
		else:
			out.append("- " + str(old_lines[i]))
			i += 1
	while i < rows:
		out.append("- " + str(old_lines[i]))
		i += 1
	while j < cols:
		out.append("+ " + str(new_lines[j]))
		j += 1
	return "\n".join(PackedStringArray(out))
