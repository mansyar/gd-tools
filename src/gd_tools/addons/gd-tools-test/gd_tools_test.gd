class_name GdToolsTest
extends Node

## Base class for gd-tools native GDScript tests.
##
## The runner owns lifecycle and process management. This class only provides
## the assertion surface and Godot-specific waits needed by a test suite.

var _gd_tools_failures: Array[Dictionary] = []
var _gd_tools_suite_state: Dictionary = {}
var _gd_tools_test_context: GdToolsTestContext = null
var _gd_tools_skipped := false
var _gd_tools_skip_reason := ""


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


func wait_for_signal(target_signal: Signal) -> bool:
	## Wait until a signal is emitted and return true.
	await target_signal
	return true
