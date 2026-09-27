extends GdToolsTest

class_name NativeAssertionTypeSafetySuite

# Spec R4: a wrong-typed argument must record an ACTIONABLE TEST FAILURE, never
# raise a GDScript runtime error.
#
# This is a hard requirement, not a nicety. A GDScript error captured by the
# runner escalates the WHOLE RUN to exit 2 (gd_tools_test_runner.gd, the
# engine-diagnostics escalation), which would convert one bad call in one test
# into a run-level environment failure with a misleading exit code.
#
# So every method here must end with status `failed` and a message naming the
# type problem -- never a crash, and never exit 2.

func test_between_rejects_non_numeric_value() -> void:
	# R4: the value under test is a String.
	assert_between("five", 1, 10, "value is not numeric")


func test_between_rejects_non_numeric_bound() -> void:
	# R4: the bound is a String, so no comparison is possible.
	assert_between(5, "one", 10, "lower bound is not numeric")


func test_almost_eq_rejects_non_numeric() -> void:
	# R4: a String cannot be differenced.
	assert_almost_eq("one", "two", 0.1, "arguments are not numeric")


func test_has_rejects_non_container() -> void:
	# R4: an int is not a container.
	assert_has(5, 1, "not a container")


func test_in_rejects_non_container() -> void:
	# R4: a float is not a container.
	assert_in(1, 2.5, "not a container")


func test_has_method_rejects_non_object() -> void:
	# R4: an int has no methods to look up.
	assert_has_method(5, "free", "not an object")


func test_is_rejects_value_types() -> void:
	# R4: two ints are compared by value, not identity, so assert_is is the
	# wrong assertion and the message must say so rather than silently
	# behaving like assert_eq.
	assert_is(2, 2, "integers carry no reference identity")


func test_is_rejects_null() -> void:
	# R4: null carries no reference identity either.
	assert_is(null, null, "null carries no reference identity")
