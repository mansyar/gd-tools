extends GdToolsTest

class_name NativeAssertionSuite

# Satisfying-side coverage for the GUT-core comparison, membership, and
# introspection assertions (spec R5). Every method here must pass.
#
# `test_structured_failure` is pre-existing and deliberately fails; it is pinned
# by tests/e2e/test_native_runtime.py::test_native_assertions_report_values_and_source,
# which selects it by name in its manifest. The passing methods below are
# selected by a different manifest, so both coexist in this file.

func test_structured_failure() -> void:
	assert_eq(1, 2, "values differ")


func test_gt_passes_when_greater() -> void:
	# R5: assert_gt passes when the first argument is strictly greater.
	assert_gt(5, 3)


func test_gte_passes_when_equal() -> void:
	# R5: assert_gte is inclusive, so equal values pass.
	assert_gte(4, 4)


func test_lt_passes_when_less() -> void:
	# R5: assert_lt passes when the first argument is strictly less.
	assert_lt(2, 9)


func test_lte_passes_when_equal() -> void:
	# R5: assert_lte is inclusive, so equal values pass.
	assert_lte(-1, -1)


func test_between_passes_in_range() -> void:
	# R5: assert_between passes for a value strictly inside the bounds.
	assert_between(5, 1, 10)


func test_between_inclusive_lower_bound() -> void:
	# R5 DELIBERATE: the lower bound is INCLUSIVE. Exclusive is the more common
	# convention elsewhere, but a migrated GUT test must not change meaning.
	# Do not "fix" this to be exclusive.
	assert_between(1, 1, 10)


func test_between_inclusive_upper_bound() -> void:
	# R5 DELIBERATE: the upper bound is INCLUSIVE. Do not "fix" this to be
	# exclusive; see test_between_inclusive_lower_bound.
	assert_between(10, 1, 10)


func test_almost_eq_passes_within_delta() -> void:
	# R5: assert_almost_eq compares the absolute difference against max_delta.
	assert_almost_eq(1.001, 1.0, 0.01)


func test_has_passes_for_present_element() -> void:
	# R5: assert_has(container, element) -- element is present.
	assert_has([1, 2, 3], 2)


func test_in_passes_for_present_element() -> void:
	# R5: assert_in(element, container) -- note the INVERTED argument order
	# relative to assert_has. Do not normalise the two.
	assert_in(2, [1, 2, 3])


func test_has_argument_order() -> void:
	# R5 DELIBERATE: the same membership check in assert_has's order.
	# Written so that swapping the two arguments would break this method.
	assert_has(["a", "b"], "a")


func test_in_argument_order() -> void:
	# R5 DELIBERATE: the same membership check in assert_in's order.
	# Written so that swapping the two arguments would break this method.
	assert_in("a", ["a", "b"])


func test_has_works_on_dictionary() -> void:
	# R5: membership is not limited to arrays.
	assert_has({"key": 1}, "key")


func test_has_works_on_string_via_contains() -> void:
	# Strings spell membership `contains`, not `has`. The assertion bridges
	# that difference so a natural call does not read as a type failure.
	assert_has("hello world", "world")


func test_has_method_passes_for_existing_method() -> void:
	# R5: assert_has_method checks an Object really exposes the method.
	assert_has_method(self, "get_tree")


func test_is_passes_for_same_instance() -> void:
	# R5: assert_is compares reference identity, so two references to one
	# object pass.
	var shared := RefCounted.new()
	var alias := shared
	assert_is(shared, alias)


func test_is_passes_for_shared_array() -> void:
	# Arrays are reference types in Godot 4, so identity applies to them too.
	var values: Array = [1, 2, 3]
	var alias: Array = values
	assert_is(values, alias)
