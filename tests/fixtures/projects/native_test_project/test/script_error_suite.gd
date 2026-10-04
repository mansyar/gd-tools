extends GdToolsTest

class_name NativeScriptErrorSuite

# Aborted-test detection: a GDScript runtime error must never masquerade as
# a pass. Script errors are recoverable in Godot, so without runner support
# a test that aborts mid-body is reported as `passed`. These cases pin the
# contract: the aborted test is reported as errored with the engine message,
# and the rest of the suite still runs.

func test_script_error_aborts_the_test_body() -> void:
	# Calling a nonexistent method through a Variant aborts this body; the
	# runner must report this test as errored, never passed.
	var v: Variant = RefCounted.new()
	v.nonexistent_method_on_purpose()
	# Unreachable when the abort behaves as expected.
	assert_true(false, "the body should have aborted before this line")


func test_the_rest_of_the_suite_still_runs() -> void:
	assert_true(true)
