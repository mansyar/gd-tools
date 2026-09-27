extends GdToolsTest

class_name NativeAssertionFailuresSuite

# Violating-side coverage for the GUT-core comparison, membership, and
# introspection assertions (spec R5, final column).
#
# Every method here deliberately breaks its contract so the recorded failure
# can be inspected. R5 requires the MESSAGE to carry the type-specific detail,
# because the record keeps no extra structure (R6). These methods therefore
# pin what each message must name.

func test_gt_fails_when_not_greater() -> void:
	assert_gt(2, 5, "two should beat five")


func test_gte_fails_when_less() -> void:
	assert_gte(1, 5, "one is not at least five")


func test_lt_fails_when_not_less() -> void:
	assert_lt(9, 2, "nine is not less than two")


func test_lte_fails_when_greater() -> void:
	assert_lte(7, 2, "seven is not at most two")


func test_between_fails_below_lower_bound() -> void:
	# The message must name the violated bound AND its value.
	assert_between(-3, 0, 10, "value under the lower bound")


func test_between_fails_above_upper_bound() -> void:
	# The message must name the violated bound AND its value.
	assert_between(42, 0, 10, "value over the upper bound")


func test_between_fails_when_bounds_inverted() -> void:
	# A value outside an inverted range still fails; the message must name
	# which bound was violated.
	assert_between(5, 10, 0, "bounds are inverted")


func test_almost_eq_fails_outside_delta() -> void:
	# The message must name the observed delta and the allowance.
	assert_almost_eq(1.5, 1.0, 0.1, "half a unit apart")


func test_has_fails_for_absent_element() -> void:
	# The message must name the missing element and the container's type.
	assert_has([1, 2, 3], 99, "99 is not in the array")


func test_in_fails_for_absent_element() -> void:
	# The message must name the missing element and the container's type.
	assert_in("missing", ["a", "b"], "string absent from the array")


func test_has_method_fails_for_missing_method() -> void:
	# The message must name the object's type and the missing method.
	assert_has_method(self, "definitely_not_a_method", "no such method")


func test_is_fails_for_distinct_instances() -> void:
	# The message must name both types and say they were distinct instances.
	var left := RefCounted.new()
	var right := RefCounted.new()
	assert_is(left, right, "two different objects")
