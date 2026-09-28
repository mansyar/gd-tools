extends GutTest
class_name BridgeAssertionSuite

func test_value_and_comparison_assertions() -> void:
	assert_eq(1 + 1, 2)
	assert_ne(1, 2)
	assert_true(true)
	assert_false(false)
	assert_null(null)
	assert_not_null(RefCounted.new())
	assert_gt(3, 2)
	assert_gte(2, 2)
	assert_lt(1, 2)
	assert_lte(2, 2)
	assert_almost_eq(0.5, 0.50001, 0.001)
	assert_almost_ne(0.5, 0.6, 0.001)
	assert_between(5, 1, 10)
	assert_not_between(15, 1, 10)

func test_container_and_object_assertions() -> void:
	assert_has([1, 2, 3], 2)
	assert_does_not_have([1, 2, 3], 4)
	assert_has("hello world", "world")
	assert_has_method(self, "test_container_and_object_assertions")
	assert_same(self, self)
	assert_not_same(RefCounted.new(), RefCounted.new())
	assert_typeof(5, TYPE_INT)
	assert_not_typeof("five", TYPE_INT)
	assert_eq_deep([1, [2]], [1, [2]])
	assert_ne_deep([1, 2], [1, 3])

func test_string_assertions() -> void:
	assert_string_contains("hello world", "o w")
	assert_string_starts_with("hello world", "hello")
	assert_string_ends_with("hello world", "world")

func test_file_assertions() -> void:
	assert_file_exists("res://data/sample.txt")
	assert_file_not_empty("res://data/sample.txt")
	assert_file_does_not_exist("res://data/missing.txt")

func test_file_empty_assertion() -> void:
	# Regression: an existing empty file must pass assert_file_empty; the
	# original implementation fell through to the "File does not exist" fail.
	var path := "res://data/empty_tmp.txt"
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.close()
	assert_file_exists(path)
	assert_file_empty(path)
