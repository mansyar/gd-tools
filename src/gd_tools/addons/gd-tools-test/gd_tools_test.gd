class_name GdToolsTest
extends Node

## Base class for gd-tools native GDScript tests.
##
## The runner owns lifecycle and process management. This class only provides
## the assertion surface and Godot-specific waits needed by a test suite.

var _gd_tools_failures: Array[Dictionary] = []


func _gd_tools_record_failure(
		assertion: String,
		message: String = "",
		actual = null,
		expected = null
) -> void:
	## Record one structured assertion failure for the current test.
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
	## Clear assertion state before reusing a test instance.
	_gd_tools_failures.clear()


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
